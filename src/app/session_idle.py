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
    try:
        # simple sleep; we reset by cancelling this task on every new message
        await asyncio.sleep(IDLE_SECONDS)

        # pull current state
        state: Optional[Tuple[BookingContext, SQLiteSession]] = await get_state(user_id)
        if not state:
            logger.info(f"idle: no state for {user_id}")
            return

        ctx, session = state

        logger.info(f"idle: building summary for {user_id}")
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
            logger.error(f"idle: upload failed for {user_id}: {e}")

        try:
            await clear_state(user_id)
            logger.info(f"idle: state cleared for {user_id}")
        except Exception as e:
            logger.error(f"idle: clear_state error for {user_id}: {e}")

    except asyncio.CancelledError:
        # expected on every new message (we reset the timer)
        logger.info(f"idle: watcher cancelled/reset for {user_id}")
        return
    finally:
        # only remove if *this* task is the one stored
        async with _lock:
            if _running_watchers.get(user_id) is asyncio.current_task():
                _running_watchers.pop(user_id, None)


async def schedule_idle_watch(user_id: str) -> None:
    """
    Reset the idle timer: cancel any existing watcher and start a fresh one.
    This guarantees the summary runs IDLE_SECONDS after the *last* message.
    """
    async with _lock:
        # cancel previous watcher if still running
        existing = _running_watchers.get(user_id)
        if existing and not existing.done():
            existing.cancel()
        # start a fresh watcher
        task = asyncio.create_task(_check_and_finalize(user_id))
        _running_watchers[user_id] = task
    logger.info(f"idle: timer reset for {user_id} ({IDLE_SECONDS}s)")
