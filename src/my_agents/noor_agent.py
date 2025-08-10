from agents import Agent, Runner, SQLiteSession
from src.my_agents.prompts.system_prompt_noor import SYSTEM_PROMPT
from src.tools.file_search import build_file_search_tool
from src.app.context_models import BookingContext

# Build the retrieval tool if VECTOR_STORE_ID is set
_tools = [t for t in [build_file_search_tool()] if t]

noor = Agent(
    name="Noor",
    instructions=SYSTEM_PROMPT,
    model="gpt-4o",
    tools=_tools,
)


async def run_noor_turn(
    *, user_input: str, ctx: BookingContext, session: SQLiteSession
) -> str:
    result = await Runner.run(
        starting_agent=noor,
        input=user_input,
        session=session,  # keeps chat history
        context=ctx,  # passes enriched context
    )
    return result.final_output
