from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str | None = None
    vector_store_id: str | None = None
    wa_green_id_instance: str | None = None
    wa_green_api_token: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
