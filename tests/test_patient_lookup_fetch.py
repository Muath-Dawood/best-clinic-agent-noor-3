import httpx
import pytest

from src.app.patient_lookup import fetch_patient_data_from_whatsapp_id


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.mark.asyncio
async def test_fetch_patient_handles_404(monkeypatch):
    async def boom(_):
        raise httpx.HTTPStatusError("404", request=None, response=FakeResponse(404))

    monkeypatch.setattr("src.app.patient_lookup.lookup_api", boom)
    # valid WA id to pass formatting gate
    result = await fetch_patient_data_from_whatsapp_id("972591234567@c.us")
    assert result is None

