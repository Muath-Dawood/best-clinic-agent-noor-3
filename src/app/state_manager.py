"""Persistent state manager backed by SQLite.

The previous implementation kept conversation state in a global
dictionary.  This module stores state in a SQLite database so it can be
shared across processes.  All helpers are asynchronous and use
``asyncio.Lock`` together with ``asyncio.to_thread`` to perform the
blocking SQLite operations without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import asdict
from typing import Optional, Tuple

from agents import SQLiteSession

from .context_models import BookingContext

# Path to the SQLite file used to persist state
STATE_DB = "state.db"

# Single lock protects concurrent access to the database
_lock = asyncio.Lock()


def _ensure_table_sync() -> None:
    conn = sqlite3.connect(STATE_DB)
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


async def _ensure_table() -> None:
    await asyncio.to_thread(_ensure_table_sync)


async def get_state(
    user_id: str,
) -> Optional[Tuple[BookingContext, SQLiteSession]]:
    """Retrieve stored context and create a session for ``user_id``."""
    await _ensure_table()

    async with _lock:
        def _fetch() -> Optional[str]:
            conn = sqlite3.connect(STATE_DB)
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

    ctx = BookingContext(**json.loads(ctx_json))
    session = SQLiteSession(user_id, "noor_sessions.db")
    return ctx, session


async def touch_state(
    user_id: str, ctx: BookingContext, session: SQLiteSession
) -> None:
    """Persist ``ctx`` for ``user_id``."""
    await _ensure_table()
    ctx_json = json.dumps(asdict(ctx))

    async with _lock:
        def _write() -> None:
            conn = sqlite3.connect(STATE_DB)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO state (user_id, ctx) VALUES (?, ?)",
                    (user_id, ctx_json),
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_write)


async def clear_state(user_id: str) -> None:
    """Remove stored state and clear the associated session."""
    await _ensure_table()

    async with _lock:
        def _delete() -> None:
            conn = sqlite3.connect(STATE_DB)
            try:
                conn.execute("DELETE FROM state WHERE user_id = ?", (user_id,))
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_delete)

    # Clear conversation session (ignore failures)
    try:
        session = SQLiteSession(user_id, "noor_sessions.db")
        try:
            await session.clear_session()
        finally:
            await session.close()
    except Exception:
        pass

