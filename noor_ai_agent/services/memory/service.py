"""
Memory service for handling conversation summaries and memory.
"""

import io
import json
from datetime import datetime
from typing import List, Optional
import pytz
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from agents import Agent, Runner, SQLiteSession, ItemHelpers, RunConfig

from ...core.models.chat import ChatSummary, ChatMessage
from ...core.enums import Language, BookingStatus
from ...config import get_settings


class MemoryService:
    """Service for handling conversation memory and summaries."""

    def __init__(self):
        self.settings = get_settings()
        self.tz = pytz.timezone(self.settings.timezone)
        self.summarizer = self._create_summarizer()

    def _create_summarizer(self) -> Agent:
        """Create the conversation summarizer agent."""
        return Agent(
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

    def _guess_language(self, items: List[dict]) -> Language:
        """Guess language from conversation items."""
        for msg in reversed(items):
            if msg.get("role") == "user":
                text = ItemHelpers.extract_last_text(msg) or ""
                if any("\u0600" <= ch <= "\u06ff" for ch in text):
                    return Language.ARABIC
                if any("a" <= ch.lower() <= "z" for ch in text):
                    return Language.ENGLISH
        return Language.UNKNOWN

    def _extract_times(self, items: List[dict]) -> tuple[datetime, datetime]:
        """Extract start and end times from conversation items."""
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
                    # normalize to timezone
                    if dt.tzinfo is None:
                        try:
                            dt = self.tz.localize(dt)
                        except Exception:
                            dt = dt.replace(tzinfo=self.tz)
                    else:
                        dt = dt.astimezone(self.tz)
                    collected.append(dt)

        now = datetime.now(self.tz)
        if not collected:
            return now, now
        return min(collected), max(collected)

    async def build_summary(
        self,
        *,
        user_id: str,
        user_name: Optional[str],
        user_phone: Optional[str],
        session: SQLiteSession,
    ) -> ChatSummary:
        """Build conversation summary from session items."""
        items = await session.get_items()
        if not items:
            now = datetime.now(self.tz).isoformat()
            return ChatSummary.create_empty(user_id, user_name, user_phone)

        lang = self._guess_language(items)
        result = await Runner.run(
            self.summarizer,
            input=items,
            run_config=RunConfig(trace_include_sensitive_data=False),
        )
        s: ChatSummary = result.final_output
        s.user_id = user_id
        s.user_name = user_name
        s.user_phone = user_phone
        s.language = lang
        start_dt, end_dt = self._extract_times(items)
        s.start_time_iso = start_dt.isoformat()
        s.end_time_iso = end_dt.isoformat()
        return s

    async def save_summary_to_vector_store(
        self, *, vector_store_id: str, summary: ChatSummary
    ) -> str:
        """Save summary to vector store for future retrieval."""
        if not self.settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        meta = {
            "user_id": summary.user_id,
            "user_name": summary.user_name,
            "user_phone": summary.user_phone,
            "language": summary.language.value,
            "start_time_iso": summary.start_time_iso,
            "end_time_iso": summary.end_time_iso,
            "booking_status": summary.booking_status.value,
            "type": "noor_chat_summary",
            "tz": self.settings.timezone,
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

    async def fetch_recent_summaries(
        self,
        user_id: str,
        user_phone: Optional[str] = None,
        limit: int = 5
    ) -> List[str]:
        """Fetch recent conversation summaries for context."""
        # This would integrate with the vector store to fetch recent summaries
        # For now, return empty list
        return []
