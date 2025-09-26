"""
Language-related enums.
"""

from enum import Enum


class Language(str, Enum):
    """Supported languages."""

    ARABIC = "ar"
    ENGLISH = "en"
    UNKNOWN = "unknown"

    @classmethod
    def detect_from_text(cls, text: str) -> "Language":
        """Detect language from text content."""
        if not text:
            return cls.UNKNOWN

        # Check for Arabic characters
        if any("\u0600" <= char <= "\u06ff" for char in text):
            return cls.ARABIC

        # Check for English characters
        if any("a" <= char.lower() <= "z" for char in text):
            return cls.ENGLISH

        return cls.UNKNOWN
