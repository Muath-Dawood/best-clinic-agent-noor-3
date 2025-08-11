from __future__ import annotations
import os
from typing import Optional, Tuple, List
from agents import Agent, Runner, FileSearchTool, RunConfig, ModelSettings
from src.app.logging import get_logger

logger = get_logger("noor.prefetch")

VS_SUMM = os.getenv("VECTOR_STORE_ID_SUMMARIES", "").strip()
PREFETCH_SUMMARY_COUNT = int(os.getenv("PREFETCH_SUMMARY_COUNT", "3"))
MAX_PREFETCH_CHARS = int(os.getenv("MAX_PREFETCH_CHARS", "8000"))


def _build_summaries_tool():
    if not VS_SUMM:
        return None
    return FileSearchTool(vector_store_ids=[VS_SUMM])


# Agent that MUST fetch via FileSearch and return N summaries separated by a delimiter.
_prefetch_agent = Agent(
    name="NoorMemoryFetcher",
    instructions=(
        "You MUST call the FileSearch tool exactly once to retrieve chat summaries.\n"
        "Filter: type=noor_chat_summary AND user_id=<given> (and user_phone if provided).\n"
        "Sort by end_time_iso DESC and return up to N items.\n"
        "OUTPUT CONTRACT (strict):\n"
        "- Return ONLY the body text (not the YAML front matter) of each summary, in order.\n"
        "- Separate summaries by a single line containing exactly: ---\n"
        "- If no results, return an empty string.\n"
        "- Do NOT add any commentary, headers, or tool mentions."
    ),
    tools=[t for t in [_build_summaries_tool()] if t],
    model="gpt-4o-mini",
)


async def fetch_recent_summaries_text(
    *, user_id: str, user_phone: Optional[str], limit: int = PREFETCH_SUMMARY_COUNT
) -> Tuple[List[str], str]:
    """Returns (parts, combined_text). parts are individual summary bodies."""
    if not VS_SUMM:
        logger.info("prefetch: summaries store not configured; skipping")
        return [], ""

    # Construct a strict query for the summaries store
    q_bits = ["type:noor_chat_summary", f"user_id:{user_id}"]
    if user_phone:
        q_bits.append(f"user_phone:{user_phone}")
    # Ask the fetcher to pull at most {limit}
    query = " ".join(q_bits) + f" sort:desc end_time_iso limit:{limit}"

    # Nudge the agent to use the tool and obey the delimiter contract
    prompt = (
        f"N={limit}\n"
        f"Query: {query}\n"
        "Return ONLY the body texts separated by a line '---' (no quotes). "
        "If none, return an empty string."
    )

    res = await Runner.run(
        _prefetch_agent,
        input=prompt,
        run_config=RunConfig(model_settings=ModelSettings(tool_choice="required")),
    )
    raw = (res.final_output or "").strip()

    if not raw:
        logger.info(f"prefetch: no summaries found for {user_id}")
        return [], ""

    # Split on the delimiter we mandated
    parts = [p.strip() for p in raw.split("\n---\n") if p.strip()]
    # Enforce limit and char budget
    parts = parts[: max(1, limit)]
    combined = "\n\n---\n\n".join(parts)
    if len(combined) > MAX_PREFETCH_CHARS:
        combined = (
            combined[:MAX_PREFETCH_CHARS].rsplit("\n", 1)[0].strip()
        )  # cut at a line boundary

    logger.info(
        f"prefetch: fetched {len(parts)} summaries for {user_id} "
        f"(chars={len(combined)}, limit={limit})"
    )
    # Small preview to confirm it’s the right data (first 120 chars)
    if combined:
        logger.info("prefetch: preview: " + combined[:120].replace("\n", " ") + " …")

    return parts, combined
