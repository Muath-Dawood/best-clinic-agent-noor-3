from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo


def _now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Hebron")).strftime("%Y-%m-%dT%H:%M:%S.%f%z")


class BookingStep(str, Enum):
    """Enumeration of the booking flow steps."""

    SELECT_SERVICE = "select_service"
    SELECT_DATE = "select_date"
    SELECT_TIME = "select_time"
    SELECT_EMPLOYEE = "select_employee"


# Map of allowed transitions in the booking flow
BOOKING_STEP_TRANSITIONS: Dict[
    Optional["BookingStep"], List[Optional["BookingStep"]]
] = {
    None: [BookingStep.SELECT_SERVICE],
    BookingStep.SELECT_SERVICE: [BookingStep.SELECT_DATE],
    BookingStep.SELECT_DATE: [BookingStep.SELECT_TIME],
    BookingStep.SELECT_TIME: [BookingStep.SELECT_EMPLOYEE],
    BookingStep.SELECT_EMPLOYEE: [None],
}


@dataclass
class BookingContext:
    # user basics
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_lang: Optional[str] = None
    tz: str = "Asia/Hebron"
    current_datetime: Optional[str] = field(default_factory=_now_iso)

    # gender and section (determines available services)
    gender: Optional[str] = None  # 'male'/'female' or 'ذكر'/'أنثى'
    section_pm_si: Optional[str] = None  # men's or women's section

    # patient record & history (if found)
    patient_data: Optional[Dict] = None
    previous_summaries: Optional[List[str]] = None
    user_has_attachments: bool = False

    # booking selections - these build up as the user progresses
    selected_services_pm_si: Optional[List[str]] = None  # list of service pm_si tokens
    selected_services_data: Optional[List[Dict]] = (
        None  # full service objects for display
    )

    # appointment details
    appointment_date: Optional[str] = None  # YYYY-MM-DD format
    appointment_time: Optional[str] = None  # HH:MM format
    available_times: Optional[List[Dict]] = None  # available time slots
    employee_pm_si: Optional[str] = None  # selected employee token
    employee_name: Optional[str] = None  # human-readable employee name
    offered_employees: Optional[List[Dict]] = None  # employees offered to user

    # pricing
    total_price: Optional[float] = None
    price_currency: str = "NIS"
    checkout_summary: Optional[Dict] = None  # summary of booking details

    # booking status
    booking_confirmed: bool = False
    booking_in_progress: bool = False  # true when user is actively booking

    # customer info for new patients
    customer_type: Optional[str] = None  # 'new' or 'exists'
    customer_gender: Optional[str] = None  # for new patients

    # flow guidance
    next_booking_step: Optional[BookingStep] = None  # what Noor should ask next
    pending_questions: Optional[List[str]] = None  # questions Noor needs to ask

    # versioning
    version: int = 0  # incremented on each context update
