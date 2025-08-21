import json
import pytest
from src.app.context_models import BookingContext
from src.tools.booking_agent_tool import update_booking_context
from src.workflows.step_controller import StepController


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_invalidation_persists_without_revert():
    ctx = BookingContext(
        selected_services_pm_si=["svc1"],
        appointment_date="2025-09-01",
        available_times=[{"time": "10:00"}],
        appointment_time="10:00",
        offered_employees=[{"pm_si": "emp1", "name": "Dr A"}],
        employee_pm_si="emp1",
    )
    body = json.dumps({"updates": {"selected_services_pm_si": ["svc2"]}})
    res = await update_booking_context.on_invoke_tool(W(ctx), body)
    p = res.ctx_patch
    assert p.get("appointment_date") is None
    assert p.get("appointment_time") is None
    assert p.get("offered_employees") is None
    assert p.get("employee_pm_si") is None
