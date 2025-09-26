"""
Validation utilities for data validation and sanitization.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from ..core.enums import Gender
from ..core.models.booking import BookingContext


class ValidationUtils:
    """Validation utilities for various data types."""

    @staticmethod
    def validate_palestinian_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Palestinian phone number format.

        Args:
            phone: Phone number to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not phone:
            return False, "رقم الهاتف مطلوب"

        # Extract digits only
        digits = re.sub(r"\D", "", phone)

        # Check various formats
        if digits.startswith("970") and len(digits) == 12:
            digits = "0" + digits[3:]
        elif digits.startswith("972") and len(digits) == 12:
            digits = "0" + digits[3:]
        elif digits.startswith("59") and len(digits) == 9:
            digits = "0" + digits
        elif not digits.startswith("05") or len(digits) != 10:
            return False, "رقم الهاتف غير صالح. الرجاء بصيغة 05XXXXXXXX"

        return True, None

    @staticmethod
    def validate_name(name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate name format.

        Args:
            name: Name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name or not isinstance(name, str):
            return False, "الاسم مطلوب"

        name = name.strip()
        if len(name) < 2:
            return False, "الاسم قصير جداً. الرجاء إدخال الاسم الثلاثي"

        if len(name) > 100:
            return False, "الاسم طويل جداً"

        # Check for valid characters (Arabic, English, spaces, hyphens)
        if not re.match(r"^[\u0600-\u06FFa-zA-Z\s\-]+$", name):
            return False, "الاسم يحتوي على أحرف غير صالحة"

        return True, None

    @staticmethod
    def validate_gender(gender: str) -> Tuple[bool, Optional[str], Optional[Gender]]:
        """
        Validate and normalize gender.

        Args:
            gender: Gender string to validate

        Returns:
            Tuple of (is_valid, error_message, normalized_gender)
        """
        if not gender:
            return True, None, Gender.MALE  # Default fallback

        try:
            normalized = Gender.from_string(gender)
            return True, None, normalized
        except Exception:
            return False, "الرجاء اختيار القسم: رجال أو نساء", None

    @staticmethod
    def validate_booking_context(ctx: BookingContext) -> List[str]:
        """
        Validate booking context for completeness.

        Args:
            ctx: Booking context to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Check required fields for booking
        if not ctx.selected_services_pm_si:
            errors.append("يجب اختيار الخدمات أولاً")

        if not ctx.appointment_date:
            errors.append("يجب تحديد التاريخ أولاً")

        if not ctx.appointment_time:
            errors.append("يجب تحديد الوقت أولاً")

        if not ctx.employee_pm_si:
            errors.append("يجب اختيار الطبيب أولاً")

        # Check subject information
        subject_info = ctx.get_subject_info()
        if not subject_info["name"]:
            errors.append("اسم الشخص مطلوب")

        if not subject_info["phone"]:
            errors.append("رقم هاتف الشخص مطلوب")

        # Validate phone number
        if subject_info["phone"]:
            is_valid, error_msg = ValidationUtils.validate_palestinian_phone(subject_info["phone"])
            if not is_valid:
                errors.append(error_msg)

        return errors

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Sanitize text by removing potentially harmful characters.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove control characters except newlines and tabs
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def validate_service_identifiers(identifiers: List[str]) -> Tuple[List[str], List[str]]:
        """
        Validate service identifiers.

        Args:
            identifiers: List of service identifiers to validate

        Returns:
            Tuple of (valid_identifiers, invalid_identifiers)
        """
        valid = []
        invalid = []

        for identifier in identifiers:
            if not identifier or not isinstance(identifier, str):
                invalid.append(str(identifier))
                continue

            identifier = identifier.strip()
            if len(identifier) < 1:
                invalid.append(identifier)
            else:
                valid.append(identifier)

        return valid, invalid
