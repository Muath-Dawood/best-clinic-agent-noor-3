# src/app/whatsapp_webhook.py
from __future__ import annotations
import asyncio
import os
import httpx
from fastapi import APIRouter, Request, Response, status
from agents import SQLiteSession

from src.app.context_models import BookingContext
from src.app.state_manager import get_state, touch_state
from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number
from src.app.patient_lookup import fetch_patient_data_from_whatsapp_id
from src.my_agents.noor_agent import run_noor_turn
from src.app.session_idle import update_last_seen, schedule_idle_watch
from src.app.logging import get_logger
from src.app.memory_prefetch import fetch_recent_summaries_text


# Export a router (main.py mounts it at prefix="/webhook")
router = APIRouter()

GREEN_ID = os.getenv("WA_GREEN_ID_INSTANCE", "").strip()
GREEN_TOKEN = os.getenv("WA_GREEN_API_TOKEN", "").strip()
GREEN_URL = (
    f"https://7105.api.greenapi.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
)

logger = get_logger("noor.webhook")


async def _send_whatsapp(chat_id: str, text: str) -> None:
    if not (GREEN_ID and GREEN_TOKEN):
        logger.warning("Skipping WhatsApp send: WA env not configured")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(GREEN_URL, json={"chatId": chat_id, "message": text})
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")


def fire_and_forget_send(chat_id: str, text: str) -> None:
    asyncio.create_task(_send_whatsapp(chat_id, text))


@router.post("/wa")
async def receive_wa(request: Request) -> Response:
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # Only handle plain text messages
    try:
        sender_id = body["senderData"]["chatId"]  # e.g. '97259XXXXXXX@c.us'
        text_in = body["messageData"]["textMessageData"]["textMessage"]
    except KeyError:
        return Response(content='{"status":"ignored"}', media_type="application/json")

    # --- Load or create state (context + session) ---
    state = get_state(sender_id)
    if state:
        ctx, session = state
        is_new_session = False
    else:
        ctx = BookingContext()
        session = SQLiteSession(sender_id, "noor_sessions.db")
        is_new_session = True

    # --- Enrich context ONCE (silent) ---
    if not ctx.user_phone:
        try:
            ctx.user_phone = parse_whatsapp_to_local_palestinian_number(sender_id)
        except Exception:
            pass

    if not ctx.user_name:
        # WhatsApp usually gives a display name in senderData.senderName
        ctx.user_name = body.get("senderData", {}).get("senderName")

    ctx.user_has_attachments = False

    if ctx.patient_data is None:
        patient = await fetch_patient_data_from_whatsapp_id(sender_id)
        if patient:
            details = patient.get("details") or {}
            ctx.patient_data = details

            # ✅ always prefer DB name over WhatsApp display name
            db_name = details.get("name")
            if isinstance(db_name, str) and db_name.strip():
                ctx.user_name = db_name.strip()
            elif not ctx.user_name:
                # fallback to WhatsApp sender display name if we still don't have one
                wa_display_name = body.get("senderData", {}).get("senderName")
                if isinstance(wa_display_name, str) and wa_display_name.strip():
                    ctx.user_name = wa_display_name.strip()

            logger.info(
                f"[lookup] FOUND: {ctx.user_phone} → {ctx.user_name or '<no name>'}"
            )
        else:
            # optional: fallback to WhatsApp sender name when no DB record
            if not ctx.user_name:
                wa_display_name = body.get("senderData", {}).get("senderName")
                if isinstance(wa_display_name, str) and wa_display_name.strip():
                    ctx.user_name = wa_display_name.strip()
            logger.info(f"[lookup] NOT FOUND: {ctx.user_phone}")

    # Prefetch last summary only at the start of a brand-new session
    if is_new_session:
        try:
            parts, combined = await fetch_recent_summaries_text(
                user_id=sender_id, user_phone=ctx.user_phone
            )
            ctx.previous_summaries = parts
            logger.info(
                f"prefetch: feeding {len(parts)} summaries into first turn "
                f"(chars={len(combined)}) for {sender_id}"
            )
        except Exception as e:
            logger.error(f"prefetch: error for {sender_id}: {e}")

    # --- Run Noor with session + context ---
    try:
        reply = await run_noor_turn(
            user_input=text_in,
            ctx=ctx,
            session=session,
        )
    except Exception:
        reply = "عذرًا، في خلل تقني بسيط الآن. جرّب بعد قليل لو تكرّمت."

    # Persist state and send reply
    touch_state(sender_id, ctx, session)
    fire_and_forget_send(sender_id, reply)

    # ---- idle summarization hooks ----
    await update_last_seen(sender_id)
    await schedule_idle_watch(sender_id)

    return Response(content='{"status":"ok"}', media_type="application/json")
