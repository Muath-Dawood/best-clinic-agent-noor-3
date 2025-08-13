import json
import pytest

import src.tools.booking_agent_tool as booking_agent_tool_module
from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import (
    update_booking_context,
    BookingContextUpdate,
    revert_to_step,
    check_availability,
    suggest_employees,
)
from src.workflows.step_controller import StepController
from src.data.services import MEN_SERVICES

# Use a real service token for tests instead of placeholder values
CANONICAL_SERVICE_TOKEN = MEN_SERVICES[0]["pm_si"]


class DummyWrapper:
    def __init__(self, ctx: BookingContext | None = None):
        self.context = ctx or BookingContext()


@pytest.mark.asyncio
async def test_update_booking_context_ignores_next_step():
    """If ``next_booking_step`` is provided, it should simply be ignored."""
    wrapper = DummyWrapper()
    updates = BookingContextUpdate(next_booking_step=BookingStep.SELECT_DATE)
    payload = json.dumps({"updates": updates.model_dump()})
    result = await update_booking_context.on_invoke_tool(wrapper, payload)
    assert result.ctx_patch == {}
    # Should return generic message indicating no updates were applied
    assert "لم يتم" in result.public_text


@pytest.mark.asyncio
async def test_update_booking_context_defers_without_service():
    wrapper = DummyWrapper()
    updates = BookingContextUpdate(
        appointment_date="2024-06-01", appointment_time="10:00"
    )
    payload = json.dumps({"updates": updates.model_dump()})
    result = await update_booking_context.on_invoke_tool(wrapper, payload)
    assert result.ctx_patch == {}
    assert "لا يمكن تحديد التاريخ" in result.public_text
    assert "لا يمكن تحديد الوقت" in result.public_text


def test_apply_patch_sets_next_step():
    ctx = BookingContext()
    controller = StepController(ctx)
    controller.apply_patch(
        {
            "selected_services_pm_si": [CANONICAL_SERVICE_TOKEN],
            "next_booking_step": BookingStep.SELECT_EMPLOYEE,
        }
    )
    assert ctx.next_booking_step == BookingStep.SELECT_DATE
    controller.apply_patch(
        {
            "appointment_date": "2024-06-01",
            "available_times": [{"time": "09:00"}],
        }
    )
    assert ctx.next_booking_step == BookingStep.SELECT_TIME
    controller.apply_patch(
        {
            "appointment_time": "09:00",
            "available_times": [{"time": "09:00"}],
            "appointment_date": "2024-06-01",
            "offered_employees": [{"pm_si": "emp1"}],
        }
    )
    assert ctx.next_booking_step == BookingStep.SELECT_EMPLOYEE
    controller.apply_patch({"employee_pm_si": "emp1"})
    assert ctx.next_booking_step is None


def test_apply_patch_rejects_downstream_fields():
    ctx = BookingContext()
    controller = StepController(ctx)
    with pytest.raises(ValueError):
        controller.apply_patch({"appointment_date": "2024-06-01"})


@pytest.mark.asyncio
async def test_revert_to_step_clears_downstream_fields():
    ctx = BookingContext(
        selected_services_pm_si=[CANONICAL_SERVICE_TOKEN],
        appointment_date="2024-06-01",
        appointment_time="10:00",
        employee_pm_si="emp1",
        employee_name="Dr. X",
    )
    wrapper = DummyWrapper(ctx)
    payload = json.dumps({"step": "select_date"})
    result = await revert_to_step.on_invoke_tool(wrapper, payload)
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.appointment_date is None
    assert ctx.appointment_time is None
    assert ctx.employee_pm_si is None
    assert ctx.next_booking_step == BookingStep.SELECT_DATE
    assert "اختيار التاريخ" in result.public_text


