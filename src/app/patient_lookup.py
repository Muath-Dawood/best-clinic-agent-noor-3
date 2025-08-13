from __future__ import annotations
import os
from typing import Optional, Dict, Any
import httpx

from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number
from src.app.logging import get_logger

# --- Best Clinic official lookup API (working path) ---
BEST_CLINIC_API_BASE = (
    os.getenv("BEST_CLINIC_API_BASE") or "https://www.bestclinic24.net"
).rstrip("/")
BEST_CLINIC_API_TOKEN = os.getenv("BEST_CLINIC_API_TOKEN") or ""
PATIENT_LOOKUP_TIMEOUT = float(os.getenv("PATIENT_LOOKUP_TIMEOUT", "10"))
BEST_CLINIC_API_PATH = "/api-ai-get-customer-details"

logger = get_logger("noor.lookup")


async def lookup_api(phone: str) -> Dict[str, Any]:
    """
    Calls:  {BEST_CLINIC_API_BASE}/api-ai-get-customer-details
    Query:  identifier_type=PHONE, identifier_value=<05XXXXXXXX>, includes_data=details
    Returns normalized shape:
      {"details": {...}, "appointments": {"data": []}}

    Raises httpx.HTTPError, ValueError or LookupError on failure.
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
    except httpx.HTTPStatusError as e:
        logger.error(
            f"lookup_api HTTP {e.response.status_code} for {phone}",
        )
        raise
    except httpx.RequestError as e:
        logger.error(f"lookup_api request failed for {phone}: {e}")
        raise

    try:
        payload = r.json()
    except ValueError as e:
        logger.error(f"lookup_api invalid JSON for {phone}: {e}")
        raise

    # Expect: {"status": true, "data": {"details": {...}}}
    if not (isinstance(payload, dict) and payload.get("status") is True):
        status_val = payload.get("status")
        logger.error(f"lookup_api failed for {phone}: status={status_val}")
        raise LookupError(f"lookup_api error status for {phone}: {status_val}")

    data = payload.get("data") or {}
    details = data.get("details") or {}
    if not isinstance(details, dict):
        logger.error(f"lookup_api details missing for {phone}")
        raise LookupError(f"lookup_api malformed details for {phone}")

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
