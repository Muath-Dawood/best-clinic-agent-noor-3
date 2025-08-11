import io
import json
from datetime import datetime
from typing import List
import pytz
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from agents import Agent, Runner, SQLiteSession, ItemHelpers, RunConfig

TZ_NAME = "Asia/Jerusalem"
tz = pytz.timezone(TZ_NAME)


class ChatSummary(BaseModel):
    user_id: str
    user_name: str | None
    user_phone: str | None
    start_time_iso: str
    end_time_iso: str
    language: str
    intents: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    booking_status: str = "none"
    next_best_action: str = ""
    free_text: str = ""


summarizer = Agent(
    name="Noor summarizer",
    instructions=(
        """
        Summarize a WhatsApp conversation between a clinic assistant and a user into a concise, actionable note for long-term memory.

        RULES
        - WhatsApp text flow only: do NOT mention files/uploads unless explicitly present in messages.
        - Factual only; no PHI beyond name/phone. No speculation. Do not invent prices or diagnoses.
        - language ∈ {"ar","en"} — infer from the latest user messages.
        - booking_status ∈ {"none","suggested","in_progress","confirmed","failed"} (lowercase exact).
        - intents: 1-5 items — plain phrases (no leading dashes/numbers/emojis).
        - key_points: 1-5 items — concrete facts exchanged (no duplicates; no bullets/numbering/emojis).
        - next_best_action: 0-1 sentence, imperative, ≤ 90 chars, no emoji.
        - free_text: 3-6 neutral sentences (non-salesy, not user-facing).
        - Ignore tool/system traces unless they carry user-visible content; prefer the user's latest statements.
        - If chat is trivial (greetings/thanks only), leave lists empty; booking_status="none".
    """
    ),
    output_type=ChatSummary,
    model="gpt-4o-mini",
)


def _guess_language(items: List[dict]) -> str:
    for msg in reversed(items):
        if msg.get("role") == "user":
            text = ItemHelpers.extract_last_text(msg) or ""
            if any("\u0600" <= ch <= "\u06ff" for ch in text):
                return "ar"
            if any("a" <= ch.lower() <= "z" for ch in text):
                return "en"
    return "unknown"


def _extract_times(items: List[dict], tz) -> tuple[datetime, datetime]:
    """
    Find earliest & latest timestamps in session items.
    Looks for common keys and falls back to 'now' if none found.
    """

    def _parse_dt(v):
        # epoch seconds
        if isinstance(v, (int, float)):
            try:
                return datetime.fromtimestamp(float(v))
            except Exception:
                return None
        # ISO 8601 strings (handle 'Z')
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    collected = []
    for it in items:
        for key in ("created_at", "timestamp", "time", "ts"):
            dt = _parse_dt(it.get(key))
            if dt:
                # normalize to your tz
                if dt.tzinfo is None:
                    try:
                        dt = tz.localize(dt)  # pytz-aware
                    except Exception:
                        dt = dt.replace(tzinfo=tz)  # last resort
                else:
                    dt = dt.astimezone(tz)
                collected.append(dt)

    now = datetime.now(tz)
    if not collected:
        return now, now
    return min(collected), max(collected)


async def build_summary(
    *,
    user_id: str,
    user_name: str | None,
    user_phone: str | None,
    session: SQLiteSession,
) -> ChatSummary:
    items = await session.get_items()
    if not items:
        now = datetime.now(tz).isoformat()
        return ChatSummary(
            user_id=user_id,
            user_name=user_name,
            user_phone=user_phone,
            start_time_iso=now,
            end_time_iso=now,
            language="unknown",
        )

    lang = _guess_language(items)
    result = await Runner.run(
        summarizer,
        input=items,
        run_config=RunConfig(trace_include_sensitive_data=False),
    )
    s: ChatSummary = result.final_output
    s.user_id = user_id
    s.user_name = user_name
    s.user_phone = user_phone
    s.language = lang
    start_dt, end_dt = _extract_times(items, tz)
    s.start_time_iso = start_dt.isoformat()
    s.end_time_iso = end_dt.isoformat()
    return s


async def save_summary_to_vector_store(
    *, vector_store_id: str, summary: ChatSummary
) -> str:
    client = AsyncOpenAI()
    meta = {
        "user_id": summary.user_id,
        "user_name": summary.user_name,
        "user_phone": summary.user_phone,
        "language": summary.language,
        "start_time_iso": summary.start_time_iso,
        "end_time_iso": summary.end_time_iso,
        "booking_status": summary.booking_status,
        "type": "noor_chat_summary",
        "tz": TZ_NAME,
        "version": "v1",
    }
    body = [
        "---",
        json.dumps(meta, ensure_ascii=False),
        "---\n",
        "# Chat summary\n",
        "## Intents\n",
        *[f"- {b}" for b in summary.intents],
        "\n## Key points\n",
        *[f"- {b}" for b in summary.key_points],
        "\n## Next best action\n",
        summary.next_best_action.strip(),
        "\n\n## Recap\n",
        summary.free_text.strip(),
    ]
    text = "\n".join(body).encode("utf-8")
    file_obj = io.BytesIO(text)
    file_obj.name = (
        f"noor_summary_{summary.user_id}_{summary.end_time_iso.replace(':','-')}.md"
    )
    uploaded = await client.vector_stores.files.upload_and_poll(
        vector_store_id=vector_store_id,
        file=file_obj,
    )
    return uploaded.id
