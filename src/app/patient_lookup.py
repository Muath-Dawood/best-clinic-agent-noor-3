from __future__ import annotations
import os
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number

load_dotenv()
BOOKING_API_BASE_URL = (os.getenv("BOOKING_API_BASE_URL") or "").rstrip("/")
BOOKING_API_TOKEN = os.getenv("BOOKING_API_TOKEN") or ""


async def fetch_patient_data_from_whatsapp_id(chat_id: str) -> Optional[Dict[str, Any]]:
    """
    Return a dict with patient 'details' and 'appointments' (shape up to your API),
    or None if nothing found / error. Adjust URLs/shape to your backend.
    """
    if not BOOKING_API_BASE_URL or not BOOKING_API_TOKEN:
        return None

    phone = parse_whatsapp_to_local_palestinian_number(chat_id)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Example endpoint — replace to match your API
            r = await client.get(
                f"{BOOKING_API_BASE_URL}/patients/by_phone",
                params={"phone": phone},
                headers={"Authorization": f"Bearer {BOOKING_API_TOKEN}"},
            )
            r.raise_for_status()
            payload = r.json()
    except Exception:
        return None

    # Normalize to a stable shape Noor can rely on.
    # Expecting something like: {"result": true, "data": { "details": {...}, "appointments": {"data": [...]}}}
    data = payload.get("data") if isinstance(payload, dict) else None
    if not data:
        return None

    # Ensure keys exist
    data.setdefault("details", {})
    data.setdefault("appointments", {"data": []})
    return data
