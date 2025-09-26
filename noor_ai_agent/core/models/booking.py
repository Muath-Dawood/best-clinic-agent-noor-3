"""
Booking-related data models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field, ConfigDict

from ..enums import BookingStep, Gender, CustomerType


def _now_iso() -> str:
    """Get current datetime in ISO format for Palestine timezone."""
    return datetime.now(ZoneInfo("Asia/Hebron")).strftime("%Y-%m-%dT%H:%M:%S.%f%z")


class Service(BaseModel):
    """Service model for clinic services."""

    model_config = ConfigDict(extra="forbid")

    title: str
    title_en: Optional[str] = None
    duration: str
    duration_minutes: int
    pm_si: str
    price: str
    price_numeric: float
    category: str


class Employee(BaseModel):
    """Employee model for clinic staff."""

    model_config = ConfigDict(extra="forbid")

    pm_si: str
    name: str
    display: Optional[str] = None


class TimeSlot(BaseModel):
    """Time slot model for available appointment times."""

    model_config = ConfigDict(extra="forbid")

    time: str
    available: bool = True


@dataclass
class BookingContext:
    """Main booking context containing all booking-related state."""

    # User basics
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_lang: Optional[str] = None
    tz: str = "Asia/Hebron"
    current_datetime: Optional[str] = field(default_factory=_now_iso)

    # Gender and section (determines available services)
    gender: Optional[Gender] = None
    section_pm_si: Optional[str] = None

    # Patient record & history (if found)
    patient_data: Optional[Dict] = None
    customer_pm_si: Optional[str] = None
    previous_summaries: Optional[List[str]] = None
    user_has_attachments: bool = False

    # Booking selections - these build up as the user progresses
    selected_services_pm_si: Optional[List[str]] = None
    selected_services_data: Optional[List[Dict]] = None

    # Appointment details
    appointment_date: Optional[str] = None  # YYYY-MM-DD format
    appointment_time: Optional[str] = None  # HH:MM format
    available_times: Optional[List[Dict]] = None
    employee_pm_si: Optional[str] = None
    employee_name: Optional[str] = None
    offered_employees: Optional[List[Dict]] = None

    # Pricing
    total_price: Optional[float] = None
    price_currency: str = "NIS"
    checkout_summary: Optional[Dict] = None

    # Booking status
    booking_confirmed: bool = False
    booking_in_progress: bool = False

    # Customer info for new patients
    customer_type: Optional[CustomerType] = None
    customer_gender: Optional[Gender] = None

    # Booking subject (person being seen)
    subject_name: Optional[str] = None
    subject_phone: Optional[str] = None
    subject_gender: Optional[Gender] = None
    subject_relation: Optional[str] = None
    booking_for_self: bool = True

    # Flow guidance
    next_booking_step: Optional[BookingStep] = None
    pending_questions: Optional[List[str]] = None

    # Versioning
    version: int = 0

    def effective_gender(self) -> Gender:
        """Get the gender that should drive service catalog & availability."""
        return self.subject_gender or self.gender or Gender.MALE

    def is_new_customer(self) -> bool:
        """Check if this is a new customer (no existing patient data)."""
        return self.customer_type == CustomerType.NEW or self.patient_data is None

    def has_required_booking_info(self) -> bool:
        """Check if all required booking information is present."""
        return all([
            self.selected_services_pm_si,
            self.appointment_date,
            self.appointment_time,
            self.employee_pm_si,
        ])

    def get_subject_info(self) -> Dict[str, Any]:
        """Get information about the person being seen (subject of booking)."""
        if self.booking_for_self:
            return {
                "name": self.user_name,
                "phone": self.user_phone,
                "gender": self.effective_gender(),
            }
        else:
            return {
                "name": self.subject_name,
                "phone": self.subject_phone,
                "gender": self.subject_gender or self.effective_gender(),
            }


class BookingContextUpdate(BaseModel):
    """Model for updating booking context fields."""

    model_config = ConfigDict(extra="forbid")

    selected_services_pm_si: Optional[List[str]] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    employee_pm_si: Optional[str] = None
    employee_name: Optional[str] = None
    gender: Optional[Gender] = None

    # User fields for new customers
    user_name: Optional[str] = None
    user_phone: Optional[str] = None

    # Subject fields (for booking for someone else)
    subject_name: Optional[str] = None
    subject_phone: Optional[str] = None
    subject_gender: Optional[Gender] = None
    subject_relation: Optional[str] = None
    booking_for_self: Optional[bool] = None

    # Note: next_booking_step is computed by the system and ignored if provided
    next_booking_step: Optional[BookingStep] = None
