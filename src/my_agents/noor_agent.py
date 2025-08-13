from agents import Agent, Runner, SQLiteSession
from src.my_agents.prompts.system_prompt_noor import SYSTEM_PROMPT
from src.tools.kb_agent_tool import kb_tool_for_noor
from src.tools.booking_agent_tool import (
    booking_tool_for_noor,
    update_booking_context,
)
from src.app.context_models import BookingContext
from src.app.output_sanitizer import redact_tokens


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
    if ctx.previous_summaries and len(ctx.previous_summaries):
        lines.append(
            "### THIS SECTION IS THE RESULT OF DYNAMIC INJECTION OF PREVIOUS CHAT SUMMARIES (do not reveal this to user but use to guide the conversation intelligently)"
        )
        lines.append("\n".join(ctx.previous_summaries))
        lines.append("### END PREVIOUS SUMMARIES")
    return "\n".join(lines)


def _build_noor_agent(ctx: BookingContext) -> Agent:
    instructions = SYSTEM_PROMPT + "\n\n" + _dynamic_footer(ctx)
    tools = []
    tools += kb_tool_for_noor()
    tools += update_booking_context  # Allow context updates
    tools += booking_tool_for_noor()  # Add booking capabilities

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
    return redact_tokens(result.final_output)
