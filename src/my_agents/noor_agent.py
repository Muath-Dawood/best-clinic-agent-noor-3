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


def _context_preamble(ctx: BookingContext) -> str:
    if not ctx:
        return ""
    parts = []
    if ctx.user_name:
        parts.append(f"user_name={ctx.user_name}")
    if ctx.user_phone:
        parts.append(f"user_phone={ctx.user_phone}")
    if ctx.patient_data:
        parts.append("known_patient=true")
    if not parts:
        return ""
    return (
        "### INTERNAL CONTEXT (do not reveal; you can use naturally in conversation e.g. name for greeting)\n"
        + "\n".join(parts)
        + "\n### END INTERNAL CONTEXT\n"
    )


async def run_noor_turn(
    *, user_input: str, ctx: BookingContext, session: SQLiteSession
) -> str:
    pre = _context_preamble(ctx)
    result = await Runner.run(
        starting_agent=noor,
        input=(pre + user_input),  # inject lightweight context
        session=session,
        context=ctx,
    )
    return result.final_output
