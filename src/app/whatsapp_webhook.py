import asyncio
import httpx
from fastapi import APIRouter, Request, Response, status
from urllib.parse import quote_plus

from .settings import settings
from .logging import get_logger
from ..agents.noor_agent import run_noor_turn

router = APIRouter()
log = get_logger("wa")

def _green_api_url():
    if not (settings.wa_green_id_instance and settings.wa_green_api_token):
        return None
    return (
        f"https://7105.api.greenapi.com/waInstance{quote_plus(settings.wa_green_id_instance)}"
        f"/sendMessage/{quote_plus(settings.wa_green_api_token)}"
    )

async def _send_whatsapp(chat_id: str, text: str):
    try:
        url = _green_api_url()
        if not url:
            log.warning("Green API creds missing; skipping send")
            return
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={"chatId": chat_id, "message": text})
            log.info("WA send", extra={"status": r.status_code})
    except Exception as exc:
        log.exception("WA send failed", exc_info=exc)

@router.post("/wa")
async def receive_wa(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # Only handle text messages; Green-API sample structure
    try:
        sender_id = payload["senderData"]["chatId"]
        text_in = payload["messageData"]["textMessageData"]["textMessage"]
    except KeyError:
        return Response(content='{"status":"ignored"}', media_type="application/json")

    log.info("incoming", extra={"sender": sender_id, "text": text_in})

    # One LLM turn
    reply = await run_noor_turn(user_input=text_in)

    # fire-and-forget send
    asyncio.create_task(_send_whatsapp(sender_id, reply))

    return Response(content='{"status":"ok"}', media_type="application/json")
