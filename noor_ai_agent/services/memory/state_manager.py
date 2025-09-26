"""
State manager for persistent conversation state.
"""

import asyncio
import json
import sqlite3
from dataclasses import asdict
from typing import Optional, Tuple

from agents import SQLiteSession
from ...core.models.booking import BookingContext
from ...core.enums import BookingStep
from ...config import get_settings


def _coerce_enums(obj):
    """Recursively convert Enums to raw values for JSON serialization."""
    from enum import Enum

    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _coerce_enums(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_coerce_enums(v) for v in obj]
    return obj


class StateManager:
    """Manages persistent state using SQLite database."""

    def __init__(self):
        self.settings = get_settings()
        self.state_db = self.settings.state_db_path
        self.sessions_db = self.settings.sessions_db_path
        self._lock = asyncio.Lock()

    async def _ensure_table(self) -> None:
        """Ensure the state table exists."""
        def _create_table():
            conn = sqlite3.connect(self.state_db)
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS state (
                        user_id TEXT PRIMARY KEY,
                        ctx TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_create_table)

    async def get_state(
        self, user_id: str
    ) -> Optional[Tuple[BookingContext, SQLiteSession]]:
        """Retrieve stored context and create a session for user_id."""
        await self._ensure_table()

        async with self._lock:
            def _fetch() -> Optional[str]:
                conn = sqlite3.connect(self.state_db)
                try:
                    cur = conn.execute(
                        "SELECT ctx FROM state WHERE user_id = ?", (user_id,)
                    )
                    row = cur.fetchone()
                finally:
                    conn.close()
                return row[0] if row else None

            ctx_json = await asyncio.to_thread(_fetch)

        if ctx_json is None:
            return None

        data = json.loads(ctx_json)
        step = data.get("next_booking_step")
        if isinstance(step, str):
            try:
                data["next_booking_step"] = BookingStep(step)
            except Exception:
                data["next_booking_step"] = None

        ctx = BookingContext(**data)
        session = SQLiteSession(user_id, self.sessions_db)
        return ctx, session

    async def save_state(
        self, user_id: str, ctx: BookingContext, session: SQLiteSession
    ) -> None:
        """Persist context for user_id."""
        await self._ensure_table()
        ctx_json = json.dumps(_coerce_enums(asdict(ctx)))

        async with self._lock:
            def _write() -> None:
                conn = sqlite3.connect(self.state_db)
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO state (user_id, ctx) VALUES (?, ?)",
                        (user_id, ctx_json),
                    )
                    conn.commit()
                finally:
                    conn.close()

            await asyncio.to_thread(_write)

    async def clear_state(self, user_id: str) -> None:
        """Remove stored state and clear the associated session."""
        await self._ensure_table()

        async with self._lock:
            def _delete() -> None:
                conn = sqlite3.connect(self.state_db)
                try:
                    conn.execute("DELETE FROM state WHERE user_id = ?", (user_id,))
                    conn.commit()
                finally:
                    conn.close()

            await asyncio.to_thread(_delete)

        # Clear conversation session (ignore failures)
        try:
            session = SQLiteSession(user_id, self.sessions_db)
            try:
                await session.clear_session()
            finally:
                await session.close()
        except Exception:
            pass
