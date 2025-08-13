import asyncio
import pytest

from src.app import session_idle
from src.app.context_models import BookingContext


@pytest.mark.asyncio
async def test_update_last_seen_expires_stale_entries(monkeypatch):
    session_idle._last_seen.clear()
    monkeypatch.setattr(session_idle, "LAST_SEEN_EXPIRY_SECONDS", 10)
    now = asyncio.get_event_loop().time()
    session_idle._last_seen["old"] = now - 20
    session_idle._last_seen["fresh"] = now - 5

    await session_idle.update_last_seen("new")

    assert "old" not in session_idle._last_seen
    assert "fresh" in session_idle._last_seen
    assert "new" in session_idle._last_seen


@pytest.mark.asyncio
async def test_clear_state_removes_last_seen(monkeypatch):
    session_idle._last_seen.clear()
    session_idle._last_seen["user"] = 0.0

    async def dummy_get_state(uid):
        return BookingContext(user_name="a"), object()

    async def dummy_build_summary(**kwargs):  # pragma: no cover - placeholder
        return "summary"

    async def dummy_save_summary_to_vector_store(**kwargs):  # pragma: no cover
        return None

    cleared = []

    async def dummy_clear_state(uid):
        cleared.append(uid)

    async def no_sleep(_: float):
        return None

    monkeypatch.setattr(session_idle, "get_state", dummy_get_state)
    monkeypatch.setattr(session_idle, "build_summary", dummy_build_summary)
    monkeypatch.setattr(
        session_idle, "save_summary_to_vector_store", dummy_save_summary_to_vector_store
    )
    monkeypatch.setattr(session_idle, "clear_state", dummy_clear_state)
    monkeypatch.setattr(session_idle.asyncio, "sleep", no_sleep)

    await session_idle._check_and_finalize("user")

    assert cleared == ["user"]
    assert "user" not in session_idle._last_seen
