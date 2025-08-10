from dataclasses import dataclass
from typing import Optional


@dataclass
class BookingContext:
    # Booking flow slots
    section_pm_si: Optional[str] = None
    service_pm_si: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    employee_pm_si: Optional[str] = None
    gender: Optional[str] = None
    booking_confirmed: Optional[bool] = None

    # User meta
    user_name: Optional[str] = None
    user_phone: Optional[str] = None

    # Patient history
    patient_data: Optional[dict] = None
    previous_appointments: Optional[list] = None

    # Internal flags
    ltm_checked: Optional[bool] = None
