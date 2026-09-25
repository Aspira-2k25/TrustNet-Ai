import pytest
from shared.config.base_settings import BaseSettings

def test_cors_origins_dev_allows_configured():
    settings = BaseSettings(
        ENVIRONMENT="dev",
        CORS_ALLOWED_ORIGINS="http://localhost:5173,http://localhost:3000"
    )
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:3000"]

def test_cors_origins_production_strips_wildcard():
    settings = BaseSettings(
        ENVIRONMENT="production",
        CORS_ALLOWED_ORIGINS="http://localhost:5173,*,https://app.trustnet.ai"
    )
    assert settings.cors_origins == ["http://localhost:5173", "https://app.trustnet.ai"]

def test_cors_origins_production_empty_fallback():
    settings = BaseSettings(
        ENVIRONMENT="production",
        CORS_ALLOWED_ORIGINS="*"
    )
    # Wildcard is stripped, fallback to trusted domain
    assert settings.cors_origins == ["https://trustnet.ai"]
