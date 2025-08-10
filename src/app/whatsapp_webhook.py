from __future__ import annotations
import asyncio
import os
import httpx
from fastapi import FastAPI, Request, Response, status
from agents import SQLiteSession

from src.app.context_models import BookingContext
from src.app.state_manager import get_state, touch_state
from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number
from src.app.patient_lookup import fetch_patient_data_from_whatsapp_id
from src.my_agents.noor_agent import run_noor_turn

app = FastAPI()

GREEN_ID = os.getenv("WA_GREEN_ID_INSTANCE", "").strip()
GREEN_TOKEN = os.getenv("WA_GREEN_API_TOKEN", "").strip()
GREEN_URL = (
    f"https://7105.api.greenapi.com/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
)


async def _send_whatsapp(chat_id: str, text: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(GREEN_URL, json={"chatId": chat_id, "message": text})
    except Exception:
        pass  # swallow send errors


def fire_and_forget_send(chat_id: str, text: str) -> None:
    asyncio.create_task(_send_whatsapp(chat_id, text))


@app.post("/webhook/wa")
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
    else:
        ctx = BookingContext()
        session = SQLiteSession(sender_id, "noor_sessions.db")

    # --- Enrich context ONCE (silent) ---
    if not ctx.user_phone:
        try:
            ctx.user_phone = parse_whatsapp_to_local_palestinian_number(sender_id)
        except Exception:
            pass

    if not ctx.user_name:
        # WhatsApp usually gives a display name in senderData.senderName
        ctx.user_name = body.get("senderData", {}).get("senderName")

    if ctx.patient_data is None:
        patient = await fetch_patient_data_from_whatsapp_id(sender_id)
        if patient:
            ctx.patient_data = patient.get("details")
            ctx.previous_appointments = patient.get("appointments", {}).get("data", [])

    # --- Run Noor with session + context ---
    try:
        reply = await run_noor_turn(user_input=text_in, ctx=ctx, session=session)
    except Exception:
        reply = "عذرًا، في خلل تقني بسيط الآن. جرّب بعد قليل لو تكرّمت."

    # Persist state and send reply
    touch_state(sender_id, ctx, session)
    fire_and_forget_send(sender_id, reply)

    return Response(content='{"status":"ok"}', media_type="application/json")
