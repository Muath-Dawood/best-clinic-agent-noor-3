import pytest

from src.app import state_manager
from src.app.context_models import BookingContext


@pytest.mark.asyncio
async def test_touch_get_clear_state(tmp_path, monkeypatch):
    db_file = tmp_path / "state.db"
    monkeypatch.setattr(state_manager, "STATE_DB", str(db_file))

    cleared_sessions = []

    class DummySession:
        def __init__(self, session_id: str, db_path: str):
            self.session_id = session_id
            self.db_path = db_path

        async def clear_session(self) -> None:
            cleared_sessions.append(self.session_id)

        async def close(self) -> None:  # pragma: no cover - no cleanup needed
            pass

    monkeypatch.setattr(state_manager, "SQLiteSession", DummySession)

    user_id = "user123"
    ctx = BookingContext(user_name="Ali")
    session = DummySession(user_id, "")

    await state_manager.touch_state(user_id, ctx, session)

    loaded = await state_manager.get_state(user_id)
    assert loaded is not None
    loaded_ctx, loaded_session = loaded
    assert loaded_ctx.user_name == "Ali"
    assert isinstance(loaded_session, DummySession)
    assert loaded_session.session_id == user_id

    await state_manager.clear_state(user_id)
    assert user_id in cleared_sessions
    assert await state_manager.get_state(user_id) is None
