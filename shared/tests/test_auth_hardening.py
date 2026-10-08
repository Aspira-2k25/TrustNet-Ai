import os
import pytest
from shared.auth.verify_token import verify_token, TokenVerificationError

def test_mock_auth_rejected_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_MOCK_AUTH", "false")
    
    with pytest.raises(TokenVerificationError) as exc_info:
        verify_token("mock_jwt_developer_token")
    assert exc_info.value.error_code == "MOCK_AUTH_DISABLED"

def test_mock_auth_rejected_when_allow_mock_auth_false(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOW_MOCK_AUTH", "false")
    
    with pytest.raises(TokenVerificationError) as exc_info:
        verify_token("developer_token")
    assert exc_info.value.error_code == "MOCK_AUTH_DISABLED"

def test_mock_auth_permitted_only_when_dev_and_explicitly_allowed(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOW_MOCK_AUTH", "true")
    
    payload = verify_token("mock_jwt_developer_token")
    assert payload["sub"] == "usr-researcher-1"
    assert payload["role"] == "researcher"

def test_insecure_default_secret_rejected_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET_KEY", "super_secret_placeholder_key_change_in_production_32bytes_long")
    
    with pytest.raises(TokenVerificationError) as exc_info:
        verify_token("some.jwt.token")
    assert exc_info.value.error_code == "INSECURE_SECRET_KEY"

def test_missing_secret_rejected_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    
    with pytest.raises(TokenVerificationError) as exc_info:
        verify_token("some.jwt.token")
    assert exc_info.value.error_code == "CONFIG_ERROR"
