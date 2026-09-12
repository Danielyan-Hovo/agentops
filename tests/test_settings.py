from src.settings import Settings


def test_settings_default_to_safe_content_capture():
    settings = Settings()
    assert settings.environment == "development"
    assert settings.capture_content is False
    assert settings.max_batch_size == 1000


def test_settings_read_agentops_environment(monkeypatch):
    monkeypatch.setenv("AGENTOPS_ENVIRONMENT", "test")
    monkeypatch.setenv("AGENTOPS_MAX_BATCH_SIZE", "25")
    settings = Settings()
    assert settings.environment == "test"
    assert settings.max_batch_size == 25
