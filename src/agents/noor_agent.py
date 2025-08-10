import os
from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings, SQLiteSession
from ..app.context_models import BookingContext
from ..tools import get_all_tools
from .prompts.system_prompt_noor import SYSTEM_PROMPT

load_dotenv()

# Vector store IDs
CLINIC_KB_ID = "vs_68958dea7d5c8191946e7f15d1f6c098"
USER_SUMMARIES_ID = "vs_6897cd964ef881918fb69a90dccd18a2"

noor_agent = Agent(
    name="Noor",
    instructions=SYSTEM_PROMPT,
    tools=get_all_tools(),
    model="gpt-4o",
    model_settings=ModelSettings(temperature=0.3),
)


async def run_noor_turn(
    *, user_input: str, context: BookingContext, session: SQLiteSession
) -> str:
    result = await Runner.run(
        starting_agent=noor_agent,
        input=user_input,
        session=session,
        context=context,
    )
    return result.final_output
