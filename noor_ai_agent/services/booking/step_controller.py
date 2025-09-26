"""
Step controller for managing booking workflow state.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, Optional

from agents import Agent, RunContextWrapper
from agents.lifecycle import RunHooksBase
from agents.tool import Tool

from ...core.models.booking import BookingContext, BookingContextUpdate
from ...core.enums import BookingStep
from ...utils.validation import ValidationUtils


class StepController:
    """Manage transitions and mutations on a BookingContext."""

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
        ],
    }

    def __init__(self, ctx: BookingContext) -> None:
        self.ctx = ctx
        self._history: Dict[int, BookingContext] = {ctx.version: deepcopy(ctx)}
        self._defaults = asdict(BookingContext())

    def next_allowed(self, step: Optional[BookingStep]) -> bool:
        """Return True if step is allowed from current state."""
        # This would need the original BOOKING_STEP_TRANSITIONS mapping
        # For now, implementing a simplified version
        if self.ctx.next_booking_step is None:
            return step == BookingStep.SELECT_SERVICE
        elif self.ctx.next_booking_step == BookingStep.SELECT_SERVICE:
            return step == BookingStep.SELECT_DATE
        elif self.ctx.next_booking_step == BookingStep.SELECT_DATE:
            return step == BookingStep.SELECT_TIME
        elif self.ctx.next_booking_step == BookingStep.SELECT_TIME:
            return step == BookingStep.SELECT_EMPLOYEE
        elif self.ctx.next_booking_step == BookingStep.SELECT_EMPLOYEE:
            return step is None
        return False

    def _derive_step_from_patch(self, patch: Dict[str, Any]) -> Optional[BookingStep]:
        """Derive the step from the fields being updated."""
        steps = [self._FIELD_TO_STEP.get(name) for name in patch]
        steps = [s for s in steps if s is not None]
        if not steps:
            return None
        for step in self._STEP_ORDER:
            if step in steps:
                return step
        return None

    def _compute_next_step(self) -> Optional[BookingStep]:
        """Compute the next step based on current context state."""
        if not self.ctx.selected_services_pm_si:
            return BookingStep.SELECT_SERVICE
        if not self.ctx.appointment_date:
            return BookingStep.SELECT_DATE
        if not self.ctx.available_times and not self.ctx.appointment_time:
            return BookingStep.SELECT_DATE
        if not self.ctx.appointment_time:
            return BookingStep.SELECT_TIME
        if self.ctx.available_times and self.ctx.appointment_time not in {
            t.get("time") for t in self.ctx.available_times
        }:
            return BookingStep.SELECT_TIME
        if not self.ctx.employee_pm_si or not self.ctx.booking_confirmed:
            return BookingStep.SELECT_EMPLOYEE
        return None

    def _validate_prereqs(self, patch: Dict[str, Any]) -> None:
        """Validate prerequisites for the fields being updated."""
        combined: Dict[str, Any] = asdict(self.ctx)
        combined.update({k: v for k, v in patch.items() if k != "next_booking_step"})

        for name, value in patch.items():
            step = self._FIELD_TO_STEP.get(name)
            if step is None:
                continue
            if value is None or value is False:
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

    def apply_patch(
        self,
        patch: Dict[str, Any],
        *,
        invalidate: bool = True,
        expected_version: int | None = None,
    ) -> None:
        """Apply patch to the context and record a new version."""
        if expected_version is not None and expected_version != self.ctx.version:
            raise ValueError(
                f"Context version mismatch: expected {expected_version}, got {self.ctx.version}"
            )

        patch = {k: v for k, v in patch.items() if k != "next_booking_step"}

        prev_step = self.ctx.next_booking_step

        if not patch:
            self.ctx.next_booking_step = self._compute_next_step()
            if prev_step != self.ctx.next_booking_step:
                self._log_step_transition(prev_step, self.ctx.next_booking_step)
            return

        if invalidate:
            self._validate_prereqs(patch)
            step = self._derive_step_from_patch(patch)
            if step is not None:
                self.invalidate_downstream_fields(step, expected_version=self.ctx.version)

        for name, value in patch.items():
            setattr(self.ctx, name, value)

        self.ctx.next_booking_step = self._compute_next_step()
        self.ctx.version += 1
        self._history[self.ctx.version] = deepcopy(self.ctx)

        if prev_step != self.ctx.next_booking_step:
            self._log_step_transition(prev_step, self.ctx.next_booking_step)

    def revert_to(self, version: int) -> None:
        """Revert the context to a previous version."""
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
            self._log_step_transition(prev_step, self.ctx.next_booking_step)

    def invalidate_downstream_fields(
        self, step: BookingStep, *, expected_version: int | None = None
    ) -> None:
        """Clear fields for step and all downstream steps."""
        fields = self._DOWNSTREAM_FIELDS.get(step, [])
        patch = {name: self._defaults[name] for name in fields}
        if patch:
            self.apply_patch(
                patch, invalidate=False, expected_version=expected_version
            )

    def _log_step_transition(self, from_step: Optional[BookingStep], to_step: Optional[BookingStep]) -> None:
        """Log step transition for debugging."""
        # This would integrate with the logging system
        pass


class StepControllerRunHooks(RunHooksBase[BookingContext, Agent]):
    """Apply context patches returned by tools using StepController."""

    async def on_tool_end(
        self,
        context: RunContextWrapper[BookingContext],
        agent: Agent,
        tool: Tool,
        result: Any,
    ) -> None:
        """Handle tool completion and apply patches."""
        # This would integrate with the tool result system
        pass
