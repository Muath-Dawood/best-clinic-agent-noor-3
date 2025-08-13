import json
import pytest

from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import (
    update_booking_context,
    BookingContextUpdate,
    revert_to_step,
)
from src.workflows.step_controller import StepController


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


def test_apply_patch_sets_next_step():
    ctx = BookingContext()
    controller = StepController(ctx)
    controller.apply_patch({"selected_services_pm_si": ["svc1"], "next_booking_step": BookingStep.SELECT_EMPLOYEE})
    assert ctx.next_booking_step == BookingStep.SELECT_DATE
    controller.apply_patch(
        {
            "appointment_date": "2024-06-01",
            "available_times": [{"time": "09:00"}],
        }
    )
    assert ctx.next_booking_step == BookingStep.SELECT_TIME


def test_apply_patch_rejects_downstream_fields():
    ctx = BookingContext()
    controller = StepController(ctx)
    with pytest.raises(ValueError):
        controller.apply_patch({"appointment_date": "2024-06-01"})


@pytest.mark.asyncio
async def test_revert_to_step_clears_downstream_fields():
    ctx = BookingContext(
        selected_services_pm_si=["svc1"],
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
        selected_services_pm_si=["svc1"],
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
