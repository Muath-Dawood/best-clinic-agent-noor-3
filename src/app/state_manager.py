from __future__ import annotations
from typing import Dict, Tuple, Optional
from agents import SQLiteSession
from .context_models import BookingContext

# simple in‑memory cache; replace with Redis later if you like
_STATE: Dict[str, Tuple[BookingContext, SQLiteSession]] = {}


def get_state(user_id: str) -> Optional[Tuple[BookingContext, SQLiteSession]]:
    return _STATE.get(user_id)


def touch_state(user_id: str, ctx: BookingContext, session: SQLiteSession) -> None:
    _STATE[user_id] = (ctx, session)


async def clear_state(user_id: str) -> None:
    pair = _STATE.pop(user_id, None)
    if pair:
        _, sess = pair
        await sess.close()
