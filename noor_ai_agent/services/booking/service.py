"""
Booking service for handling appointment bookings.
"""

import hashlib
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

from ...core.models.booking import BookingContext, BookingContextUpdate, Service, Employee, TimeSlot
from ...core.enums import Gender, BookingStep
from ...core.exceptions import BookingFlowError, SlotUnavailableError
from ...utils.date import DateParser, TimeParser
from ...utils.validation import ValidationUtils
from .data import ServiceDataProvider
from ..external import ExternalAPIService


class BookingService:
    """Service for handling appointment bookings."""

    def __init__(self, external_api: ExternalAPIService, service_data: ServiceDataProvider):
        self.external_api = external_api
        self.service_data = service_data
        self.date_parser = DateParser()
        self.time_parser = TimeParser()

    async def get_available_services(self, gender: Gender) -> List[Dict]:
        """Get available services for a specific gender."""
        return self.service_data.get_services_by_gender(gender)

    async def get_available_dates(
        self,
        services_pm_si: List[str],
        gender: Gender
    ) -> List[str]:
        """Get available dates for selected services."""
        cus_sec_pm_si = self.service_data.get_cus_sec_pm_si_by_gender(gender)
        data = {"services_pm_si[]": services_pm_si}

        result = await self.external_api.get_available_dates(data, cus_sec_pm_si)
        return result.get("data", [])

    async def get_available_times(
        self,
        date: str,
        services_pm_si: List[str],
        gender: Gender
    ) -> List[Dict]:
        """Get available times for a specific date and services."""
        cus_sec_pm_si = self.service_data.get_cus_sec_pm_si_by_gender(gender)
        data = {"date": date, "services_pm_si[]": services_pm_si}

        result = await self.external_api.get_available_times(data, cus_sec_pm_si)

        slots: List[Dict] = []
        for item in result.get("data", []):
            if isinstance(item, str):
                time_str = item.strip()
                if time_str:
                    slots.append({"time": time_str})
            elif isinstance(item, dict):
                time_str = item.get("time")
                if isinstance(time_str, str):
                    time_str = time_str.strip()
                    if time_str:
                        slots.append({"time": time_str})

        return slots

    async def get_available_employees(
        self,
        date: str,
        time: str,
        services_pm_si: List[str],
        gender: Gender
    ) -> Tuple[List[Dict], Dict]:
        """Get available employees and pricing summary."""
        cus_sec_pm_si = self.service_data.get_cus_sec_pm_si_by_gender(gender)
        data = {"date": date, "time": time, "services_pm_si[]": services_pm_si}

        result = await self.external_api.get_available_employees(data, cus_sec_pm_si)

        employees = result.get("data", [])
        checkout_summary = result.get("checkout_summary", {})

        return employees, checkout_summary

    async def create_booking(
        self,
        date: str,
        time: str,
        employee_pm_si: str,
        services_pm_si: List[str],
        customer_pm_si: Optional[str],
        gender: Gender,
        idempotency_key: Optional[str] = None,
        **extra,
    ) -> Dict:
        """Create the final booking."""
        cus_sec_pm_si = self.service_data.get_cus_sec_pm_si_by_gender(gender)

        data = {
            "date": date,
            "time": time,
            "employee_pm_si": employee_pm_si,
            "services_pm_si[]": services_pm_si,
        }

        if customer_pm_si:
            data["customer_pm_si"] = customer_pm_si

        note = extra.pop("note", None)
        if note is not None:
            data["note"] = json.dumps(note, ensure_ascii=False)

        if extra:
            data.update(extra)

        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None

        result = await self.external_api.create_booking(
            "BOKINNEW", data, cus_sec_pm_si, extra_headers=headers
        )
        return result

    def parse_natural_date(self, text: str, language: str = "ar") -> Optional[str]:
        """Parse natural language dates."""
        return self.date_parser.parse_natural_date(text, language)

    def parse_natural_time(self, text: str) -> Optional[str]:
        """Parse natural language times."""
        return self.time_parser.parse_natural_time(text)

    def calculate_total_price(self, services_pm_si: List[str]) -> float:
        """Calculate total price for selected services."""
        total = 0.0
        for pm_si in services_pm_si:
            service = self.service_data.find_service_by_pm_si(pm_si)
            if service:
                total += service["price_numeric"]
        return total

    def format_booking_summary(
        self,
        services: List[Dict],
        date: str,
        time: str,
        employee_name: str,
        total_price: float,
    ) -> str:
        """Format a human-readable booking summary."""
        service_titles = [s["title"] for s in services]
        services_text = "\n".join([f"• {title}" for title in service_titles])

        summary = f"""
📋 ملخص الحجز:

الخدمات:
{services_text}

📅 التاريخ: {date}
🕐 الوقت: {time}
👨‍⚕️ الطبيب: {employee_name}
💰 السعر الإجمالي: {total_price:.2f} ₪

هل تريد تأكيد هذا الحجز؟
        """.strip()

        return summary

    def build_booking_idempotency_key(self, ctx: BookingContext) -> str:
        """Build idempotency key for booking to prevent duplicates."""
        raw = {
            "chat": getattr(ctx, "chat_id", None),
            "date": getattr(ctx, "appointment_date", None),
            "time": getattr(ctx, "appointment_time", None),
            "emp": getattr(ctx, "employee_pm_si", None),
            "svcs": sorted(getattr(ctx, "selected_services_pm_si", []) or []),
            "subject": {
                "self": bool(getattr(ctx, "booking_for_self", True)),
                "name": (
                    getattr(ctx, "subject_name", None)
                    if not getattr(ctx, "booking_for_self", True)
                    else getattr(ctx, "user_name", None)
                ),
                "phone": (
                    getattr(ctx, "subject_phone", None)
                    if not getattr(ctx, "booking_for_self", True)
                    else getattr(ctx, "user_phone", None)
                ),
                "gender": str(ctx.effective_gender()),
            },
        }
        return hashlib.sha256(
            json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def validate_booking_context(self, ctx: BookingContext) -> List[str]:
        """Validate booking context for completeness."""
        return ValidationUtils.validate_booking_context(ctx)

    async def recover_slot_conflict(
        self,
        ctx: BookingContext,
        human_prefix: Optional[str] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        When the selected slot is unavailable, refresh times and reset slot-related fields.

        Returns:
            Tuple of (patch_data, human_message)
        """
        try:
            fresh_times = await self.get_available_times(
                ctx.appointment_date,
                ctx.selected_services_pm_si,
                ctx.effective_gender()
            )
        except Exception:
            fresh_times = None

        # Reset slot + doctor
        patch = {
            "appointment_time": None,
            "offered_employees": None,
            "employee_pm_si": None,
            "employee_name": None,
        }

        if fresh_times is not None:
            patch.update({"available_times": fresh_times})

        # Friendly message
        human = human_prefix or "عذراً، لم يعد الوقت المختار متاحاً."
        if fresh_times:
            times = [t.get("time") for t in fresh_times if isinstance(t, dict)]
            if times:
                human += " الأوقات المتاحة الأخرى: " + ", ".join(times[:12])
            else:
                human += " لا توجد أوقات متاحة حالياً في هذا اليوم."
        else:
            human += " تعذّر تحديث الأوقات حالياً."

        return patch, human
