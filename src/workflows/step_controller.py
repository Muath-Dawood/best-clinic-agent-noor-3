"""Utilities for managing booking workflow state.

The :class:`StepController` applies patches to a :class:`BookingContext`
instance while keeping track of a monotonically increasing ``version`` and
supporting rollbacks.  It also knows which context fields belong to each
booking step so downstream selections can be invalidated when upstream values
change.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, Optional

from agents import Agent, RunContextWrapper
from agents.lifecycle import RunHooksBase
from agents.tool import Tool

from src.tools.tool_result import ToolResult

from src.app.context_models import (
    BookingContext,
    BookingStep,
    BOOKING_STEP_TRANSITIONS,
)
from src.app.event_log import log_event


class StepController:
    """Manage transitions and mutations on a :class:`BookingContext`."""

    _FIELD_TO_STEP: Dict[str, BookingStep] = {
        "selected_services_pm_si": BookingStep.SELECT_SERVICE,
        "selected_services_data": BookingStep.SELECT_SERVICE,
        "appointment_date": BookingStep.SELECT_DATE,
        "available_times": BookingStep.SELECT_DATE,
        "appointment_time": BookingStep.SELECT_TIME,
        "total_price": BookingStep.SELECT_TIME,
        "employee_pm_si": BookingStep.SELECT_EMPLOYEE,
        "employee_name": BookingStep.SELECT_EMPLOYEE,
        "offered_employees": BookingStep.SELECT_EMPLOYEE,
        "checkout_summary": BookingStep.SELECT_EMPLOYEE,
        "booking_confirmed": BookingStep.SELECT_EMPLOYEE,
    }

    _DOWNSTREAM_FIELDS: Dict[BookingStep, list[str]] = {
        BookingStep.SELECT_SERVICE: [
            "selected_services_pm_si",
            "selected_services_data",
            "appointment_date",
            "available_times",
            "appointment_time",
            "total_price",
            "employee_pm_si",
            "employee_name",
            "offered_employees",
            "checkout_summary",
            "booking_confirmed",
        ],
        BookingStep.SELECT_DATE: [
            "appointment_date",
            "available_times",
            "appointment_time",
            "total_price",
            "employee_pm_si",
            "employee_name",
            "offered_employees",
            "checkout_summary",
            "booking_confirmed",
        ],
        BookingStep.SELECT_TIME: [
            "available_times",
            "appointment_time",
            "total_price",
            "employee_pm_si",
            "employee_name",
            "offered_employees",
            "checkout_summary",
            "booking_confirmed",
        ],
        BookingStep.SELECT_EMPLOYEE: [
            "employee_pm_si",
            "employee_name",
            "offered_employees",
            "checkout_summary",
            "booking_confirmed",
        ],
    }

    _STEP_ORDER = [
        BookingStep.SELECT_SERVICE,
        BookingStep.SELECT_DATE,
        BookingStep.SELECT_TIME,
        BookingStep.SELECT_EMPLOYEE,
    ]

    _STEP_PREREQS: Dict[BookingStep, list[str]] = {
        BookingStep.SELECT_SERVICE: [],
        BookingStep.SELECT_DATE: ["selected_services_pm_si"],
        BookingStep.SELECT_TIME: [
            "selected_services_pm_si",
            "appointment_date",
            "available_times",
        ],
        BookingStep.SELECT_EMPLOYEE: [
            "selected_services_pm_si",
            "appointment_date",
            "appointment_time",
            "available_times",
        ],
    }

    def __init__(self, ctx: BookingContext) -> None:
        self.ctx = ctx
        self._history: Dict[int, BookingContext] = {ctx.version: deepcopy(ctx)}
        self._defaults = asdict(BookingContext())

    # ------------------------------------------------------------------
    def next_allowed(self, step: Optional[BookingStep]) -> bool:
        """Return ``True`` if ``step`` is allowed from current state."""

        allowed = BOOKING_STEP_TRANSITIONS.get(self.ctx.next_booking_step, [])
        return step in allowed

    # ------------------------------------------------------------------
    def _derive_step_from_patch(self, patch: Dict[str, Any]) -> Optional[BookingStep]:
        steps = [self._FIELD_TO_STEP.get(name) for name in patch]
        steps = [s for s in steps if s is not None]
        if not steps:
            return None
        for step in self._STEP_ORDER:
            if step in steps:
                return step
        return None

    # ------------------------------------------------------------------
    def _compute_next_step(self) -> Optional[BookingStep]:
        if not self.ctx.selected_services_pm_si:
            return BookingStep.SELECT_SERVICE
        if not self.ctx.appointment_date:
            return BookingStep.SELECT_DATE
        if not self.ctx.available_times:
            return BookingStep.SELECT_DATE
        if not self.ctx.appointment_time:
            return BookingStep.SELECT_TIME
        if self.ctx.available_times and self.ctx.appointment_time not in {
            t.get("time") for t in self.ctx.available_times
        }:
            return BookingStep.SELECT_TIME
        if not self.ctx.employee_pm_si:
            return BookingStep.SELECT_EMPLOYEE
        return None

    # ------------------------------------------------------------------
    def _validate_prereqs(self, patch: Dict[str, Any]) -> None:
        combined: Dict[str, Any] = asdict(self.ctx)
        combined.update({k: v for k, v in patch.items() if k != "next_booking_step"})
        for name, value in patch.items():
            step = self._FIELD_TO_STEP.get(name)
            if step is None:
                continue
            for req in self._STEP_PREREQS.get(step, []):
                if not combined.get(req):
                    raise ValueError(
                        f"Cannot set '{name}' before '{req}' is provided"
                    )
            if name == "appointment_time" and combined.get("available_times"):
                times = {t.get("time") for t in combined["available_times"]}
                if value not in times:
                    raise ValueError(
                        f"Cannot set 'appointment_time' to unavailable time '{value}'"
                    )

    # ------------------------------------------------------------------
    def apply_patch(self, patch: Dict[str, Any], *, invalidate: bool = True) -> None:
        """Apply ``patch`` to the context and record a new version."""

        patch = {k: v for k, v in patch.items() if k != "next_booking_step"}

        prev_step = self.ctx.next_booking_step

        if not patch:
            self.ctx.next_booking_step = self._compute_next_step()
            if prev_step != self.ctx.next_booking_step:
                log_event(
                    "step_transition",
                    {"from": prev_step, "to": self.ctx.next_booking_step, "version": self.ctx.version},
                )
            return

        if invalidate:
            self._validate_prereqs(patch)
            step = self._derive_step_from_patch(patch)
            if step is not None:
                self.invalidate_downstream_fields(step)

        for name, value in patch.items():
            setattr(self.ctx, name, value)

        self.ctx.next_booking_step = self._compute_next_step()

        self.ctx.version += 1
        self._history[self.ctx.version] = deepcopy(self.ctx)

        if prev_step != self.ctx.next_booking_step:
            log_event(
                "step_transition",
                {"from": prev_step, "to": self.ctx.next_booking_step, "version": self.ctx.version},
            )
        log_event("context_patch", {"patch": patch, "version": self.ctx.version})

    # ------------------------------------------------------------------
    def revert_to(self, version: int) -> None:
        """Revert the context to ``version`` if available."""

        snapshot = self._history.get(version)
        if snapshot is None:
            return

        prev_step = self.ctx.next_booking_step

        for field in self.ctx.__dataclass_fields__:
            setattr(self.ctx, field, getattr(snapshot, field))

        self.ctx.version = version
        self._history = {
            v: deepcopy(s) for v, s in self._history.items() if v <= version
        }

        if prev_step != self.ctx.next_booking_step:
            log_event(
                "step_transition",
                {"from": prev_step, "to": self.ctx.next_booking_step, "version": self.ctx.version},
            )
        log_event("revert_context", {"version": version})

    # ------------------------------------------------------------------
    def invalidate_downstream_fields(self, step: BookingStep) -> None:
        """Clear fields for ``step`` and all downstream steps."""

        fields = self._DOWNSTREAM_FIELDS.get(step, [])
        patch = {name: self._defaults[name] for name in fields}
        if patch:
            log_event("invalidate_downstream", {"step": step, "fields": fields})
            self.apply_patch(patch, invalidate=False)


class StepControllerRunHooks(RunHooksBase[BookingContext, Agent]):
    """Apply context patches returned by tools using :class:`StepController`."""

    async def on_tool_end(
        self,
        context: RunContextWrapper[BookingContext],
        agent: Agent,
        tool: Tool,
        result: Any,
    ) -> None:
        log_event("tool_call", {"tool": getattr(tool, "name", str(tool))})
        if isinstance(result, ToolResult) and result.ctx_patch:
            StepController(context.context).apply_patch(result.ctx_patch)


__all__ = ["StepController", "StepControllerRunHooks"]

