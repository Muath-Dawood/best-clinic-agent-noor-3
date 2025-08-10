from __future__ import annotations
import os
import asyncio
from typing import Dict, Optional, Tuple
from agents import SQLiteSession

from src.app.session_memory import build_summary, save_summary_to_vector_store
from src.app.state_manager import get_state, clear_state
from src.app.context_models import BookingContext
from src.app.logging import get_logger

# 30 minutes
IDLE_SECONDS = int(os.getenv("IDLE_SECONDS", "1800"))

# last activity timestamp per user_id
_last_seen: Dict[str, float] = {}
# to avoid launching multiple watchers per user
_running_watchers: Dict[str, asyncio.Task] = {}
_lock = asyncio.Lock()

logger = get_logger("noor.idle")


def _vector_store_id() -> Optional[str]:
    v = os.getenv("VECTOR_STORE_ID_SUMMARIES", "").strip()
    return v or None


async def update_last_seen(user_id: str) -> None:
    async with _lock:
        _last_seen[user_id] = asyncio.get_event_loop().time()
    logger.info(f"idle: last_seen updated for {user_id}")


async def _check_and_finalize(user_id: str) -> None:
    """
    Waits IDLE_SECONDS; if user still idle, summarize, save to vector store, and clear state.
    """
    try:
        # capture the timestamp when we started watching
        async with _lock:
            started_at = _last_seen.get(user_id, 0.0)

        await asyncio.sleep(IDLE_SECONDS)

        async with _lock:
            # if changed, user sent something; abort
            if _last_seen.get(user_id, 0.0) != started_at:
                logger.info(f"idle: aborted (activity) for {user_id}")
                return

        # pull current state
        state: Optional[Tuple[BookingContext, SQLiteSession]] = get_state(user_id)
        if not state:
            logger.info(f"idle: no state for {user_id}")
            return

        ctx, session = state
        logger.info(f"idle: building summary for {user_id}")
        # build summary text
        try:
            summary = await build_summary(
                user_id=user_id,
                user_name=ctx.user_name,
                user_phone=ctx.user_phone,
                session=session,
            )
        except Exception as e:
            logger.error(f"idle: build_summary failed for {user_id}: {e}")
            summary = None

        # save to vector store if configured
        try:
            vsid = _vector_store_id()
            if vsid and summary:
                logger.info(f"idle: uploading summary to {vsid} for {user_id}")
                await save_summary_to_vector_store(
                    vector_store_id=vsid, summary=summary
                )
            else:
                logger.warning(
                    f"idle: skip upload (vsid={vsid}, has_summary={bool(summary)}) for {user_id}"
                )
        except Exception as e:
            # non‑fatal
            logger.error(f"idle: upload failed for {user_id}: {e}")
            pass

        # clear session/context
        try:
            await clear_state(user_id)
            logger.info(f"idle: state cleared for {user_id}")
        except Exception as e:
            logger.error(f"idle: clear_state error for {user_id}: {e}")
            pass
    finally:
        # allow a new watcher to be scheduled later
        async with _lock:
            _running_watchers.pop(user_id, None)


async def schedule_idle_watch(user_id: str) -> None:
    """
    Ensure exactly one background watcher is running for this user.
    """
    async with _lock:
        if user_id in _running_watchers:
            return
        task = asyncio.create_task(_check_and_finalize(user_id))
        _running_watchers[user_id] = task
    logger.info(f"idle: watcher scheduled for {user_id} ({IDLE_SECONDS}s)")
