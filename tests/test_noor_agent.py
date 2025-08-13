from src.my_agents.noor_agent import _build_noor_agent
from src.app.context_models import BookingContext

def test_noor_agent_tools_are_flat():
    agent = _build_noor_agent(BookingContext())
    assert all(not isinstance(t, list) for t in agent.tools)
