"""
User-related data models.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict

from ..enums import Gender, Language


class UserProfile(BaseModel):
    """User profile information."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    phone: Optional[str] = None
    language: Language = Language.UNKNOWN
    gender: Optional[Gender] = None
    timezone: str = "Asia/Hebron"
    has_attachments: bool = False


class User(BaseModel):
    """User model for WhatsApp users."""

    model_config = ConfigDict(extra="forbid")

    chat_id: str
    profile: UserProfile
    is_new: bool = True
    last_seen: Optional[str] = None

    @classmethod
    def from_whatsapp_data(cls, chat_id: str, sender_data: Dict[str, Any]) -> "User":
        """Create User from WhatsApp sender data."""
        profile = UserProfile(
            name=sender_data.get("senderName"),
            phone=None,  # Will be parsed from chat_id
            language=Language.UNKNOWN,
        )

        return cls(
            chat_id=chat_id,
            profile=profile,
            is_new=True,
        )
