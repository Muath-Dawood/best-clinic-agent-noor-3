"""
Phone number parsing and validation utilities.
"""

import re
from typing import Optional


class PhoneNumberParser:
    """Phone number parsing utilities for Palestinian numbers."""

    # Palestinian phone number patterns
    PALESTINIAN_PATTERNS = [
        r"^05\d{8}$",  # Local format: 05XXXXXXXX
        r"^\+9705\d{8}$",  # International format: +9705XXXXXXXX
        r"^9725\d{8}$",  # Alternative international: 9725XXXXXXXX
    ]

    @classmethod
    def parse_whatsapp_to_local_palestinian_number(cls, chat_id: str) -> Optional[str]:
        """
        Parse WhatsApp chat ID to local Palestinian phone number format.

        Args:
            chat_id: WhatsApp chat ID (e.g., "972599123456@c.us")

        Returns:
            Local Palestinian phone number in format 05XXXXXXXX or None if invalid
        """
        if not chat_id or not isinstance(chat_id, str):
            return None

        # Extract phone number from chat ID
        # Format: "972599123456@c.us" or "972599123456"
        phone_match = re.match(r"(\d+)@", chat_id)
        if phone_match:
            phone = phone_match.group(1)
        else:
            phone = chat_id

        return cls.normalize_to_local_format(phone)

    @classmethod
    def normalize_to_local_format(cls, phone: str) -> Optional[str]:
        """
        Normalize phone number to local Palestinian format (05XXXXXXXX).

        Args:
            phone: Phone number in various formats

        Returns:
            Normalized phone number or None if invalid
        """
        if not phone:
            return None

        # Remove all non-digit characters
        digits = re.sub(r"\D", "", phone)

        # Handle different formats
        if digits.startswith("970") and len(digits) == 12:
            # +9705XXXXXXXX -> 05XXXXXXXX
            return "0" + digits[3:]
        elif digits.startswith("972") and len(digits) == 12:
            # 9725XXXXXXXX -> 05XXXXXXXX
            return "0" + digits[3:]
        elif digits.startswith("59") and len(digits) == 9:
            # 59XXXXXXXX -> 05XXXXXXXX
            return "0" + digits
        elif digits.startswith("05") and len(digits) == 10:
            # Already in correct format
            return digits

        return None

    @classmethod
    def is_valid_palestinian_number(cls, phone: str) -> bool:
        """
        Check if phone number is a valid Palestinian number.

        Args:
            phone: Phone number to validate

        Returns:
            True if valid Palestinian number, False otherwise
        """
        normalized = cls.normalize_to_local_format(phone)
        if not normalized:
            return False

        return any(re.match(pattern, normalized) for pattern in cls.PALESTINIAN_PATTERNS)

    @classmethod
    def format_for_display(cls, phone: str) -> str:
        """
        Format phone number for display purposes.

        Args:
            phone: Phone number to format

        Returns:
            Formatted phone number for display
        """
        normalized = cls.normalize_to_local_format(phone)
        if not normalized:
            return phone

        # Format as 05X XXX XXXX
        if len(normalized) == 10 and normalized.startswith("05"):
            return f"{normalized[:3]} {normalized[3:6]} {normalized[6:]}"

        return normalized
