"""
Tests for utility functions.
"""

import pytest
from noor_ai_agent.utils.phone import PhoneNumberParser
from noor_ai_agent.utils.date import DateParser, TimeParser
from noor_ai_agent.utils.validation import ValidationUtils
from noor_ai_agent.utils.text import TextProcessor


class TestPhoneNumberParser:
    """Test phone number parsing utilities."""

    def test_parse_whatsapp_to_local_palestinian_number(self):
        """Test parsing WhatsApp chat ID to Palestinian phone number."""
        parser = PhoneNumberParser()

        # Test valid WhatsApp chat ID
        result = parser.parse_whatsapp_to_local_palestinian_number("972599123456@c.us")
        assert result == "0599123456"

        # Test invalid input
        result = parser.parse_whatsapp_to_local_palestinian_number("invalid")
        assert result is None

    def test_normalize_to_local_format(self):
        """Test normalizing phone numbers to local format."""
        parser = PhoneNumberParser()

        # Test various formats
        assert parser.normalize_to_local_format("+970599123456") == "0599123456"
        assert parser.normalize_to_local_format("972599123456") == "0599123456"
        assert parser.normalize_to_local_format("599123456") == "0599123456"
        assert parser.normalize_to_local_format("0599123456") == "0599123456"

        # Test invalid formats
        assert parser.normalize_to_local_format("123") is None
        assert parser.normalize_to_local_format("") is None

    def test_is_valid_palestinian_number(self):
        """Test Palestinian phone number validation."""
        parser = PhoneNumberParser()

        # Valid numbers
        assert parser.is_valid_palestinian_number("0599123456") is True
        assert parser.is_valid_palestinian_number("+970599123456") is True

        # Invalid numbers
        assert parser.is_valid_palestinian_number("123") is False
        assert parser.is_valid_palestinian_number("059912345") is False  # Too short
        assert parser.is_valid_palestinian_number("") is False


class TestDateParser:
    """Test date parsing utilities."""

    def test_parse_natural_date_arabic(self):
        """Test parsing Arabic natural language dates."""
        parser = DateParser()

        # Test weekday parsing
        result = parser.parse_natural_date("الاثنين القادم", "ar")
        assert result is not None
        assert len(result) == 10  # YYYY-MM-DD format

        # Test invalid input
        result = parser.parse_natural_date("invalid date", "ar")
        assert result is None

    def test_parse_natural_date_english(self):
        """Test parsing English natural language dates."""
        parser = DateParser()

        # Test weekday parsing
        result = parser.parse_natural_date("next Monday", "en")
        assert result is not None
        assert len(result) == 10  # YYYY-MM-DD format

    def test_is_valid_iso_date(self):
        """Test ISO date validation."""
        parser = DateParser()

        # Valid dates
        assert parser.is_valid_iso_date("2025-01-15") is True
        assert parser.is_valid_iso_date("2024-12-31") is True

        # Invalid dates
        assert parser.is_valid_iso_date("2025-13-01") is False
        assert parser.is_valid_iso_date("invalid") is False
        assert parser.is_valid_iso_date("2025-01-32") is False


class TestTimeParser:
    """Test time parsing utilities."""

    def test_parse_natural_time_arabic(self):
        """Test parsing Arabic natural language times."""
        parser = TimeParser()

        # Test predefined mappings
        assert parser.parse_natural_time("صباحاً") == "09:00"
        assert parser.parse_natural_time("الظهر") == "12:00"
        assert parser.parse_natural_time("مساءً") == "18:00"

    def test_parse_natural_time_english(self):
        """Test parsing English natural language times."""
        parser = TimeParser()

        # Test predefined mappings
        assert parser.parse_natural_time("morning") == "09:00"
        assert parser.parse_natural_time("afternoon") == "15:00"
        assert parser.parse_natural_time("evening") == "18:00"

    def test_is_valid_time_format(self):
        """Test time format validation."""
        parser = TimeParser()

        # Valid times
        assert parser.is_valid_time_format("09:00") is True
        assert parser.is_valid_time_format("23:59") is True
        assert parser.is_valid_time_format("00:00") is True

        # Invalid times
        assert parser.is_valid_time_format("25:00") is False
        assert parser.is_valid_time_format("12:60") is False
        assert parser.is_valid_time_format("invalid") is False


class TestValidationUtils:
    """Test validation utilities."""

    def test_validate_palestinian_phone(self):
        """Test Palestinian phone number validation."""
        # Valid numbers
        is_valid, error = ValidationUtils.validate_palestinian_phone("0599123456")
        assert is_valid is True
        assert error is None

        is_valid, error = ValidationUtils.validate_palestinian_phone("+970599123456")
        assert is_valid is True
        assert error is None

        # Invalid numbers
        is_valid, error = ValidationUtils.validate_palestinian_phone("123")
        assert is_valid is False
        assert error is not None

        is_valid, error = ValidationUtils.validate_palestinian_phone("")
        assert is_valid is False
        assert error is not None

    def test_validate_name(self):
        """Test name validation."""
        # Valid names
        is_valid, error = ValidationUtils.validate_name("أحمد محمد")
        assert is_valid is True
        assert error is None

        is_valid, error = ValidationUtils.validate_name("John Doe")
        assert is_valid is True
        assert error is None

        # Invalid names
        is_valid, error = ValidationUtils.validate_name("")
        assert is_valid is False
        assert error is not None

        is_valid, error = ValidationUtils.validate_name("a")  # Too short
        assert is_valid is False
        assert error is not None

    def test_sanitize_text(self):
        """Test text sanitization."""
        # Test control character removal
        text = "Hello\x00World\x01Test"
        sanitized = ValidationUtils.sanitize_text(text)
        assert "\x00" not in sanitized
        assert "\x01" not in sanitized

        # Test whitespace normalization
        text = "Hello    World\n\nTest"
        sanitized = ValidationUtils.sanitize_text(text)
        assert "    " not in sanitized
        assert "\n\n" not in sanitized


class TestTextProcessor:
    """Test text processing utilities."""

    def test_normalize_arabic_text(self):
        """Test Arabic text normalization."""
        processor = TextProcessor()

        text = "أحمد محمد علي"
        normalized = processor.normalize_arabic_text(text)
        assert "أ" not in normalized  # Should be converted to ا
        assert "ى" not in normalized  # Should be converted to ي

    def test_clean_whatsapp_text(self):
        """Test WhatsApp text cleaning."""
        processor = TextProcessor()

        text = "Hello\nThis is a file upload\nWorld"
        cleaned = processor.clean_whatsapp_text(text)
        assert "file upload" not in cleaned

        text = "مرحبا\nهذا ملف مرفق\nالعالم"
        cleaned = processor.clean_whatsapp_text(text)
        assert "ملف مرفق" not in cleaned

    def test_split_text_for_whatsapp(self):
        """Test text splitting for WhatsApp."""
        processor = TextProcessor()

        # Short text should not be split
        text = "Hello World"
        chunks = processor.split_text_for_whatsapp(text, 100)
        assert len(chunks) == 1
        assert chunks[0] == text

        # Long text should be split
        text = "Hello " * 1000  # Very long text
        chunks = processor.split_text_for_whatsapp(text, 100)
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
