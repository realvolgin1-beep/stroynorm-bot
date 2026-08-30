from app.config import Settings


def test_default_openai_model_is_luna():
    settings = Settings(telegram_bot_token="test-token")

    assert settings.openai_model == "gpt-5.6-luna"
