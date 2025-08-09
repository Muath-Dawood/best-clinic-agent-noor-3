import os
from dotenv import load_dotenv
from agents import Agent, Runner, ModelSettings, FileSearchTool
from .prompts.system_prompt_noor import SYSTEM_PROMPT

load_dotenv()

_vector_store_id = os.getenv("VECTOR_STORE_ID")

tools = []
if _vector_store_id:
    tools.append(FileSearchTool(vector_store_ids=[_vector_store_id]))

noor = Agent(
    name="Noor",
    instructions=SYSTEM_PROMPT,
    model="gpt-4o",
    tools=tools,
    model_settings=ModelSettings(temperature=0.3),
)


async def run_noor_turn(user_input: str) -> str:
    result = await Runner.run(starting_agent=noor, input=user_input)
    return result.final_output
