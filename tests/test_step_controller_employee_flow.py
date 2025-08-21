import json
import pytest

from src.app.context_models import BookingContext, BookingStep
from src.workflows.step_controller import StepController
from src.tools.booking_agent_tool import (
    check_availability,
    suggest_employees,
    update_booking_context,
)
import src.tools.booking_tool as booking_tool_module
from src.data.services import MEN_SERVICES

CANONICAL_SERVICE_TOKEN = MEN_SERVICES[0]["pm_si"]


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_employee_selection_after_time_no_longer_requires_available_times(monkeypatch):
    """
    Regression: After choosing a time and receiving offered doctors,
    we should be able to set employee_name without needing `available_times`
    to be re-validated/required by the controller.
    """

    # 1) Given a service is already selected
    ctx = BookingContext(selected_services_pm_si=[CANONICAL_SERVICE_TOKEN])
    StepController(ctx).apply_patch({})
    wrapper = W(ctx)

    # 2) Availability returns some times (date step)
    async def fake_times(date, svcs, gender):
        return [{"time": "12:00"}, {"time": "12:10"}]

    monkeypatch.setattr(
        booking_tool_module.booking_tool, "get_available_times", fake_times
    )

    res = await check_availability.on_invoke_tool(
        wrapper, json.dumps({"date": "2025-08-26"})
    )
    StepController(ctx).apply_patch(res.ctx_patch)
    assert ctx.available_times and ctx.next_booking_step == BookingStep.SELECT_TIME

    # 3) Choosing time yields one doctor
    async def fake_emps(date, time, svcs, gender):
        return ([{"pm_si": "emp-1", "name": "دكتور مؤمن"}], {"total_price": 50})

    monkeypatch.setattr(
        booking_tool_module.booking_tool, "get_available_employees", fake_emps
    )

    res = await suggest_employees.on_invoke_tool(
        wrapper, json.dumps({"time": "12:00"})
    )
    StepController(ctx).apply_patch(res.ctx_patch)
    assert ctx.appointment_time == "12:00"
    assert ctx.offered_employees and ctx.next_booking_step == BookingStep.SELECT_EMPLOYEE

    # 4) Now set employee by name; should succeed and NOT require available_times anew
    res = await update_booking_context.on_invoke_tool(
        wrapper, json.dumps({"updates": {"employee_name": "دكتور مؤمن"}})
    )
    # Should produce a patch (mapping name -> pm_si) or at worst a friendly message.
    # Critically: must not raise or be blocked by "available_times" prerequisite.
    assert res.ctx_patch.get("employee_pm_si") == "emp-1" or res.public_text is None


@pytest.mark.asyncio
async def test_available_times_not_cleared_on_time_change():
    """
    Changing time should not wipe available_times (they belong to the selected date).
    """
    ctx = BookingContext(
        selected_services_pm_si=[CANONICAL_SERVICE_TOKEN],
        appointment_date="2025-08-26",
        available_times=[{"time": "12:00"}, {"time": "12:10"}],
    )
    sc = StepController(ctx)

    # Simulate what suggest_employees would patch on a new time choice
    sc.apply_patch(
        {
            "appointment_time": "12:00",
            "offered_employees": [{"pm_si": "emp-1", "name": "Dr"}],
        }
    )

    # available_times should still be present
    assert ctx.available_times and {"time": "12:00"} in ctx.available_times


@pytest.mark.asyncio
async def test_employee_name_normalization():
    """Employee names with minor spelling variants should resolve correctly."""

    ctx = BookingContext(
        selected_services_pm_si=[CANONICAL_SERVICE_TOKEN],
        appointment_date="2025-08-26",
        appointment_time="12:00",
        offered_employees=[{"pm_si": "emp-1", "name": "الدكتورة هناء"}],
    )
    wrapper = W(ctx)

    res = await update_booking_context.on_invoke_tool(
        wrapper, json.dumps({"updates": {"employee_name": "الدكتوره هناء"}})
    )

    assert res.ctx_patch.get("employee_pm_si") == "emp-1"
    assert res.ctx_patch.get("employee_name") == "الدكتورة هناء"
