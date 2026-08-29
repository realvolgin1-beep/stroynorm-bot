from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    public_url: str = ""
    webhook_secret: str = ""
    admin_telegram_id: int | None = None
    database_path: str = "data/stroynorm.db"
    render_external_url: str = ""

    @property
    def effective_public_url(self) -> str:
        return self.public_url or self.render_external_url

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
