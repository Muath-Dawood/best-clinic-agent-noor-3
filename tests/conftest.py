"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from noor_ai_agent.core.models.booking import BookingContext
from noor_ai_agent.core.enums import Gender, BookingStep
from noor_ai_agent.services.external import ExternalAPIService
from noor_ai_agent.services.booking import BookingService, ServiceDataProvider


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_external_api():
    """Mock external API service."""
    api = Mock(spec=ExternalAPIService)
    api.get_available_dates = AsyncMock(return_value={"data": ["2025-01-15", "2025-01-16"]})
    api.get_available_times = AsyncMock(return_value={"data": [{"time": "09:00"}, {"time": "10:00"}]})
    api.get_available_employees = AsyncMock(return_value={"data": [{"pm_si": "emp1", "name": "Dr. Test"}], "checkout_summary": {}})
    api.create_booking = AsyncMock(return_value={"result": True, "booking_id": "123"})
    api.lookup_patient = AsyncMock(return_value={"details": {"name": "Test Patient"}})
    api.send_whatsapp_message = AsyncMock(return_value=True)
    return api


@pytest.fixture
def mock_service_data():
    """Mock service data provider."""
    data = Mock(spec=ServiceDataProvider)
    data.get_services_by_gender = Mock(return_value=[
        {"title": "Test Service", "pm_si": "svc1", "price": "100.00", "duration": "00:30"}
    ])
    data.get_cus_sec_pm_si_by_gender = Mock(return_value="test_cus_sec")
    data.find_service_by_pm_si = Mock(return_value={"title": "Test Service", "pm_si": "svc1", "price_numeric": 100.0})
    return data


@pytest.fixture
def booking_service(mock_external_api, mock_service_data):
    """Create booking service with mocked dependencies."""
    return BookingService(mock_external_api, mock_service_data)


@pytest.fixture
def sample_booking_context():
    """Create a sample booking context for testing."""
    return BookingContext(
        user_name="Test User",
        user_phone="0591234567",
        gender=Gender.MALE,
        selected_services_pm_si=["svc1"],
        appointment_date="2025-01-15",
        appointment_time="09:00",
        employee_pm_si="emp1",
        employee_name="Dr. Test",
        next_booking_step=BookingStep.SELECT_EMPLOYEE,
    )


@pytest.fixture
def empty_booking_context():
    """Create an empty booking context for testing."""
    return BookingContext()
