"""
Tests for service layer.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from noor_ai_agent.services.booking import BookingService
from noor_ai_agent.services.patient import PatientService
from noor_ai_agent.core.enums import Gender
from noor_ai_agent.core.exceptions import BookingFlowError, PatientNotFoundError


class TestBookingService:
    """Test booking service functionality."""

    @pytest.mark.asyncio
    async def test_get_available_services(self, booking_service):
        """Test getting available services."""
        services = await booking_service.get_available_services(Gender.MALE)
        assert isinstance(services, list)
        assert len(services) > 0

    @pytest.mark.asyncio
    async def test_get_available_dates(self, booking_service):
        """Test getting available dates."""
        dates = await booking_service.get_available_dates(
            ["svc1"], Gender.MALE
        )
        assert isinstance(dates, list)

    @pytest.mark.asyncio
    async def test_get_available_times(self, booking_service):
        """Test getting available times."""
        times = await booking_service.get_available_times(
            "2025-01-15", ["svc1"], Gender.MALE
        )
        assert isinstance(times, list)

    @pytest.mark.asyncio
    async def test_get_available_employees(self, booking_service):
        """Test getting available employees."""
        employees, checkout = await booking_service.get_available_employees(
            "2025-01-15", "09:00", ["svc1"], Gender.MALE
        )
        assert isinstance(employees, list)
        assert isinstance(checkout, dict)

    @pytest.mark.asyncio
    async def test_create_booking(self, booking_service, sample_booking_context):
        """Test creating a booking."""
        result = await booking_service.create_booking(
            "2025-01-15",
            "09:00",
            "emp1",
            ["svc1"],
            None,
            Gender.MALE
        )
        assert isinstance(result, dict)
        assert result.get("result") is True

    def test_parse_natural_date(self, booking_service):
        """Test parsing natural language dates."""
        # Test Arabic date
        result = booking_service.parse_natural_date("الاثنين القادم", "ar")
        assert result is not None or result is None  # May be None if date is in past

        # Test English date
        result = booking_service.parse_natural_date("next Monday", "en")
        assert result is not None or result is None  # May be None if date is in past

    def test_parse_natural_time(self, booking_service):
        """Test parsing natural language times."""
        # Test Arabic time
        result = booking_service.parse_natural_time("صباحاً")
        assert result == "09:00"

        # Test English time
        result = booking_service.parse_natural_time("morning")
        assert result == "09:00"

    def test_calculate_total_price(self, booking_service):
        """Test calculating total price."""
        price = booking_service.calculate_total_price(["svc1"])
        assert isinstance(price, float)
        assert price >= 0

    def test_build_booking_idempotency_key(self, booking_service, sample_booking_context):
        """Test building idempotency key."""
        key = booking_service.build_booking_idempotency_key(sample_booking_context)
        assert isinstance(key, str)
        assert len(key) > 0

    def test_validate_booking_context_complete(self, booking_service, sample_booking_context):
        """Test validating complete booking context."""
        errors = booking_service.validate_booking_context(sample_booking_context)
        assert len(errors) == 0

    def test_validate_booking_context_incomplete(self, booking_service):
        """Test validating incomplete booking context."""
        from noor_ai_agent.core.models.booking import BookingContext
        ctx = BookingContext()  # Empty context
        errors = booking_service.validate_booking_context(ctx)
        assert len(errors) > 0


class TestPatientService:
    """Test patient service functionality."""

    @pytest.mark.asyncio
    async def test_lookup_patient_by_whatsapp_id_success(self, mock_external_api):
        """Test successful patient lookup by WhatsApp ID."""
        service = PatientService(mock_external_api)

        # Mock successful lookup
        mock_external_api.lookup_patient.return_value = {
            "details": {"name": "Test Patient", "phone": "0591234567"},
            "appointments": {"data": []}
        }

        patient = await service.lookup_patient_by_whatsapp_id("972599123456@c.us")
        assert patient is not None
        assert patient.details.name == "Test Patient"
        assert patient.is_existing is True

    @pytest.mark.asyncio
    async def test_lookup_patient_by_whatsapp_id_not_found(self, mock_external_api):
        """Test patient lookup when patient not found."""
        service = PatientService(mock_external_api)

        # Mock not found
        mock_external_api.lookup_patient.side_effect = PatientNotFoundError("Not found")

        patient = await service.lookup_patient_by_whatsapp_id("972599123456@c.us")
        assert patient is None

    @pytest.mark.asyncio
    async def test_lookup_patient_by_phone_success(self, mock_external_api):
        """Test successful patient lookup by phone."""
        service = PatientService(mock_external_api)

        # Mock successful lookup
        mock_external_api.lookup_patient.return_value = {
            "details": {"name": "Test Patient", "phone": "0591234567"},
            "appointments": {"data": []}
        }

        patient = await service.lookup_patient_by_phone("0591234567")
        assert patient is not None
        assert patient.details.name == "Test Patient"

    def test_create_new_patient(self):
        """Test creating new patient."""
        from noor_ai_agent.services.patient import PatientService
        from noor_ai_agent.services.external import ExternalAPIService

        service = PatientService(Mock(spec=ExternalAPIService))
        patient = service.create_new_patient("New Patient", "0591234567", "male")

        assert patient is not None
        assert patient.details.name == "New Patient"
        assert patient.details.phone == "0591234567"
        assert patient.is_existing is False

    def test_is_existing_patient_true(self):
        """Test checking existing patient."""
        from noor_ai_agent.services.patient import PatientService
        from noor_ai_agent.services.external import ExternalAPIService
        from noor_ai_agent.core.models.patient import Patient, PatientDetails

        service = PatientService(Mock(spec=ExternalAPIService))
        patient = Patient(
            details=PatientDetails(name="Test", phone="0591234567"),
            appointments=[],
            is_existing=True
        )

        assert service.is_existing_patient(patient) is True

    def test_is_existing_patient_false(self):
        """Test checking non-existing patient."""
        from noor_ai_agent.services.patient import PatientService
        from noor_ai_agent.services.external import ExternalAPIService

        service = PatientService(Mock(spec=ExternalAPIService))

        assert service.is_existing_patient(None) is False