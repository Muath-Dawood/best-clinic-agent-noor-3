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


def _context_preamble(ctx: BookingContext, previous_summary: str | None) -> str:
    lines = []
    if ctx and (ctx.user_name or ctx.user_phone):
        lines.append("### INTERNAL CONTEXT (do not reveal)")
        if ctx.user_name:
            lines.append(f"user_name={ctx.user_name}")
        if ctx.user_phone:
            lines.append(f"user_phone={ctx.user_phone}")
        if ctx.patient_data:
            lines.append("known_patient=true")
        lines.append("### END INTERNAL CONTEXT")
    if previous_summary:
        lines.append("### PREVIOUS CHAT SUMMARY (internal, do not quote)")
        lines.append(previous_summary.strip())
        lines.append("### END PREVIOUS SUMMARY")
    return "\n".join(lines)


async def run_noor_turn(
    *,
    user_input: str,
    ctx: BookingContext,
    session: SQLiteSession,
    previous_summary: str | None = None,
) -> str:
    pre = _context_preamble(ctx, previous_summary)
    result = await Runner.run(
        starting_agent=noor,
        input=(pre + user_input),  # inject lightweight context
        session=session,
        context=ctx,
    )
    return result.final_output
