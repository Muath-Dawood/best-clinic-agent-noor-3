import json, pytest
from src.app.context_models import BookingContext, BookingStep
from src.tools.booking_agent_tool import check_availability
import src.tools.booking_tool as booking_tool_module
import src.tools.booking_agent_tool as booking_agent_tool_module
from src.workflows.step_controller import StepController


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_ar_weekday_variant_al_alef_with_hamza(monkeypatch):
    ctx = BookingContext(selected_services_pm_si=["svc1"], subject_gender="male")
    StepController(ctx).apply_patch({})
    monkeypatch.setattr(booking_agent_tool_module, "find_service_by_pm_si", lambda pm: {"pm_si": pm})
    monkeypatch.setattr(booking_agent_tool_module, "get_services_by_gender", lambda g: [{"pm_si": "svc1"}])

    async def fake_times(date, svcs, gender):
        assert date
        return [{"time": "09:00"}]

    monkeypatch.setattr(booking_tool_module.booking_tool, "get_available_times", fake_times)

    res = await check_availability.on_invoke_tool(W(ctx), json.dumps({"date": "الأثنين القادم"}))
    assert "available_times" in res.ctx_patch
