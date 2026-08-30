from app.config import Settings


def test_default_openai_model_is_luna():
    settings = Settings(telegram_bot_token="test-token")

    assert settings.openai_model == "gpt-5.6-luna"


def test_legacy_render_model_is_migrated_to_luna():
    settings = Settings(telegram_bot_token="test-token", openai_model="gpt-4.1-mini")

    assert settings.openai_model == "gpt-5.6-luna"


def test_explicit_non_legacy_model_is_preserved():
    settings = Settings(telegram_bot_token="test-token", openai_model="custom-model")

    assert settings.openai_model == "custom-model"
