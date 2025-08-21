import json
import pytest
from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import suggest_employees, create_booking
import src.tools.booking_tool as booking_tool_module
from src.workflows.step_controller import StepController


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_recover_after_conflict_allows_new_time(monkeypatch):
    ctx = BookingContext(
        selected_services_pm_si=["svcF"],
        appointment_date="2025-08-25",
        available_times=[{"time": "10:00"}, {"time": "12:00"}],
        subject_gender="female",
        booking_for_self=False,
        subject_name="الزوجة",
        subject_phone="0591111111",
    )

    StepController(ctx).apply_patch({})

    async def fake_emps(d, t, svcs, g):
        assert t in ("10:00", "12:00")
        return ([{"pm_si": "empF", "name": "د. خديجة"}], {"total_price": 100})

    monkeypatch.setattr(
        booking_tool_module.booking_tool, "get_available_employees", fake_emps
    )

    res = await suggest_employees.on_invoke_tool(W(ctx), json.dumps({"time": "10:00"}))
    assert "offered_employees" in res.ctx_patch
    StepController(ctx).apply_patch(res.ctx_patch)

    async def fake_create(*a, **kw):
        return {"result": False, "error_code": "CONFLICT"}

    monkeypatch.setattr(booking_tool_module.booking_tool, "create_booking", fake_create)

    async def fresh_times(d, svcs, g):
        return [{"time": "12:00"}]

    monkeypatch.setattr(
        booking_tool_module.booking_tool, "get_available_times", fresh_times
    )

    res = await create_booking.on_invoke_tool(W(ctx), json.dumps({}))
    p = res.ctx_patch
    assert p.get("appointment_time") is None
    assert p.get("employee_pm_si") is None
    assert p.get("available_times") == [{"time": "12:00"}]
    StepController(ctx).apply_patch(p, invalidate=False)

    res2 = await suggest_employees.on_invoke_tool(W(ctx), json.dumps({"time": "12:00"}))
    assert "offered_employees" in res2.ctx_patch
