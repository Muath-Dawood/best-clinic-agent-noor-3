import asyncio
from urllib.parse import quote_plus
import httpx
from fastapi import APIRouter, Request, Response, status

from .settings import settings
from .logging import get_logger
from .state_manager import get_state, touch_state
from .context_models import BookingContext
from ..agents.noor_agent import run_noor_turn
from .patient_lookup import fetch_patient_data_from_whatsapp_id
from .middleware import SecurityHeaders
from .errors import user_friendly_message
from .parse_phone_number import parse_whatsapp_to_local_palestinian_number

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

    try:
        sender_id = payload["senderData"]["chatId"]
        text_in = payload["messageData"]["textMessageData"]["textMessage"]
    except KeyError:
        return Response(content='{"status":"ignored"}', media_type="application/json")

    log.info("incoming", extra={"sender": sender_id, "text": text_in})

    # Load or create state
    cached = get_state(sender_id)
    if cached:
        ctx, session = cached
    else:
        ctx = BookingContext()
        session = SQLiteSession(sender_id, "noor_sessions.db")

    # Enrich context if missing
    if not ctx.user_phone:
        try:
            ctx.user_phone = parse_whatsapp_to_local_palestinian_number(sender_id)
        except ValueError:
            pass
    if not ctx.user_name:
        ctx.user_name = payload["senderData"].get("senderName")
    if ctx.patient_data is None:
        try:
            patient = await fetch_patient_data_from_whatsapp_id(sender_id)
            if patient:
                ctx.patient_data = patient.get("details")
                ctx.previous_appointments = patient.get("appointments", {}).get(
                    "data", []
                )
        except Exception as exc:
            log.warning("patient_lookup_failed", extra={"err": str(exc)})

    # Run agent
    try:
        reply = await run_noor_turn(user_input=text_in, context=ctx, session=session)
    except Exception as exc:
        log.exception("agent_failed")
        reply = user_friendly_message(exc)

    # Save state & send reply
    touch_state(sender_id, ctx, session)
    asyncio.create_task(_send_whatsapp(sender_id, reply))

    return Response(content='{"status":"ok"}', media_type="application/json")
