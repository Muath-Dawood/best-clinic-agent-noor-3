"""
External API configuration.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ExternalAPIConfig(BaseModel):
    """External API configuration settings."""

    # Best Clinic API
    best_clinic_base_url: str = "https://www.bestclinic24.net"
    best_clinic_api_token: Optional[str] = None
    best_clinic_timeout: float = 10.0

    # WhatsApp Green API
    wa_green_id: Optional[str] = None
    wa_green_token: Optional[str] = None
    wa_green_timeout: float = 10.0
    wa_max_message_length: int = 4096

    # OpenAI API
    openai_api_key: Optional[str] = None
    openai_timeout: float = 30.0
    vector_store_id: Optional[str] = None

    def get_whatsapp_url(self) -> Optional[str]:
        """Get WhatsApp API URL if configured."""
        if self.wa_green_id and self.wa_green_token:
            return f"https://7105.api.greenapi.com/waInstance{self.wa_green_id}/sendMessage/{self.wa_green_token}"
        return None

    def get_best_clinic_patient_lookup_url(self) -> str:
        """Get Best Clinic patient lookup API URL."""
        return f"{self.best_clinic_base_url}/api-ai-get-customer-details"

    def is_whatsapp_configured(self) -> bool:
        """Check if WhatsApp API is properly configured."""
        return bool(self.wa_green_id and self.wa_green_token)

    def is_best_clinic_configured(self) -> bool:
        """Check if Best Clinic API is properly configured."""
        return bool(self.best_clinic_base_url)

    def is_openai_configured(self) -> bool:
        """Check if OpenAI API is properly configured."""
        return bool(self.openai_api_key)
