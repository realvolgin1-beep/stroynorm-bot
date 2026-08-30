from app.config import Settings


def test_default_openai_model_is_luna():
    settings = Settings(telegram_bot_token="test-token")

    assert settings.openai_model == "gpt-5.6-luna"


def test_groq_is_preferred_when_both_keys_exist():
    settings = Settings(
        telegram_bot_token="test-token",
        groq_api_key="gsk-test",
        openai_api_key="sk-test",
    )

    assert settings.answer_provider == "groq"
    assert settings.answer_api_key == "gsk-test"
    assert settings.answer_model == "qwen/qwen3.8-27b"
    assert settings.answer_fallback_model == "openai/gpt-oss-120b"


def test_openai_remains_fallback_when_groq_is_not_configured():
    settings = Settings(telegram_bot_token="test-token", openai_api_key="sk-test")

    assert settings.answer_provider == "openai"
    assert settings.answer_model == "gpt-5.6-luna"


def test_local_provider_is_reported_without_external_keys():
    settings = Settings(telegram_bot_token="test-token")

    assert settings.answer_provider == "local"
    assert settings.answer_model == "local-grounded"


def test_legacy_render_model_is_migrated_to_luna():
    settings = Settings(telegram_bot_token="test-token", openai_model="gpt-4.1-mini")

    assert settings.openai_model == "gpt-5.6-luna"


def test_explicit_non_legacy_model_is_preserved():
    settings = Settings(telegram_bot_token="test-token", openai_model="custom-model")

    assert settings.openai_model == "custom-model"
