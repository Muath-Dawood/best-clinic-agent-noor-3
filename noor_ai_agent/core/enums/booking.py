"""
Booking-related enums.
"""

from enum import Enum


class BookingStep(str, Enum):
    """Enumeration of the booking flow steps."""

    SELECT_SERVICE = "select_service"
    SELECT_DATE = "select_date"
    SELECT_TIME = "select_time"
    SELECT_EMPLOYEE = "select_employee"


class Gender(str, Enum):
    """Gender enumeration for service selection."""

    MALE = "male"
    FEMALE = "female"

    @classmethod
    def from_string(cls, value: str) -> "Gender":
        """Convert string to Gender enum with Arabic/English support."""
        if not value:
            return cls.MALE

        value = value.strip().lower()

        # Arabic support
        if value in ["ذكر", "رجال", "m"]:
            return cls.MALE
        if value in ["أنثى", "نساء", "f"]:
            return cls.FEMALE

        # English support
        if value in ["male", "men"]:
            return cls.MALE
        if value in ["female", "women"]:
            return cls.FEMALE

        # Default fallback
        return cls.MALE


class CustomerType(str, Enum):
    """Customer type enumeration."""

    NEW = "new"
    EXISTING = "existing"


class BookingStatus(str, Enum):
    """Booking status enumeration."""

    NONE = "none"
    SUGGESTED = "suggested"
    IN_PROGRESS = "in_progress"
    CONFIRMED = "confirmed"
    FAILED = "failed"
