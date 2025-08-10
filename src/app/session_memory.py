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
        "Summarize the conversation between a clinic assistant and a user into a concise, "
        "actionable note for long-term memory. Keep it factual; no PHI beyond name/phone. "
        "Language should be 'ar' or 'en'. booking_status ∈ {none, suggested, in_progress, confirmed, failed}."
    ),
    output_type=ChatSummary,
    model="gpt-4.1-mini",
)


def _guess_language(items: List[dict]) -> str:
    for msg in reversed(items):
        if msg.get("role") == "user":
            text = ItemHelpers.text_from_input_item(msg) or ""
            if any("\u0600" <= ch <= "\u06ff" for ch in text):
                return "ar"
            if any("a" <= ch.lower() <= "z" for ch in text):
                return "en"
    return "unknown"


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
        input=items
        + [
            {
                "role": "developer",
                "content": (
                    "Produce a compact memory of this chat. "
                    "Use concise bullet points for intents/key_points. "
                    "free_text: 3-6 sentences, no user-facing tone."
                ),
            }
        ],
        run_config=RunConfig(trace_include_sensitive_data=False),
    )
    s: ChatSummary = result.final_output
    s.user_id = user_id
    s.user_name = user_name
    s.user_phone = user_phone
    s.language = lang
    now = datetime.now(tz).isoformat()
    s.start_time_iso = now
    s.end_time_iso = now
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
    uploaded = await client.beta.vector_stores.files.upload_and_poll(
        vector_store_id=vector_store_id,
        file=file_obj,
    )
    return uploaded.id
