"""Application configuration, loaded from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://verdant:verdant@localhost:5432/verdant"

    webhook_secret: str = "verdant-demo-secret-2026"

    jwt_secret: str = "change-me-in-production"
    jwt_ttl_hours: int = 12
    seed_agent_username: str = "agent"
    seed_agent_password: str = "verdant123"

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    default_brand_id: str = "verdant-co"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
