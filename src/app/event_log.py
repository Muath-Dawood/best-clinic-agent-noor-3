import json
import os
from pathlib import Path
import contextvars
from typing import Any, Dict

# Path to the log file; can be overridden via EVENT_LOG_PATH env var or set_log_path.
_LOG_PATH = Path(os.environ.get("EVENT_LOG_PATH", "noor_event_log.jsonl"))

_current_turn_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_turn_id", default=None
)

def set_log_path(path: str | Path) -> None:
    """Override the log file path (useful for tests)."""
    global _LOG_PATH
    _LOG_PATH = Path(path)


def get_log_path() -> Path:
    """Return the current log file path."""
    return _LOG_PATH


def set_turn_id(turn_id: int) -> None:
    """Set the active turn identifier for subsequent events."""
    _current_turn_id.set(turn_id)


def log_event(event: str, data: Dict[str, Any], *, turn_id: int | None = None) -> None:
    """Append an event to the log as a JSON line.

    Parameters
    ----------
    event:
        Type of the event (e.g., "user_text", "tool_call").
    data:
        Arbitrary JSON-serializable payload.
    turn_id:
        Optional explicit turn identifier. If omitted, the previously set
        turn id (via :func:`set_turn_id`) is used.
    """
    tid = turn_id if turn_id is not None else _current_turn_id.get()
    record = {"turn_id": tid, "event": event, **data}
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")
