import httpx
import pytest

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
