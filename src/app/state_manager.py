from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from agents import SQLiteSession
from .context_models import BookingContext
from .session_memory import build_summary, save_summary_to_vector_store

STATE_IDLE_MINUTES = 30
STATE_CACHE_LIMIT = 500
_CACHE: Dict[str, Tuple[BookingContext, SQLiteSession, datetime]] = {}


def get_state(sender_id: str) -> Optional[Tuple[BookingContext, SQLiteSession]]:
    triple = _CACHE.get(sender_id)
    return (triple[0], triple[1]) if triple else None


def touch_state(sender_id: str, ctx: BookingContext, session: SQLiteSession) -> None:
    _CACHE[sender_id] = (ctx, session, datetime.now())
    if len(_CACHE) > STATE_CACHE_LIMIT:
        oldest = min(_CACHE.items(), key=lambda kv: kv[1][2])[0]
        _CACHE.pop(oldest, None)


async def clear_state(sender_id: str) -> None:
    triple = _CACHE.pop(sender_id, None)
    if triple:
        _, session, _ = triple
        try:
            await session.clear_session()
        except Exception:
            pass


async def finalize_idle_sessions(user_summaries_vs_id: str) -> None:
    now = datetime.now()
    cutoff = timedelta(minutes=STATE_IDLE_MINUTES)
    idle_users = [uid for uid, (_, _, last) in _CACHE.items() if now - last > cutoff]
    for uid in idle_users:
        try:
            ctx, session, _ = _CACHE.get(uid, (None, None, None))
            if not ctx or not session:
                _CACHE.pop(uid, None)
                continue
            summary = await build_summary(
                user_id=uid,
                user_name=ctx.user_name,
                user_phone=ctx.user_phone,
                session=session,
            )
            await save_summary_to_vector_store(
                vector_store_id=user_summaries_vs_id,
                summary=summary,
            )
        except Exception:
            pass
        finally:
            await clear_state(uid)
