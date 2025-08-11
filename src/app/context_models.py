from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class BookingContext:
    # user basics
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_lang: Optional[str] = None
    tz: str = "Asia/Jerusalem"

    # patient record & history (if found)
    patient_data: Optional[Dict] = None
    previous_summaries: Optional[List[str]] = None
    user_has_attachments: bool = False

    # booking selections
    section_pm_si: Optional[str] = None
    service_pm_si: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    employee_pm_si: Optional[str] = None
    gender: Optional[str] = None
    booking_confirmed: bool = False
