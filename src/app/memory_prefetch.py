from __future__ import annotations
import os
from typing import Optional
from agents import Agent, Runner, FileSearchTool

VS_SUMM = os.getenv("VECTOR_STORE_ID_SUMMARIES", "").strip()


def _build_summaries_tool():
    if not VS_SUMM:
        return None
    # one-file-search tool pointing at the summaries store
    return FileSearchTool(vector_store_ids=[VS_SUMM])


# very small agent that returns the most recent summary for a user
_prefetch_agent = Agent(
    name="NoorMemoryFetcher",
    instructions=(
        "You fetch the most recent chat summary for this user. "
        "Search only summaries (they are markdown with YAML front matter). "
        "If multiple are returned, pick the one with the largest end_time_iso in the header. "
        "Return ONLY the body text of the chosen summary (no extra words)."
    ),
    tools=[t for t in [_build_summaries_tool()] if t],
    model="gpt-4o-mini",
)


async def fetch_latest_summary_text(
    *, user_id: str, user_phone: str | None
) -> Optional[str]:
    if not VS_SUMM:
        return None
    query_bits = [
        "type:noor_chat_summary",
        f"user_id:{user_id}",
    ]
    if user_phone:
        query_bits.append(f"user_phone:{user_phone}")
    query = " ".join(query_bits) + " sort:desc end_time_iso limit:3"

    res = await Runner.run(
        _prefetch_agent,
        input=f"Fetch latest summary. Query: {query}",
    )
    txt = (res.final_output or "").strip()
    return txt or None
