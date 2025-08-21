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
        gender="male",
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


@pytest.mark.asyncio
async def test_create_booking_no_available_times_single_doctor_no_employee_patch(monkeypatch):
    """Booking should succeed even if available_times is None and employee isn't persisted; tool must not patch employee_*."""
    ctx = BookingContext(
        selected_services_pm_si=["svc1"],
        appointment_date="2025-08-21",
        appointment_time="12:00",
        available_times=None,  # simulate missing list
        offered_employees=[{"pm_si": "emp1", "name": "دكتور مؤمن"}],
        employee_pm_si=None,
        employee_name=None,
        user_name="Tester",
        user_phone="0599000000",
        gender="male",
    )
    ctx.next_booking_step = BookingStep.SELECT_EMPLOYEE

    async def ok_create(date, time, emp, svcs, cust, gender, idempotency_key=None):
        assert emp == "emp1"  # auto-selected
        return {"result": True, "data": {"booking_id": 777}}

    monkeypatch.setattr(booking_tool_module.booking_tool, "create_booking", ok_create)

    res = await create_booking.on_invoke_tool(W(ctx), json.dumps({}))
    assert "تم تأكيد حجزك" in res.public_text
    # Must not include risky employee_* patches
    assert "employee_pm_si" not in res.ctx_patch
    assert "employee_name" not in res.ctx_patch
    assert res.ctx_patch.get("booking_confirmed") is True


@pytest.mark.asyncio
async def test_create_booking_blocks_when_missing_new_customer_info(monkeypatch):
    """For new users, create_booking should ask for name/phone before calling API."""
    called = {"flag": False}

    async def should_not_call(*args, **kwargs):
        called["flag"] = True
        return {"result": True}

    monkeypatch.setattr(booking_tool_module.booking_tool, "create_booking", should_not_call)

    ctx = BookingContext(
        selected_services_pm_si=["svc1"],
        appointment_date="2025-08-22",
        appointment_time="12:00",
        offered_employees=[{"pm_si": "emp1", "name": "Dr. A"}],
        employee_pm_si="emp1",
        gender="female",
        user_name=None,
        user_phone=None,
    )
    ctx.next_booking_step = BookingStep.SELECT_EMPLOYEE

    res = await create_booking.on_invoke_tool(W(ctx), json.dumps({}))
    assert "قبل تأكيد الحجز" in res.public_text
    assert called["flag"] is False


@pytest.mark.asyncio
async def test_create_booking_all_set_and_next_none(monkeypatch):
    ctx = BookingContext(
        selected_services_pm_si=["svc1"],
        appointment_date="2025-08-26",
        appointment_time="12:00",
        offered_employees=[{"pm_si": "emp-1", "name": "دكتور مؤمن"}],
        employee_pm_si="emp-1",
        employee_name="دكتور مؤمن",
        user_name="Tester",
        user_phone="0590000000",
        gender="male",
    )
    # Simulate flow complete
    StepController(ctx).apply_patch({})
    assert ctx.next_booking_step is None  # flow "done" after doctor chosen

    async def fake_emps(date, time, services, gender):
        return ([{"pm_si": "emp-1", "name": "دكتور مؤمن"}], {"total_price": 50})

    async def fake_times(date, services, gender):
        return [{"time": "12:00"}]

    async def fake_create(date, time, emp, services, customer, gender, idempotency_key=None):
        return {"result": True, "data": {"booking_id": "abc123"}}

    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_employees", fake_emps)
    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_times", fake_times)
    monkeypatch.setattr(booking_tool_module.booking_tool, "create_booking", fake_create)

    wrapper = type("W", (), {"context": ctx})()
    result = await create_booking.on_invoke_tool(wrapper, json.dumps({}))
    assert "تم تأكيد الحجز" in result.public_text or result.ctx_patch.get("booking_confirmed") is True
