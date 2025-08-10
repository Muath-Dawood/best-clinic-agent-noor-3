# src/app/patient_lookup.py
from __future__ import annotations
import os
from typing import Optional, Dict, Any
import httpx

from src.app.parse_phone_number import parse_whatsapp_to_local_palestinian_number

# --- Old tool-style API (preferred) ---
BEST_CLINIC_API_BASE = (
    os.getenv("BEST_CLINIC_API_BASE") or "https://www.bestclinic24.net"
).rstrip("/")
BEST_CLINIC_API_TOKEN = os.getenv("BEST_CLINIC_API_TOKEN") or ""
PATIENT_LOOKUP_TIMEOUT = float(os.getenv("PATIENT_LOOKUP_TIMEOUT", "10"))
BEST_CLINIC_API_PATH = "/api-ai-get-customer-details"

# --- Optional fallback (your newer style) ---
BOOKING_API_BASE_URL = (os.getenv("BOOKING_API_BASE_URL") or "").rstrip("/")
BOOKING_API_TOKEN = os.getenv("BOOKING_API_TOKEN") or ""


async def _lookup_old_api(phone: str) -> Optional[Dict[str, Any]]:
    """
    Calls https://<BEST_CLINIC_API_BASE>/api-ai-get-customer-details
    and normalizes to {"details": {...}, "appointments": {"data": []}}
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

    async with httpx.AsyncClient(timeout=PATIENT_LOOKUP_TIMEOUT) as client:
        r = await client.get(url, params=params, headers=headers or None)
        r.raise_for_status()
        payload = r.json()

    # Expect: {"status": true, "data": {"details": {...}}}
    if not (isinstance(payload, dict) and payload.get("status") is True):
        return None

    data = payload.get("data") or {}
    details = data.get("details") or {}
    if not isinstance(details, dict):
        return None

    # Old endpoint doesn't return appointments; keep a stable shape
    return {"details": details, "appointments": {"data": []}}


async def _lookup_new_api(phone: str) -> Optional[Dict[str, Any]]:
    """
    Fallback to your newer style API if BEST_CLINIC_* is not configured.
    GET <BOOKING_API_BASE_URL>/patients/by_phone?phone=05XXXXXXXX
    """
    if not BOOKING_API_BASE_URL or not BOOKING_API_TOKEN:
        return None

    url = f"{BOOKING_API_BASE_URL}/patients/by_phone"
    headers = {"Authorization": f"Bearer {BOOKING_API_TOKEN}"}

    async with httpx.AsyncClient(timeout=PATIENT_LOOKUP_TIMEOUT) as client:
        r = await client.get(url, params={"phone": phone}, headers=headers)
        r.raise_for_status()
        payload = r.json()

    data = payload.get("data") if isinstance(payload, dict) else None
    if not data:
        return None

    data.setdefault("details", {})
    data.setdefault("appointments", {"data": []})
    return data


async def fetch_patient_data_from_whatsapp_id(chat_id: str) -> Optional[Dict[str, Any]]:
    """
    Return a dict with patient 'details' and 'appointments' (normalized),
    or None if nothing found / error.
    """
    phone = parse_whatsapp_to_local_palestinian_number(chat_id)

    # Quick sanity: old API expects local Palestinian format '05XXXXXXXX'
    if not (isinstance(phone, str) and phone.startswith("05") and len(phone) == 10):
        return None

    # Prefer the old tool-compatible endpoint if configured; otherwise fallback.
    try:
        if BEST_CLINIC_API_BASE:
            result = await _lookup_old_api(phone)
            if result is not None:
                return result
    except Exception:
        # fall through to fallback
        pass

    try:
        return await _lookup_new_api(phone)
    except Exception:
        return None
