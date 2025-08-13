from agents import Agent, Runner, SQLiteSession
from src.my_agents.prompts.system_prompt_noor import SYSTEM_PROMPT
from src.tools.kb_agent_tool import kb_tool_for_noor
from src.tools.booking_agent_tool import (
    suggest_services,
    check_availability,
    suggest_employees,
    create_booking,
    reset_booking,
    revert_to_step,
    update_booking_context,
)
from src.app.context_models import BookingContext
from src.app.output_sanitizer import redact_tokens
from src.workflows.step_controller import StepControllerRunHooks
from src.app.event_log import log_event, set_turn_id


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
    # kb_tool_for_noor() returns a list of tools. Combine it with the booking
    # tool functions and ``update_booking_context`` so ``Agent`` receives a flat
    # list of Tool objects.
    tools = [
        update_booking_context,
        *kb_tool_for_noor(),
        suggest_services,
        check_availability,
        suggest_employees,
        create_booking,
        reset_booking,
        revert_to_step,
    ]

    return Agent(name="Noor", instructions=instructions, model="gpt-4o", tools=tools)


async def run_noor_turn(
    *,
    user_input: str,
    ctx: BookingContext,
    session: SQLiteSession,
) -> str:
    turn_id = len(await session.get_items())
    set_turn_id(turn_id)
    log_event("user_text", {"text": user_input})

    noor = _build_noor_agent(ctx)
    hooks = StepControllerRunHooks()
    result = await Runner.run(
        starting_agent=noor,
        input=user_input,
        session=session,
        context=ctx,
        hooks=hooks,
    )

    log_event("intent", {"next_booking_step": str(ctx.next_booking_step)})
    return redact_tokens(result.final_output)
