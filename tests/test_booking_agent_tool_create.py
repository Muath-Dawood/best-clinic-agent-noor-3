import json
import pytest

from src.app.context_models import BookingContext, BookingStep
from src.workflows.step_controller import StepController
from src.tools.booking_agent_tool import create_booking
import src.tools.booking_tool as booking_tool_module


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_create_booking_returns_human_message(monkeypatch):
    ctx = BookingContext(
        selected_services_pm_si=["svcX"],
        selected_services_data=[{"title": "استشارة طبية"}],
        appointment_date="2025-08-20",
        appointment_time="10:00",
        offered_employees=[{"pm_si": "emp1", "name": "دكتور مؤمن"}],
        employee_pm_si="emp1",
        employee_name="دكتور مؤمن",
        user_name="مراجع",
        user_phone="0590000000",
    )
    StepController(ctx).apply_patch({})
    ctx.next_booking_step = BookingStep.SELECT_EMPLOYEE

    async def ok_create(date, time, emp, svcs, cust, gender, idempotency_key=None):
        return {"result": True, "data": {"booking_id": 123}}

    monkeypatch.setattr(booking_tool_module.booking_tool, "create_booking", ok_create)

    res = await create_booking.on_invoke_tool(W(ctx), json.dumps({}))
    assert isinstance(res.public_text, str) and not res.public_text.strip().startswith("{")
    assert "تم تأكيد حجزك" in res.public_text
    assert "2025-08-20" in res.public_text
    assert "10:00" in res.public_text
    assert "دكتور مؤمن" in res.public_text