@pytest.mark.asyncio
async def test_update_booking_context_invalidates_downstream():
    ctx = BookingContext(
        selected_services_pm_si=[CANONICAL_SERVICE_TOKEN],
        appointment_date="2024-06-01",
        appointment_time="09:00",
        employee_pm_si="emp1",
    )
    wrapper = DummyWrapper(ctx)
    updates = BookingContextUpdate(appointment_date="2024-06-05")
    payload = json.dumps({"updates": updates.model_dump()})
    result = await update_booking_context.on_invoke_tool(wrapper, payload)
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.available_times is None
    assert ctx.appointment_time is None
    assert ctx.employee_pm_si is None
    assert ctx.offered_employees is None
    assert ctx.checkout_summary is None
    assert "الأوقات المتاحة" in result.public_text
    assert "الأطباء المقترحين" in result.public_text
    assert "ملخص الحجز" in result.public_text
    assert "اختيار الوقت والطبيب" in result.public_text


@pytest.mark.asyncio
async def test_check_availability_stores_available_times(monkeypatch):
    ctx = BookingContext(selected_services_pm_si=[MEN_SERVICES[0]["pm_si"]])
    StepController(ctx).apply_patch({})
    wrapper = DummyWrapper(ctx)

    slots = [{"time": "09:00"}, {"time": "10:00"}]

    async def fake_slots(date, services, gender):
        return slots

    monkeypatch.setattr(
        booking_agent_tool_module.booking_tool, "get_available_times", fake_slots
    )

    payload = json.dumps({"date": "2024-06-01"})
    result = await check_availability.on_invoke_tool(wrapper, payload)
    assert "next_booking_step" not in result.ctx_patch
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.available_times == slots
    assert ctx.next_booking_step == BookingStep.SELECT_TIME


@pytest.mark.asyncio
async def test_check_availability_no_slots_prevents_progress(monkeypatch):
    ctx = BookingContext(selected_services_pm_si=[MEN_SERVICES[0]["pm_si"]])
    StepController(ctx).apply_patch({})
    wrapper = DummyWrapper(ctx)

    async def fake_slots(date, services, gender):
        return []

    monkeypatch.setattr(
        booking_agent_tool_module.booking_tool, "get_available_times", fake_slots
    )

    payload = json.dumps({"date": "2024-06-01"})
    result = await check_availability.on_invoke_tool(wrapper, payload)
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.available_times is None
    assert ctx.next_booking_step == BookingStep.SELECT_DATE
    assert "لا توجد أوقات متاحة" in result.public_text


@pytest.mark.asyncio
async def test_suggest_employees_respects_available_times_and_populates(monkeypatch):
    ctx = BookingContext(
        selected_services_pm_si=[CANONICAL_SERVICE_TOKEN],
        appointment_date="2024-06-01",
        available_times=[{"time": "09:00"}],
    )
    StepController(ctx).apply_patch({})
    wrapper = DummyWrapper(ctx)

    # Unavailable time should be rejected
    payload = json.dumps({"time": "10:00"})
    result = await suggest_employees.on_invoke_tool(wrapper, payload)
    assert result.ctx_patch == {}
    assert "غير متاح" in result.public_text
    assert ctx.appointment_time is None
    assert ctx.next_booking_step == BookingStep.SELECT_TIME

    employees = [{"pm_si": "emp1", "name": "Dr. X"}]
    norm_employees = [{"pm_si": "emp1", "name": "Dr. X", "display": "Dr. X"}]
    summary = {"price": 100}

    async def fake_emps(date, time, services, gender):
        assert time == "09:00"
        return employees, summary

    monkeypatch.setattr(
        booking_agent_tool_module.booking_tool, "get_available_employees", fake_emps
    )

    payload = json.dumps({"time": "09:00"})
    result = await suggest_employees.on_invoke_tool(wrapper, payload)
    StepController(ctx).apply_patch(result.ctx_patch)
    assert ctx.appointment_time == "09:00"
    assert ctx.offered_employees == norm_employees
    assert ctx.checkout_summary == summary
    assert ctx.next_booking_step == BookingStep.SELECT_EMPLOYEE
