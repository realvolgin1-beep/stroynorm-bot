from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"
    groq_fallback_model: str = "openai/gpt-oss-120b"
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

    @property
    def answer_provider(self) -> str:
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "local"

    @property
    def answer_api_key(self) -> str:
        if self.answer_provider == "groq":
            return self.groq_api_key
        if self.answer_provider == "openai":
            return self.openai_api_key
        return ""

    @property
    def answer_model(self) -> str:
        if self.answer_provider == "groq":
            return self.groq_model
        if self.answer_provider == "openai":
            return self.openai_model
        return "local-grounded"

    @property
    def answer_fallback_model(self) -> str:
        return self.groq_fallback_model if self.answer_provider == "groq" else ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
