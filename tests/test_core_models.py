"""
Tests for core models.
"""

import pytest
from noor_ai_agent.core.models.booking import BookingContext, BookingContextUpdate
from noor_ai_agent.core.enums import Gender, BookingStep, CustomerType


class TestBookingContext:
    """Test BookingContext model."""

    def test_effective_gender_default(self):
        """Test effective_gender returns default when no gender set."""
        ctx = BookingContext()
        assert ctx.effective_gender() == Gender.MALE

    def test_effective_gender_subject_priority(self):
        """Test effective_gender prioritizes subject_gender."""
        ctx = BookingContext(
            gender=Gender.MALE,
            subject_gender=Gender.FEMALE,
            booking_for_self=False
        )
        assert ctx.effective_gender() == Gender.FEMALE

    def test_effective_gender_user_gender(self):
        """Test effective_gender uses user gender when no subject gender."""
        ctx = BookingContext(gender=Gender.FEMALE)
        assert ctx.effective_gender() == Gender.FEMALE

    def test_is_new_customer_true(self):
        """Test is_new_customer returns True for new customers."""
        ctx = BookingContext(customer_type=CustomerType.NEW)
        assert ctx.is_new_customer() is True

        ctx = BookingContext(patient_data=None)
        assert ctx.is_new_customer() is True

    def test_is_new_customer_false(self):
        """Test is_new_customer returns False for existing customers."""
        ctx = BookingContext(
            customer_type=CustomerType.EXISTING,
            patient_data={"name": "Test"}
        )
        assert ctx.is_new_customer() is False

    def test_has_required_booking_info_complete(self):
        """Test has_required_booking_info with complete info."""
        ctx = BookingContext(
            selected_services_pm_si=["svc1"],
            appointment_date="2025-01-15",
            appointment_time="09:00",
            employee_pm_si="emp1"
        )
        assert ctx.has_required_booking_info() is True

    def test_has_required_booking_info_incomplete(self):
        """Test has_required_booking_info with incomplete info."""
        ctx = BookingContext(
            selected_services_pm_si=["svc1"],
            appointment_date="2025-01-15"
            # Missing time and employee
        )
        assert ctx.has_required_booking_info() is False

    def test_get_subject_info_self_booking(self):
        """Test get_subject_info for self booking."""
        ctx = BookingContext(
            user_name="Test User",
            user_phone="0591234567",
            gender=Gender.MALE,
            booking_for_self=True
        )
        info = ctx.get_subject_info()
        assert info["name"] == "Test User"
        assert info["phone"] == "0591234567"
        assert info["gender"] == Gender.MALE

    def test_get_subject_info_other_booking(self):
        """Test get_subject_info for booking for someone else."""
        ctx = BookingContext(
            user_name="Test User",
            user_phone="0591234567",
            subject_name="Subject User",
            subject_phone="0597654321",
            subject_gender=Gender.FEMALE,
            booking_for_self=False
        )
        info = ctx.get_subject_info()
        assert info["name"] == "Subject User"
        assert info["phone"] == "0597654321"
        assert info["gender"] == Gender.FEMALE


class TestBookingContextUpdate:
    """Test BookingContextUpdate model."""

    def test_model_validation(self):
        """Test model validation works correctly."""
        update = BookingContextUpdate(
            selected_services_pm_si=["svc1"],
            appointment_date="2025-01-15",
            gender=Gender.MALE
        )
        assert update.selected_services_pm_si == ["svc1"]
        assert update.appointment_date == "2025-01-15"
        assert update.gender == Gender.MALE

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError):
            BookingContextUpdate(
                selected_services_pm_si=["svc1"],
                invalid_field="test"  # This should raise an error
            )
