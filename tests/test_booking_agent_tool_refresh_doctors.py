import json
import pytest

from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import create_booking
import src.tools.booking_tool as booking_tool_module
from src.workflows.step_controller import StepController


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_create_booking_refreshes_doctor_list(monkeypatch):
    """create_booking should refresh doctors if chosen doctor not in offered list."""

    ctx = BookingContext(
        selected_services_pm_si=["svc1"],
        selected_services_data=[{"title": "استشارة"}],
        appointment_date="2025-09-01",
        appointment_time="14:00",
        offered_employees=[{"pm_si": "emp1", "name": "دكتور أول"}],
        employee_pm_si="emp2",
        employee_name="دكتورة ثانية",
        booking_for_self=False,
        subject_name="الزوجة",
        subject_phone="0591111111",
        subject_gender="female",
        user_name="الزوج",
        user_phone="0592222222",
        gender="male",
    )

    # Initial step should be SELECT_EMPLOYEE
    StepController(ctx).apply_patch({})
    assert ctx.next_booking_step == BookingStep.SELECT_EMPLOYEE

    async def fake_get_available_employees(date, time, svcs, gender):
        return ([{"pm_si": "emp2", "name": "دكتورة ثانية"}], {"total_price": 0})

    async def fake_create(date, time, emp, svcs, cust, gender, idempotency_key=None, **kw):
        return {"result": True, "data": {"booking_id": 1}}

    monkeypatch.setattr(
        booking_tool_module.booking_tool, "get_available_employees", fake_get_available_employees
    )
    monkeypatch.setattr(booking_tool_module.booking_tool, "create_booking", fake_create)

    res = await create_booking.on_invoke_tool(W(ctx), json.dumps({}))

    # Should succeed and confirm booking
    assert res.ctx_patch.get("booking_confirmed") is True
    assert any(e["pm_si"] == "emp2" for e in res.ctx_patch.get("offered_employees", []))

    # After applying patch, flow should be complete (next step None)
    StepController(ctx).apply_patch(res.ctx_patch, invalidate=False)
    assert ctx.next_booking_step is None
