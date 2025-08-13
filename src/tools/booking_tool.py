"""
Booking tool for Best Clinic 24 - handles all API complexity and state management.
This tool manages the complete booking flow while keeping Noor's responses natural.
"""

from typing import List, Dict, Optional, Tuple
import logging

from datetime import datetime, timedelta

import httpx
from dateparser import parse as parse_date

from src.app.session_memory import tz
from src.data.services import (
    get_services_by_gender,
    get_cus_sec_pm_si_by_gender,
    find_service_by_pm_si,
)


logger = logging.getLogger(__name__)


class BookingFlowError(Exception):
    """Custom exception for booking flow errors."""

    pass


class BookingTool:
    """Handles all booking API interactions and state management."""

    def __init__(self):
        self.base_url = "https://www.bestclinic24.net"
        self.timeout = 10.0

    async def _make_api_call(
        self,
        endpoint: str,
        data: Dict,
        cus_sec_pm_si: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """Make API call to booking endpoints."""
        url = f"{self.base_url}/{endpoint}"

        # Prepare multipart form data
        form_data = {}
        for key, value in data.items():
            if isinstance(value, list):
                # Handle array fields like services_pm_si[]
                # For arrays, we need to send multiple values with the same key
                form_data[key] = value  # httpx will handle this correctly
            else:
                form_data[key] = value

        # Always include the required cus_sec_pm_si
        form_data["cus_sec_pm_si"] = cus_sec_pm_si

        # Include all the headers that the server expects
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9,pt;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/BOKNWVIWW",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        if extra_headers:
            headers.update(extra_headers)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, data=form_data, headers=headers)

                response.raise_for_status()

                # API returns JSON but with text/html content-type
                result = response.json()

                if not result.get("result"):
                    sanitized_result = {
                        k: "[REDACTED]" if k in {"cus_sec_pm_si", "token"} else v
                        for k, v in result.items()
                    }
                    logger.error("Full API response: %s", sanitized_result)
                    raise BookingFlowError(
                        f"API error: {result.get('message', 'Unknown error')} | Full response: {sanitized_result}"
                    )

                return result

        except httpx.TimeoutException:
            raise BookingFlowError("API request timed out")
        except httpx.HTTPStatusError as e:
            raise BookingFlowError(f"HTTP error {e.response.status_code}")
        except Exception as e:
            raise BookingFlowError(f"API call failed: {str(e)}")

    def parse_natural_date(self, text: str, language: str = "ar") -> Optional[str]:
        """Parse natural language dates like 'بعد ٣ أيام' or 'next Sunday'.

        If the parsed result falls before today's date, the next logical
        occurrence is returned for day-of-week phrases. Otherwise, the method
        returns ``None`` when no future date makes sense (e.g., "yesterday").
        """

        try:
            settings = {"PREFER_DATES_FROM": "future"}
            if language == "ar":
                settings["PREFER_DAY_OF_MONTH"] = "first"

            parsed_date = parse_date(text, settings=settings, languages=[language])
            if not parsed_date:
                lowered = text.strip().lower()
                weekday_map = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                    "الاثنين": 0,
                    "الإثنين": 0,
                    "الثلاثاء": 1,
                    "الأربعاء": 2,
                    "الاربعاء": 2,
                    "الخميس": 3,
                    "الجمعة": 4,
                    "السبت": 5,
                    "الأحد": 6,
                    "الاحد": 6,
                }
                for name, idx in weekday_map.items():
                    if name in lowered:
                        today = datetime.now(tz).date()
                        days_ahead = (idx - today.weekday() + 7) % 7
                        if "القادم" in lowered or days_ahead == 0:
                            days_ahead = (days_ahead or 7)
                        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                return None

            # Normalize parsed date to configured timezone
            if parsed_date.tzinfo is None:
                parsed_date = tz.localize(parsed_date)
            else:
                parsed_date = parsed_date.astimezone(tz)

            today = datetime.now(tz).date()
            result_date = parsed_date.date()

            if result_date < today:
                lowered = text.strip().lower()
                weekday_keywords = {
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                    "الاثنين",
                    "الإثنين",
                    "الثلاثاء",
                    "الأربعاء",
                    "الاربعاء",
                    "الخميس",
                    "الجمعة",
                    "السبت",
                    "الأحد",
                    "الاحد",
                }
                if any(day in lowered for day in weekday_keywords):
                    while result_date <= today:
                        result_date += timedelta(days=7)
                    return result_date.strftime("%Y-%m-%d")
                return None

            return result_date.strftime("%Y-%m-%d")

        except Exception:
            return None

    def parse_natural_time(self, text: str) -> Optional[str]:
        """Parse natural language times like 'صباحاً' or 'morning'."""
        time_mappings = {
            # Arabic
            "صباحاً": "09:00",
            "الصباح": "09:00",
            "ظهراً": "12:00",
            "الظهر": "12:00",
            "عصراً": "15:00",
            "العصر": "15:00",
            "مساءً": "18:00",
            "المساء": "18:00",
            "ليلاً": "20:00",
            "الليل": "20:00",
            # English
            "morning": "09:00",
            "noon": "12:00",
            "afternoon": "15:00",
            "evening": "18:00",
            "night": "20:00",
        }

        text_lower = text.lower().strip()
        if text_lower in time_mappings:
            return time_mappings[text_lower]

        try:
            parsed = parse_date(text, languages=["ar", "en"])
            if parsed:
                if parsed.tzinfo is None:
                    parsed = tz.localize(parsed)
                else:
                    parsed = parsed.astimezone(tz)
                return parsed.strftime("%H:%M")
        except Exception:
            pass
        return None

    async def get_available_dates(
        self, services_pm_si: List[str], gender: str
    ) -> List[str]:
        """Get available dates for selected services."""
        cus_sec_pm_si = get_cus_sec_pm_si_by_gender(gender)

        data = {"services_pm_si[]": services_pm_si}

        result = await self._make_api_call("BOKGTAVBLDTS", data, cus_sec_pm_si)
        return result.get("data", [])

    async def get_available_times(
        self, date: str, services_pm_si: List[str], gender: str
    ) -> List[str]:
        """Get available times for a specific date and services."""
        cus_sec_pm_si = get_cus_sec_pm_si_by_gender(gender)

        data = {"date": date, "services_pm_si[]": services_pm_si}

        result = await self._make_api_call("BOKGTAVBLTIMS", data, cus_sec_pm_si)
        return result.get("data", [])

    async def get_available_employees(
        self, date: str, time: str, services_pm_si: List[str], gender: str
    ) -> Tuple[List[Dict], Dict]:
        """Get available employees and pricing summary."""
        cus_sec_pm_si = get_cus_sec_pm_si_by_gender(gender)

        data = {"date": date, "time": time, "services_pm_si[]": services_pm_si}

        result = await self._make_api_call("BOKGTAVBLEMPLS", data, cus_sec_pm_si)

        employees = result.get("data", [])
        checkout_summary = result.get("checkout_summary", {})

        return employees, checkout_summary

    async def create_booking(
        self,
        date: str,
        time: str,
        employee_pm_si: str,
        services_pm_si: List[str],
        customer_info: Dict,
        gender: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        """Create the final booking."""
        cus_sec_pm_si = get_cus_sec_pm_si_by_gender(gender)

        data = {
            "date": date,
            "time": time,
            "employee_pm_si": employee_pm_si,
            "services_pm_si[]": services_pm_si,
            **customer_info,
        }

        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        result = await self._make_api_call(
            "BOKINNEW", data, cus_sec_pm_si, extra_headers=headers
        )
        return result

    def get_services_for_gender(self, gender: str) -> List[Dict]:
        """Get available services for a specific gender."""
        return get_services_by_gender(gender)

    def calculate_total_price(self, services_pm_si: List[str]) -> float:
        """Calculate total price for selected services."""
        total = 0.0
        for pm_si in services_pm_si:
            service = find_service_by_pm_si(pm_si)
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
💰 السعر الإجمالي: {total_price:.2f} د.ك

هل تريد تأكيد هذا الحجز؟
        """.strip()

        return summary


# Create a singleton instance
booking_tool = BookingTool()
