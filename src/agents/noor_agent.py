import os
from agents import Agent, Runner, ModelSettings, WebSearchTool, FileSearchTool  # from openai-agents
from .prompts.system_prompt_noor import SYSTEM_PROMPT

# NOTE: FileSearchTool will use your OpenAI Vector Store
# Make sure VECTOR_STORE_ID is present in your environment (see .env.example)

_vector_store_id = os.getenv("VECTOR_STORE_ID")

# Tools: you can add WebSearchTool() later if you want time-sensitive browsing.
tools = []
if _vector_store_id:
    tools.append(FileSearchTool(vector_store_ids=[_vector_store_id]))

noor = Agent(
    name="Noor",
    instructions=SYSTEM_PROMPT,
    model="gpt-4o-mini",
    tools=tools,
    model_settings=ModelSettings(temperature=0.3),
)

async def run_noor_turn(user_input: str) -> str:
    result = await Runner.run(starting_agent=noor, input=user_input)
    return result.final_output
