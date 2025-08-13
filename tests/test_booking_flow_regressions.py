import json
import pytest

from src.app.context_models import BookingContext, BookingStep
from src.workflows.step_controller import StepController
from src.tools.booking_agent_tool import (
    update_booking_context,
    BookingContextUpdate,
    check_availability,
    suggest_employees,
)
import src.tools.booking_tool as booking_tool_module
from src.data.services import MEN_SERVICES


CANON = MEN_SERVICES[0]["pm_si"]


class DummyWrapper:
    def __init__(self, ctx: BookingContext | None = None):
        self.context = ctx or BookingContext()


@pytest.mark.asyncio
async def test_time_to_doctors_handoff_without_prior_update(monkeypatch):
    """User picks time → we call suggest_employees directly and it both stores time and returns doctors."""
    # Mock API
    async def fake_times(date, services, gender):
        return [{"time": "18:00"}, {"time": "18:10"}]
    async def fake_emps(date, time, services, gender):
        return ([{"pm_si": "emp1", "name": "Dr. A"}], {"total_price": 100.0})
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_times", fake_times)
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_employees", fake_emps)

    ctx = BookingContext()
    wrapper = DummyWrapper(ctx)
    StepController(ctx).apply_patch({"selected_services_pm_si": [CANON]})
    # move to select_date
    assert ctx.next_booking_step == BookingStep.SELECT_DATE

    # pick date
    result = await check_availability.on_invoke_tool(wrapper, json.dumps({"date": "الأربعاء القادم"}))
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.next_booking_step == BookingStep.SELECT_TIME
    assert ctx.available_times

    # user picks 18:00 → call suggest_employees directly (no update context first)
    result = await suggest_employees.on_invoke_tool(wrapper, json.dumps({"time": "18:00"}))
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.appointment_time == "18:00"
    assert ctx.offered_employees and ctx.offered_employees[0]["pm_si"] == "emp1"
    assert ctx.next_booking_step == BookingStep.SELECT_EMPLOYEE


@pytest.mark.asyncio
async def test_suggest_employees_allowed_when_time_already_set(monkeypatch):
    """If time is already set and step is select_employee, suggest_employees should still work for the SAME time."""
    async def fake_emps(date, time, services, gender):
        return ([{"pm_si": "emp2", "name": "Dr. B"}], {"total_price": 150.0})
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_employees", fake_emps)

    ctx = BookingContext(
        selected_services_pm_si=[CANON],
        appointment_date="2025-09-01",
        available_times=[{"time": "18:00"}],
        appointment_time="18:00",
    )
    # Simulate we're already at employee selection
    StepController(ctx).apply_patch({"employee_pm_si": None})  # nudge version/step
    ctx.next_booking_step = BookingStep.SELECT_EMPLOYEE

    wrapper = DummyWrapper(ctx)
    result = await suggest_employees.on_invoke_tool(wrapper, json.dumps({"time": "18:00"}))
    assert "Dr. B" in result.public_text
    assert result.ctx_patch.get("offered_employees")


@pytest.mark.asyncio
async def test_check_availability_from_later_step_rewinds(monkeypatch):
    """Calling check_availability at a later step should auto-invalidate downstream and proceed cleanly."""
    async def fake_times(date, services, gender):
        return [{"time": "09:00"}]
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_times", fake_times)

    ctx = BookingContext(
        selected_services_pm_si=[CANON],
        appointment_date="2025-09-01",
        appointment_time="10:00",
        employee_pm_si="empX",
        employee_name="Dr. X",
    )
    # We're at employee step
    ctx.next_booking_step = BookingStep.SELECT_EMPLOYEE
    wrapper = DummyWrapper(ctx)

    result = await check_availability.on_invoke_tool(wrapper, json.dumps({"date": "الخميس القادم"}))
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.appointment_date  # updated
    assert ctx.available_times    # present
    # Downstream fields cleared
    assert ctx.appointment_time is None
    assert ctx.employee_pm_si is None
    assert ctx.next_booking_step == BookingStep.SELECT_TIME
