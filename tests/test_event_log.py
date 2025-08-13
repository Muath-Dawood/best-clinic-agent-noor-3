import json
import pytest

from src.app.event_log import set_log_path, set_turn_id, get_log_path
from src.workflows.step_controller import StepControllerRunHooks
from src.app.context_models import BookingContext
from src.tools.tool_result import ToolResult


class DummyWrapper:
    def __init__(self):
        self.context = BookingContext()


class DummyTool:
    name = "dummy_tool"


@pytest.mark.asyncio
async def test_tool_call_and_step_transition_logged(tmp_path):
    log_file = tmp_path / "events.jsonl"
    set_log_path(log_file)
    set_turn_id(1)

    hooks = StepControllerRunHooks()
    wrapper = DummyWrapper()
    tool = DummyTool()
    result = ToolResult(
        public_text="ok",
        ctx_patch={"selected_services_pm_si": ["svc1"]},
        version=wrapper.context.version,
    )

    await hooks.on_tool_end(wrapper, None, tool, result)

    with open(get_log_path(), "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    assert any(e["event"] == "tool_call" for e in events)
    assert any(e["event"] == "step_transition" for e in events)
    assert all(e["turn_id"] == 1 for e in events)
