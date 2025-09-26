"""
Date and time parsing utilities.
"""

import re
from datetime import datetime, timedelta
from typing import Optional
import pytz
from dateparser import parse as parse_date

from ..config import get_settings


class DateParser:
    """Date parsing utilities with Arabic and English support."""

    def __init__(self):
        self.settings = get_settings()
        self.tz = pytz.timezone(self.settings.timezone)

    def parse_natural_date(self, text: str, language: str = "ar") -> Optional[str]:
        """
        Parse natural language dates like 'بعد ٣ أيام' or 'next Sunday'.

        If the parsed result falls before today's date, the next logical
        occurrence is returned for day-of-week phrases. Otherwise, the method
        returns None when no future date makes sense (e.g., "yesterday").

        Args:
            text: Natural language date string
            language: Language hint ("ar" or "en")

        Returns:
            Date in YYYY-MM-DD format or None if parsing fails
        """
        try:
            settings = {"PREFER_DATES_FROM": "future"}
            if language == "ar":
                settings["PREFER_DAY_OF_MONTH"] = "first"

            parsed_date = parse_date(text, settings=settings, languages=[language])
            if not parsed_date:
                return self._parse_weekday_fallback(text)

            # Normalize parsed date to configured timezone
            if parsed_date.tzinfo is None:
                parsed_date = self.tz.localize(parsed_date)
            else:
                parsed_date = parsed_date.astimezone(self.tz)

            today = datetime.now(self.tz).date()
            result_date = parsed_date.date()

            if result_date < today:
                return self._handle_past_date(text, result_date, today)

            return result_date.strftime("%Y-%m-%d")

        except Exception:
            return None

    def _parse_weekday_fallback(self, text: str) -> Optional[str]:
        """Fallback parsing for weekday names."""
        lowered = text.strip().lower()
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
            "الاثنين": 0, "الإثنين": 0, "الأثنين": 0,
            "الثلاثاء": 1, "الأربعاء": 2, "الاربعاء": 2,
            "الخميس": 3, "الجمعة": 4, "السبت": 5,
            "الأحد": 6, "الاحد": 6,
        }

        for name, idx in weekday_map.items():
            if name in lowered:
                today = datetime.now(self.tz).date()
                days_ahead = (idx - today.weekday() + 7) % 7
                if "القادم" in lowered or days_ahead == 0:
                    days_ahead = (days_ahead or 7)
                return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

        return None

    def _handle_past_date(self, text: str, result_date: datetime.date, today: datetime.date) -> Optional[str]:
        """Handle cases where parsed date is in the past."""
        lowered = text.strip().lower()
        weekday_keywords = {
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "الاثنين", "الإثنين", "الثلاثاء", "الأربعاء", "الاربعاء",
            "الخميس", "الجمعة", "السبت", "الأحد", "الاحد"
        }

        if any(day in lowered for day in weekday_keywords):
            while result_date <= today:
                result_date += timedelta(days=7)
            return result_date.strftime("%Y-%m-%d")

        return None

    def is_valid_iso_date(self, date_str: str) -> bool:
        """Check if string is a valid ISO date (YYYY-MM-DD)."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False


class TimeParser:
    """Time parsing utilities with Arabic and English support."""

    def __init__(self):
        self.settings = get_settings()
        self.tz = pytz.timezone(self.settings.timezone)

    def parse_natural_time(self, text: str) -> Optional[str]:
        """
        Parse natural language times like 'صباحاً' or 'morning'.

        Args:
            text: Natural language time string

        Returns:
            Time in HH:MM format or None if parsing fails
        """
        time_mappings = {
            # Arabic
            "صباحاً": "09:00", "الصباح": "09:00",
            "ظهراً": "12:00", "الظهر": "12:00",
            "عصراً": "15:00", "العصر": "15:00",
            "مساءً": "18:00", "المساء": "18:00",
            "ليلاً": "20:00", "الليل": "20:00",
            # English
            "morning": "09:00", "noon": "12:00", "afternoon": "15:00",
            "evening": "18:00", "night": "20:00",
        }

        text_lower = text.lower().strip()
        if text_lower in time_mappings:
            return time_mappings[text_lower]

        try:
            parsed = parse_date(text, languages=["ar", "en"])
            if parsed:
                if parsed.tzinfo is None:
                    parsed = self.tz.localize(parsed)
                else:
                    parsed = parsed.astimezone(self.tz)
                return parsed.strftime("%H:%M")
        except Exception:
            pass

        return None

    def is_valid_time_format(self, time_str: str) -> bool:
        """Check if string is a valid time format (HH:MM)."""
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    def format_time_for_display(self, time_str: str) -> str:
        """Format time string for display purposes."""
        if not self.is_valid_time_format(time_str):
            return time_str

        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            return time_obj.strftime("%I:%M %p")
        except ValueError:
            return time_str
