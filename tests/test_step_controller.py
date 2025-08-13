import json
import pytest

from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import update_booking_context, BookingContextUpdate
from src.workflows.step_controller import StepController


class DummyWrapper:
    def __init__(self, ctx: BookingContext | None = None):
        self.context = ctx or BookingContext()


@pytest.mark.asyncio
async def test_update_booking_context_rejects_next_step():
    wrapper = DummyWrapper()
    updates = BookingContextUpdate(next_booking_step=BookingStep.SELECT_DATE)
    payload = json.dumps({"updates": updates.model_dump()})
    result = await update_booking_context.on_invoke_tool(wrapper, payload)
    assert result.ctx_patch == {}
    assert "لا يمكن" in result.public_text


def test_apply_patch_sets_next_step():
    ctx = BookingContext()
    controller = StepController(ctx)
    controller.apply_patch({"selected_services_pm_si": ["svc1"], "next_booking_step": BookingStep.SELECT_EMPLOYEE})
    assert ctx.next_booking_step == BookingStep.SELECT_DATE
    controller.apply_patch({"appointment_date": "2024-06-01"})
    assert ctx.next_booking_step == BookingStep.SELECT_TIME


def test_apply_patch_rejects_downstream_fields():
    ctx = BookingContext()
    controller = StepController(ctx)
    with pytest.raises(ValueError):
        controller.apply_patch({"appointment_date": "2024-06-01"})
