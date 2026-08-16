import pytest
import time
import jwt
from datetime import datetime, timezone, timedelta
from shared.auth.verify_token import verify_token, TokenVerificationError

SECRET_KEY = "test_secret_key_that_is_at_least_32_bytes_long_for_security"
ALGO = "HS256"

def create_test_token(sub="user_123", role="user", email="test@example.com", expires_in=60, token_type="access"):
    payload = {
        "sub": sub,
        "role": role,
        "email": email,
        "token_type": token_type,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGO)

def test_verify_valid_token():
    token = create_test_token()
    payload = verify_token(token, secret_key=SECRET_KEY, algorithm=ALGO)
    assert payload["sub"] == "user_123"
    assert payload["role"] == "user"
    assert payload["token_type"] == "access"

def test_verify_token_with_bearer_prefix():
    token = create_test_token()
    payload = verify_token(f"Bearer {token}", secret_key=SECRET_KEY, algorithm=ALGO)
    assert payload["sub"] == "user_123"

def test_verify_expired_token():
    token = create_test_token(expires_in=-10)
    with pytest.raises(TokenVerificationError) as exc_info:
        verify_token(token, secret_key=SECRET_KEY, algorithm=ALGO)
    assert exc_info.value.error_code == "TOKEN_EXPIRED"

def test_verify_invalid_token_type():
    token = create_test_token(token_type="refresh")
    with pytest.raises(TokenVerificationError) as exc_info:
        verify_token(token, secret_key=SECRET_KEY, algorithm=ALGO, expected_type="access")
    assert exc_info.value.error_code == "INVALID_TOKEN_TYPE"

def test_verify_invalid_signature():
    token = create_test_token()
    with pytest.raises(TokenVerificationError) as exc_info:
        verify_token(token, secret_key="wrong_key_that_is_also_at_least_32_bytes_long", algorithm=ALGO)
    assert exc_info.value.error_code == "INVALID_TOKEN"
