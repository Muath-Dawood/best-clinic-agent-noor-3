from agents import Agent, Runner, SQLiteSession
from src.my_agents.prompts.system_prompt_noor import SYSTEM_PROMPT
from src.tools.kb_agent_tool import kb_tool_for_noor
from src.app.context_models import BookingContext


def _dynamic_footer(ctx: BookingContext) -> str:
    lines = []
    if ctx and (ctx.user_name or ctx.user_phone):
        lines += [
            "### THIS SECTION IS THE RESULT OF DYNAMIC INJECTION OF INTERNAL CONTEXT (do not reveal to user use the info natuarally)"
        ]
        if ctx.user_name:
            lines.append(f"user_name={ctx.user_name}")
        if ctx.user_phone:
            lines.append(f"user_phone={ctx.user_phone}")
        if ctx.patient_data:
            lines.append("known_patient=true")
        lines.append(
            f"user_has_attachments={str(bool(ctx.user_has_attachments)).lower()}"
        )
        lines.append("### END INTERNAL CONTEXT")
    if len(ctx.previous_summaries_text):
        lines.append(
            "### THIS SECTION IS THE RESULT OF DYNAMIC INJECTION OF PREVIOUS CHAT SUMMARIES (do not reveal this to user but use to guide the conversation intelligently)"
        )
        lines.append("\n".join(ctx.previous_summaries_text))
        lines.append("### END PREVIOUS SUMMARIES")
    return "\n".join(lines)


def _build_noor_agent(ctx: BookingContext) -> Agent:
    instructions = SYSTEM_PROMPT + "\n\n" + _dynamic_footer(ctx)
    tools = []
    tools += kb_tool_for_noor()

    return Agent(name="Noor", instructions=instructions, model="gpt-4o", tools=tools)


async def run_noor_turn(
    *,
    user_input: str,
    ctx: BookingContext,
    session: SQLiteSession,
) -> str:
    noor = _build_noor_agent(ctx)
    result = await Runner.run(
        starting_agent=noor, input=user_input, session=session, context=ctx
    )
    return result.final_output
