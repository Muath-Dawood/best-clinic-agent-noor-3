import httpx
import pytest

from src.app.patient_lookup import lookup_api


@pytest.mark.asyncio
async def test_lookup_api_success(monkeypatch):
    """lookup_api returns normalized data when status is true."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/api-ai-get-customer-details")
        payload = {"status": True, "data": {"details": {"name": "Ali"}}}
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    result = await lookup_api("0590000000")
    assert result == {"details": {"name": "Ali"}, "appointments": {"data": []}}


@pytest.mark.asyncio
async def test_lookup_api_status_false(monkeypatch):
    """lookup_api raises LookupError when status is false."""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"status": False, "data": {}}
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    with pytest.raises(LookupError):
        await lookup_api("0590000000")
