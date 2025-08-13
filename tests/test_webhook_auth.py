import importlib
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_webhook_requires_token(monkeypatch):
    monkeypatch.setenv("WA_WEBHOOK_TOKEN", "expected")
    from src.app import whatsapp_webhook
    importlib.reload(whatsapp_webhook)

    app = FastAPI()
    app.include_router(whatsapp_webhook.router, prefix="/webhook")

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/webhook/wa", json={})
        assert resp.status_code == 401

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/webhook/wa", headers={"X-WA-TOKEN": "wrong"}, json={}
        )
        assert resp.status_code == 401
