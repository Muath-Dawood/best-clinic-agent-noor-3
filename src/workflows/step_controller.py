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


class StepController:
    """Manage transitions and mutations on a :class:`BookingContext`."""

    _FIELD_TO_STEP: Dict[str, BookingStep] = {
        "selected_services_pm_si": BookingStep.SELECT_SERVICE,
        "selected_services_data": BookingStep.SELECT_SERVICE,
        "appointment_date": BookingStep.SELECT_DATE,
        "appointment_time": BookingStep.SELECT_TIME,
        "total_price": BookingStep.SELECT_TIME,
        "employee_pm_si": BookingStep.SELECT_EMPLOYEE,
        "employee_name": BookingStep.SELECT_EMPLOYEE,
        "booking_confirmed": BookingStep.SELECT_EMPLOYEE,
    }

    _DOWNSTREAM_FIELDS: Dict[BookingStep, list[str]] = {
        BookingStep.SELECT_SERVICE: [
            "selected_services_pm_si",
            "selected_services_data",
            "appointment_date",
            "appointment_time",
            "total_price",
            "employee_pm_si",
            "employee_name",
            "booking_confirmed",
        ],
        BookingStep.SELECT_DATE: [
            "appointment_date",
            "appointment_time",
            "total_price",
            "employee_pm_si",
            "employee_name",
            "booking_confirmed",
        ],
        BookingStep.SELECT_TIME: [
            "appointment_time",
            "total_price",
            "employee_pm_si",
            "employee_name",
            "booking_confirmed",
        ],
        BookingStep.SELECT_EMPLOYEE: [
            "employee_pm_si",
            "employee_name",
            "booking_confirmed",
        ],
    }

    _STEP_ORDER = [
        BookingStep.SELECT_SERVICE,
        BookingStep.SELECT_DATE,
        BookingStep.SELECT_TIME,
        BookingStep.SELECT_EMPLOYEE,
    ]

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
    def apply_patch(self, patch: Dict[str, Any], *, invalidate: bool = True) -> None:
        """Apply ``patch`` to the context and record a new version."""

        if invalidate:
            step = self._derive_step_from_patch(patch)
            if step is not None:
                self.invalidate_downstream_fields(step)

        for name, value in patch.items():
            setattr(self.ctx, name, value)

        self.ctx.version += 1
        self._history[self.ctx.version] = deepcopy(self.ctx)

    # ------------------------------------------------------------------
    def revert_to(self, version: int) -> None:
        """Revert the context to ``version`` if available."""

        snapshot = self._history.get(version)
        if snapshot is None:
            return

        for field in self.ctx.__dataclass_fields__:
            setattr(self.ctx, field, getattr(snapshot, field))

        self.ctx.version = version
        self._history = {
            v: deepcopy(s) for v, s in self._history.items() if v <= version
        }

    # ------------------------------------------------------------------
    def invalidate_downstream_fields(self, step: BookingStep) -> None:
        """Clear fields for ``step`` and all downstream steps."""

        fields = self._DOWNSTREAM_FIELDS.get(step, [])
        patch = {name: self._defaults[name] for name in fields}
        if patch:
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
        if isinstance(result, ToolResult) and result.ctx_patch:
            StepController(context.context).apply_patch(result.ctx_patch)


__all__ = ["StepController", "StepControllerRunHooks"]

