import json
import pytest
from src.app.context_models import BookingContext
from src.tools.booking_agent_tool import update_booking_context


class W:
    def __init__(self, ctx):
        self.context = ctx


@pytest.mark.asyncio
async def test_update_user_name_and_phone_ok():
    ctx = BookingContext()
    w = W(ctx)
    body = json.dumps({"updates": {"user_name": " أحمد محمود ", "user_phone": "059-123-4567"}})
    res = await update_booking_context.on_invoke_tool(w, body)
    patch = res.ctx_patch
    assert patch.get("user_name") == "أحمد محمود"
    assert patch.get("user_phone") == "0591234567"


@pytest.mark.asyncio
async def test_update_user_phone_rejects_bad_format():
    ctx = BookingContext()
    w = W(ctx)
    bad = json.dumps({"updates": {"user_phone": "12345"}})
    res = await update_booking_context.on_invoke_tool(w, bad)
    assert "رقم الهاتف غير صالح" in res.public_text
    assert res.ctx_patch == {}
