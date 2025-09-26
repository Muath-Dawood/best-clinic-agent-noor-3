"""
Application settings and configuration.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Noor AI Agent"
    app_version: str = "4.0.0"
    debug: bool = Field(default=False, env="DEBUG")

    # Database
    state_db_path: str = Field(default="state.db", env="STATE_DB_PATH")
    sessions_db_path: str = Field(default="noor_sessions.db", env="SESSIONS_DB_PATH")

    # External APIs
    best_clinic_api_base: str = Field(
        default="https://www.bestclinic24.net",
        env="BEST_CLINIC_API_BASE"
    )
    best_clinic_api_token: Optional[str] = Field(default=None, env="BEST_CLINIC_API_TOKEN")
    patient_lookup_timeout: float = Field(default=10.0, env="PATIENT_LOOKUP_TIMEOUT")

    # WhatsApp API
    wa_green_id_instance: Optional[str] = Field(default=None, env="WA_GREEN_ID_INSTANCE")
    wa_green_api_token: Optional[str] = Field(default=None, env="WA_GREEN_API_TOKEN")
    wa_verify_secret: Optional[str] = Field(default=None, env="WA_VERIFY_SECRET")
    wa_max_message_length: int = Field(default=4096, env="WA_MAX_MESSAGE_LENGTH")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    vector_store_id_kb: Optional[str] = Field(default=None, env="VECTOR_STORE_ID_KB")
    vector_store_id_summaries: Optional[str] = Field(default=None, env="VECTOR_STORE_ID_SUMMARIES")

    # Session Management
    idle_seconds: int = Field(default=1000, env="IDLE_SECONDS")
    prefetch_summary_count: int = Field(default=3, env="PREFETCH_SUMMARY_COUNT")
    max_prefetch_chars: int = Field(default=8000, env="MAX_PREFETCH_CHARS")

    # Timezone
    timezone: str = Field(default="Asia/Hebron", env="TIMEZONE")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
