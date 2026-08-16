import os
from shared.config.base_settings import BaseSettings

def test_base_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SERVICE_NAME", "test_service")

    settings = BaseSettings()
    
    assert settings.ENVIRONMENT == "test"
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.SERVICE_NAME == "test_service"
