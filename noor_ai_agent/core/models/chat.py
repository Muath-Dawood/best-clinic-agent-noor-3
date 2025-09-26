"""
Chat-related data models.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from ..enums import Language, BookingStatus


class ChatMessage(BaseModel):
    """Individual chat message model."""

    model_config = ConfigDict(extra="forbid")

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None


class ChatSummary(BaseModel):
    """Chat conversation summary model."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    start_time_iso: str
    end_time_iso: str
    language: Language = Language.UNKNOWN
    intents: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    booking_status: BookingStatus = BookingStatus.NONE
    next_best_action: str = ""
    free_text: str = ""

    @classmethod
    def create_empty(cls, user_id: str, user_name: Optional[str] = None,
                    user_phone: Optional[str] = None) -> "ChatSummary":
        """Create an empty summary for a new conversation."""
        now = datetime.now().isoformat()
        return cls(
            user_id=user_id,
            user_name=user_name,
            user_phone=user_phone,
            start_time_iso=now,
            end_time_iso=now,
            language=Language.UNKNOWN,
        )
