import datetime as dt
import httpx
import pytest

import src.tools.booking_tool as booking_tool_module
from src.tools.booking_tool import booking_tool, BookingFlowError


@pytest.mark.asyncio
async def test_create_booking_success(monkeypatch):
    """Booking succeeds when API returns result=true."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/BOKINNEW")
        return httpx.Response(200, json={"result": True, "data": {"booking_id": 1}})

    transport = httpx.MockTransport(handler)

    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    result = await booking_tool.create_booking(
        date="2024-01-01",
        time="09:00",
        employee_pm_si="emp123",
        services_pm_si=["svc1"],
        customer_info={"name": "Ali", "phone": "0590000000"},
        gender="male",
    )

    assert result["data"]["booking_id"] == 1


@pytest.mark.asyncio
async def test_create_booking_failure(monkeypatch):
    """Booking raises BookingFlowError on API failure."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": False, "message": "No times"})

    transport = httpx.MockTransport(handler)

    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    with pytest.raises(BookingFlowError) as exc:
        await booking_tool.create_booking(
            date="2024-01-01",
            time="09:00",
            employee_pm_si="emp123",
            services_pm_si=["svc1"],
            customer_info={"name": "Ali", "phone": "0590000000"},
            gender="male",
        )

    assert "API error" in str(exc.value)


def test_parse_natural_date_rolls_over_past_weekday(monkeypatch):
    class FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2024, 1, 1, tzinfo=tz)

    def fake_parse(text, settings=None, languages=None):
        return dt.datetime(2023, 12, 31)

    monkeypatch.setattr(booking_tool_module, "datetime", FixedDateTime)
    monkeypatch.setattr(booking_tool_module, "parse_date", fake_parse)

    result = booking_tool.parse_natural_date("Sunday", "en")
    assert result == "2024-01-07"


def test_parse_natural_date_returns_none_for_past_date(monkeypatch):
    class FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2024, 1, 1, tzinfo=tz)

    def fake_parse(text, settings=None, languages=None):
        return dt.datetime(2023, 12, 31)

    monkeypatch.setattr(booking_tool_module, "datetime", FixedDateTime)
    monkeypatch.setattr(booking_tool_module, "parse_date", fake_parse)

    result = booking_tool.parse_natural_date("2023-12-31", "en")
    assert result is None
