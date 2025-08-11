from __future__ import annotations
import os
from typing import Optional, Dict, Any
import httpx

from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number

# --- Best Clinic official lookup API (working path) ---
BEST_CLINIC_API_BASE = (
    os.getenv("BEST_CLINIC_API_BASE") or "https://www.bestclinic24.net"
).rstrip("/")
BEST_CLINIC_API_TOKEN = os.getenv("BEST_CLINIC_API_TOKEN") or ""
PATIENT_LOOKUP_TIMEOUT = float(os.getenv("PATIENT_LOOKUP_TIMEOUT", "10"))
BEST_CLINIC_API_PATH = "/api-ai-get-customer-details"


async def lookup_api(phone: str) -> Optional[Dict[str, Any]]:
    """
    Calls:  {BEST_CLINIC_API_BASE}/api-ai-get-customer-details
    Query:  identifier_type=PHONE, identifier_value=<05XXXXXXXX>, includes_data=details
    Returns normalized shape:
      {"details": {...}, "appointments": {"data": []}}
    """
    url = f"{BEST_CLINIC_API_BASE}{BEST_CLINIC_API_PATH}"
    params = {
        "identifier_type": "PHONE",
        "identifier_value": phone,
        "includes_data": "details",
    }
    headers = {}
    if BEST_CLINIC_API_TOKEN:
        headers["Authorization"] = f"Bearer {BEST_CLINIC_API_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=PATIENT_LOOKUP_TIMEOUT) as client:
            r = await client.get(url, params=params, headers=headers or None)
            r.raise_for_status()
            payload = r.json()
    except Exception:
        return None

    # Expect: {"status": true, "data": {"details": {...}}}
    if not (isinstance(payload, dict) and payload.get("status") is True):
        return None

    data = payload.get("data") or {}
    details = data.get("details") or {}
    if not isinstance(details, dict):
        return None

    # Endpoint doesn't return appointments; keep a stable, forward-compatible shape.
    return {"details": details, "appointments": {"data": []}}


async def fetch_patient_data_from_whatsapp_id(chat_id: str) -> Optional[Dict[str, Any]]:
    """
    Resolve WhatsApp chatId -> local phone '05XXXXXXXX', then query lookup_api().
    Returns normalized patient dict or None.
    """
    phone = parse_whatsapp_to_local_palestinian_number(chat_id)

    # The API expects local Palestinian format '05XXXXXXXX'
    if not (isinstance(phone, str) and phone.startswith("05") and len(phone) == 10):
        return None

    return await lookup_api(phone)
