import json, pytest
from src.app.context_models import BookingContext, BookingStep
from src.workflows.step_controller import StepController
from src.tools.booking_agent_tool import update_booking_context, check_availability, suggest_employees, create_booking
import src.tools.booking_tool as booking_tool_module


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_proxy_booking_wife_new_user_flow(monkeypatch):
    # Existing male chat owner with DB record
    ctx = BookingContext(
        user_name="عبدالله",
        user_phone="0591111111",
        gender="male",
        customer_pm_si="pm-owner-123",
        booking_for_self=True,
    )

    # Switch to booking for wife
    res = await update_booking_context.on_invoke_tool(W(ctx), json.dumps({
        "updates": {
            "booking_for_self": False,
            "subject_gender": "female",
            "subject_name": "أم عبدالله",
            "subject_phone": "0592222222",
            "selected_services_pm_si": ["استشارة طبية - قسم النسائية"]
        }
    }))
    StepController(ctx).apply_patch(res.ctx_patch)
    assert ctx.booking_for_self is False
    # availability uses subject gender (female)
    async def fake_times(date, services, gender):
        assert gender == "female"
        return [{"time":"12:00"}]
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_times", fake_times)

    res = await check_availability.on_invoke_tool(W(ctx), json.dumps({"date":"2025-09-01"}))
    StepController(ctx).apply_patch(res.ctx_patch)
    assert ctx.available_times and ctx.next_booking_step == BookingStep.SELECT_TIME

    async def fake_emps(date, time, services, gender):
        assert gender == "female"
        return ([{"pm_si":"empF","name":"دكتورة مريم"}], {"total_price":100})
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_employees", fake_emps)

    res = await suggest_employees.on_invoke_tool(W(ctx), json.dumps({"time":"12:00"}))
    StepController(ctx).apply_patch(res.ctx_patch)
    assert ctx.employee_pm_si is None and ctx.offered_employees

    # Create booking -> must NOT use owner's customer_pm_si
    called = {"payload": None}
    async def fake_create(date, time, emp, svcs, customer_pm_si, gender, idempotency_key=None, **kw):
        called["payload"] = {"customer_pm_si":customer_pm_si, "gender":gender, "svcs":svcs, "emp":emp}
        return {"result": True}
    monkeypatch.setattr(booking_tool_module.booking_tool, "create_booking", fake_create)

    res = await create_booking.on_invoke_tool(W(ctx), json.dumps({}))
    assert res.ctx_patch.get("booking_confirmed") is True
    assert called["payload"]["customer_pm_si"] is None      # <-- critical: no owner pm_si
    assert called["payload"]["gender"] == "female"          # uses subject gender
