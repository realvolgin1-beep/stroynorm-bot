from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"
    public_url: str = ""
    webhook_secret: str = ""
    admin_telegram_id: int | None = None
    database_path: str = "data/stroynorm.db"
    render_external_url: str = ""

    @field_validator("openai_model", mode="before")
    @classmethod
    def migrate_legacy_openai_model(cls, value: object) -> str:
        configured = str(value or "").strip()
        if not configured or configured == "gpt-4.1-mini":
            return "gpt-5.6-luna"
        return configured

    @property
    def effective_public_url(self) -> str:
        return self.public_url or self.render_external_url

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
