from src.app.context_models import BookingContext
from agents import Agent, Runner, SQLiteSession
from .prompts.system_prompt_noor import SYSTEM_PROMPT

# from src.tools import get_all_tools  # if you already register tools

noor = Agent(
    name="Noor",
    instructions=SYSTEM_PROMPT,
    model="gpt-4o",
    # tools=get_all_tools(),  # keep or add later
)


async def run_noor_turn(
    *, user_input: str, ctx: BookingContext, session: SQLiteSession
) -> str:
    result = await Runner.run(
        starting_agent=noor,
        input=user_input,
        session=session,  # ← chat history
        context=ctx,  # ← your per-user state
    )
    return result.final_output
