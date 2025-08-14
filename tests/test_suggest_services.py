import json
import pytest

from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import suggest_services
from src.workflows.step_controller import StepController


class Wrapper:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_suggest_services_patches_only_at_service_step():
    ctx = BookingContext(gender="male")
    res = await suggest_services.on_invoke_tool(Wrapper(ctx), json.dumps({}))
    assert res.ctx_patch and "selected_services_data" in res.ctx_patch

    StepController(ctx).apply_patch({"selected_services_pm_si": ["x"]})
    StepController(ctx).apply_patch(
        {"appointment_date": "2025-08-21", "available_times": [{"time": "09:00"}]}
    )
    assert ctx.next_booking_step == BookingStep.SELECT_TIME

    res2 = await suggest_services.on_invoke_tool(Wrapper(ctx), json.dumps({}))
    assert res2.ctx_patch == {}
    assert "هذه قائمة بالخدمات المتاحة" in res2.public_text
