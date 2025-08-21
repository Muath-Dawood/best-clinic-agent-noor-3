import json, pytest
from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import suggest_employees
import src.tools.booking_tool as booking_tool_module


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_suggest_employees_allowed_from_select_employee_state(monkeypatch):
    ctx = BookingContext(
        selected_services_pm_si=["svc1"],
        appointment_date="2025-08-25",
        appointment_time="09:00",
        subject_gender="female",
        booking_for_self=False,
        available_times=None,
        next_booking_step=BookingStep.SELECT_EMPLOYEE,
    )

    async def fake_times(d, svcs, g):
        return [{"time": "09:00"}, {"time": "10:30"}]
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_times", fake_times)

    async def fake_emps(date, time, svcs, gender):
        assert time == "10:30"
        return ([{"pm_si": "empF", "name": "د. خديجة"}], {"total_price": 100})
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_employees", fake_emps)

    res = await suggest_employees.on_invoke_tool(W(ctx), json.dumps({"time": "10:30"}))
    assert res.ctx_patch.get("appointment_time") == "10:30"
    assert isinstance(res.ctx_patch.get("offered_employees"), list)
    assert res.ctx_patch.get("available_times") == [{"time": "09:00"}, {"time": "10:30"}]
