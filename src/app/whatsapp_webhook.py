# src/app/whatsapp_webhook.py
from __future__ import annotations
import asyncio
import os
import time
from fastapi import APIRouter, Request, Response, status
from agents import SQLiteSession

from src.app.utils_text import extract_text_from_wa, split_for_whatsapp_by_bytes
from src.app.http_client import client as http_client

from src.app.context_models import BookingContext
from src.app.state_manager import get_state, touch_state
from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number
from src.app.patient_lookup import fetch_patient_data_from_whatsapp_id
from src.my_agents.noor_agent import run_noor_turn
from src.app.session_idle import update_last_seen, schedule_idle_watch
from src.app.logging import get_logger
from src.app.memory_prefetch import fetch_recent_summaries_text


# simple in-memory dedupe: last msgId per sender
_last_msgid: dict[str, str] = {}


# Export a router (main.py mounts it at prefix="/webhook")
router = APIRouter()

GREEN_ID = os.getenv("WA_GREEN_ID_INSTANCE", "").strip()
GREEN_TOKEN = os.getenv("WA_GREEN_API_TOKEN", "").strip()
GREEN_URL = (
    f"https://7105.api.greenapi.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
)
# Per Green-API documentation, the maximum size of a text message is 4096 characters.
# See: https://green-api.com/en/docs/ (falls back to safe default if docs unavailable)
GREEN_MAX_MESSAGE_LEN = 4096

def _split_for_green_api(text: str, limit: int = GREEN_MAX_MESSAGE_LEN) -> list[str]:
    """Split ``text`` into chunks not exceeding ``limit`` characters.

    Args:
        text: The message body to split.
        limit: Maximum length allowed per chunk.

    Returns:
        A list of message parts each with ``len(part) <= limit``.
    """
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]

logger = get_logger("noor.webhook")


def _verify_signature(request: Request) -> bool:
    return True

async def _send_whatsapp(chat_id: str, text: str) -> None:
    if not (GREEN_ID and GREEN_TOKEN):
        logger.warning("Skipping WhatsApp send: WA env not configured")
        return
    retries = 3
    client = http_client
    for chunk in _split_for_green_api(text):
        backoff = 1
        success = False
        for attempt in range(1, retries + 1):
            try:
                resp = await client.post(GREEN_URL, json={"chatId": chat_id, "message": chunk})
                if 200 <= resp.status_code < 300:
                    success = True
                    break
                logger.error(
                    "WhatsApp send failed: status=%s body=%s",
                    resp.status_code,
                    resp.text[:200],
                )
                if resp.status_code in {429} or resp.status_code >= 500:
                    if attempt < retries:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                break
            except Exception:
                logger.exception("WhatsApp send failed on attempt %d", attempt)
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                break
        if not success:
            return


@router.post("/wa")
async def receive_wa(request: Request):
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    text_in, had_attach = extract_text_from_wa(body)
    msg_id = body.get("idMessage")
    sender_id = body.get("senderData", {}).get("chatId")

    logger.info({"event": "wa_inbound", "sender": sender_id, "msg_id": msg_id, "ts": time.time()})

    if os.getenv("WA_VERIFY_SECRET"):
        ok = _verify_signature(request)
        if not ok:
            logger.warning({"event": "wa_verify_failed", "sender": sender_id, "msg_id": msg_id})

    if sender_id and msg_id:
        last = _last_msgid.get(sender_id)
        if last == msg_id:
            return {"ok": True, "dedupe": True}
        _last_msgid[sender_id] = msg_id

    if had_attach and not text_in:
        await _send_whatsapp(sender_id, "استقبلت ملف/صورة. رجاءً اكتب رسالتك نصّياً حتى أقدر أساعدك 🌟")
        return {"ok": True}

    if not text_in:
        return {"status": "ignored"}

    # --- Load or create state (context + session) ---
    state = await get_state(sender_id)
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

    ctx.user_has_attachments = had_attach

    if ctx.patient_data is None:
        try:
            patient = await fetch_patient_data_from_whatsapp_id(sender_id)
        except Exception as e:
            # absolute last line of defense; never crash a webhook on lookup
            logger.error(f"[lookup] unexpected error for {ctx.user_phone}: {e}")
            patient = None

        if patient:
            details = patient.get("details") or {}
            ctx.patient_data = details
            ctx.customer_type = "exists"
            # ✅ prefer DB name over WhatsApp display name
            db_name = details.get("name")
            if isinstance(db_name, str) and db_name.strip():
                ctx.user_name = db_name.strip()
            elif not ctx.user_name:
                wa_display_name = body.get("senderData", {}).get("senderName")
                if isinstance(wa_display_name, str) and wa_display_name.strip():
                    ctx.user_name = wa_display_name.strip()
            logger.info(f"[lookup] FOUND: {ctx.user_phone} → {ctx.user_name or '<no name>'}")
        else:
            # No DB hit: proceed as new user, keep WA name/phone if available
            ctx.customer_type = "new"
            if not ctx.user_name:
                wa_display_name = body.get("senderData", {}).get("senderName")
                if isinstance(wa_display_name, str) and wa_display_name.strip():
                    ctx.user_name = wa_display_name.strip()
            logger.info(f"[lookup] NOT FOUND: {ctx.user_phone} (proceed as new)")

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

    # Identify the chat for idempotency keys / personalization
    try:
        ctx.chat_id = sender_id  # used by booking create to de-duplicate
    except Exception:
        pass

    # --- Run Noor with session + context ---
    try:
        reply = await run_noor_turn(
            user_input=text_in,
            ctx=ctx,
            session=session,
        )
    except Exception:
        logger.exception("run_noor_turn failed")
        reply = "عذرًا، في خلل تقني بسيط الآن. جرّب بعد قليل لو تكرّمت."

    # Send replies (split by bytes)
    for chunk in split_for_whatsapp_by_bytes(reply):
        await _send_whatsapp(sender_id, chunk)
    try:
        await touch_state(sender_id, ctx, session)
    except Exception:
        logger.exception("touch_state failed for %s", sender_id)

    # ---- idle summarization hooks ----
    await update_last_seen(sender_id)
    await schedule_idle_watch(sender_id)

    return {"status": "ok"}
