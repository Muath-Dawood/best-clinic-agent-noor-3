"""
External API service for handling all external API calls.
"""

import asyncio
from typing import Dict, List, Optional, Any
import httpx

from ...core.exceptions import ExternalAPIError, PatientLookupError, PatientNotFoundError
from ...config import get_settings


class ExternalAPIService:
    """Service for handling external API calls."""

    def __init__(self):
        self.settings = get_settings()
        self.timeout = 10.0

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    data=data,
                    params=params,
                    headers=headers or {}
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise ExternalAPIError("Request timed out")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise PatientNotFoundError("Patient not found")
            raise ExternalAPIError(f"HTTP error {e.response.status_code}")
        except Exception as e:
            raise ExternalAPIError(f"Request failed: {str(e)}")

    async def get_available_dates(self, data: Dict, cus_sec_pm_si: str) -> Dict:
        """Get available dates from Best Clinic API."""
        url = f"{self.settings.best_clinic_api_base}/BOKGTAVBLDTS"
        data["cus_sec_pm_si"] = cus_sec_pm_si
        return await self._make_request("POST", url, data=data)

    async def get_available_times(self, data: Dict, cus_sec_pm_si: str) -> Dict:
        """Get available times from Best Clinic API."""
        url = f"{self.settings.best_clinic_api_base}/BOKGTAVBLTIMS"
        data["cus_sec_pm_si"] = cus_sec_pm_si
        return await self._make_request("POST", url, data=data)

    async def get_available_employees(self, data: Dict, cus_sec_pm_si: str) -> Dict:
        """Get available employees from Best Clinic API."""
        url = f"{self.settings.best_clinic_api_base}/BOKGTAVBLEMPLS"
        data["cus_sec_pm_si"] = cus_sec_pm_si
        return await self._make_request("POST", url, data=data)

    async def create_booking(
        self,
        endpoint: str,
        data: Dict,
        cus_sec_pm_si: str,
        extra_headers: Optional[Dict] = None
    ) -> Dict:
        """Create booking via Best Clinic API."""
        url = f"{self.settings.best_clinic_api_base}/{endpoint}"
        data["cus_sec_pm_si"] = cus_sec_pm_si
        headers = extra_headers or {}
        return await self._make_request("POST", url, data=data, headers=headers)

    async def lookup_patient(self, phone: str) -> Dict:
        """Look up patient by phone number."""
        url = f"{self.settings.best_clinic_api_base}/api-ai-get-customer-details"
        params = {
            "identifier_type": "PHONE",
            "identifier_value": phone,
            "includes_data": "details",
        }
        headers = {}
        if self.settings.best_clinic_api_token:
            headers["Authorization"] = f"Bearer {self.settings.best_clinic_api_token}"

        result = await self._make_request("GET", url, params=params, headers=headers)

        # Expect: {"status": true, "data": {"details": {...}}}
        if not (isinstance(result, dict) and result.get("status") is True):
            status_val = result.get("status")
            raise PatientLookupError(f"API error status for {phone}: {status_val}")

        data = result.get("data") or {}
        details = data.get("details") or {}
        if not isinstance(details, dict):
            raise PatientLookupError(f"API malformed details for {phone}")

        # Endpoint doesn't return appointments; keep a stable, forward-compatible shape.
        return {"details": details, "appointments": {"data": []}}

    async def send_whatsapp_message(self, chat_id: str, message: str) -> bool:
        """Send WhatsApp message via Green API."""
        if not self.settings.wa_green_id_instance or not self.settings.wa_green_api_token:
            return False

        url = (
            f"https://7105.api.greenapi.com/waInstance{self.settings.wa_green_id_instance}"
            f"/sendMessage/{self.settings.wa_green_api_token}"
        )

        data = {"chatId": chat_id, "message": message}

        try:
            await self._make_request("POST", url, data=data)
            return True
        except ExternalAPIError:
            return False
