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


def test_parse_natural_date_arabic_weekdays(monkeypatch):
    class FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2024, 1, 1, tzinfo=tz)

    monkeypatch.setattr(booking_tool_module, "datetime", FixedDateTime)
    monkeypatch.setattr(
        booking_tool_module, "parse_date", lambda text, settings=None, languages=None: None
    )

    assert booking_tool.parse_natural_date("الاثنين القادم", "ar") == "2024-01-08"
    assert booking_tool.parse_natural_date("يوم الجمعة", "ar") == "2024-01-05"


def test_parse_natural_datetime_extracts_time(monkeypatch):
    class FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2024, 1, 1, tzinfo=tz)

    def fake_parse(text, settings=None, languages=None):
        return dt.datetime(2024, 1, 4, 17, 0)

    monkeypatch.setattr(booking_tool_module, "datetime", FixedDateTime)
    monkeypatch.setattr(booking_tool_module, "parse_date", fake_parse)

    text = "الخميس الساعة 5 مساءً"
    assert booking_tool.parse_natural_date(text, "ar") == "2024-01-04"
    assert booking_tool.parse_natural_time(text) == "17:00"


@pytest.mark.asyncio
async def test_get_available_times_normalizes_and_filters(monkeypatch):
    async def fake_api_call(endpoint, data, cus_sec_pm_si):
        return {"data": ["09:00", "", " \t", {"time": "10:00"}, {"time": ""}, None, 123]}

    monkeypatch.setattr(booking_tool, "_make_api_call", fake_api_call)

    result = await booking_tool.get_available_times("2024-06-01", ["svc1"], "male")
    assert result == [{"time": "09:00"}, {"time": "10:00"}]
