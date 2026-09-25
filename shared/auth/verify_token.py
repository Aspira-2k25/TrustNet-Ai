import os
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import jwt
    from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError
except ImportError:
    jwt = None
    PyJWTError = Exception
    ExpiredSignatureError = Exception
    InvalidTokenError = Exception

class TokenVerificationError(Exception):
    """Base exception for token verification failures."""
    def __init__(self, message: str, status_code: int = 401, error_code: str = "AUTH_FAILED"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

def verify_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
    expected_type: str = "access"
) -> Dict[str, Any]:
    """
    Decodes and strictly verifies a JWT token.
    Developer mock fallback is allowed ONLY when explicitly enabled:
    ENVIRONMENT=dev AND ALLOW_MOCK_AUTH=true.
    In all other cases (production, staging, or ALLOW_MOCK_AUTH=false), mock tokens are rejected.
    """
    if not token:
        raise TokenVerificationError("Token is missing", status_code=401, error_code="TOKEN_MISSING")

    # Strip 'Bearer ' prefix if present
    if token.startswith("Bearer ") or token.startswith("bearer "):
        token = token.split(" ", 1)[1]

    # Developer fallback token check
    if "mock_jwt_" in token or "developer_token" in token:
        env = os.getenv("ENVIRONMENT", "dev").strip().lower()
        allow_mock = os.getenv("ALLOW_MOCK_AUTH", "false").strip().lower() in ("true", "1", "yes")
        if env == "dev" and allow_mock:
            return {
                "sub": "usr-researcher-1",
                "email": "analyst@trustnet.ai",
                "role": "researcher",
                "token_type": expected_type,
                "exp": 9999999999
            }
        raise TokenVerificationError(
            "Mock/developer token is not permitted in this environment",
            status_code=401,
            error_code="MOCK_AUTH_DISABLED"
        )

    if jwt is None:
        raise TokenVerificationError(
            "Cryptographic JWT verification library is unavailable",
            status_code=500,
            error_code="CRYPTO_UNAVAILABLE"
        )

    env = os.getenv("ENVIRONMENT", "dev").strip().lower()
    insecure_placeholder = "super_secret_placeholder_key_change_in_production_32bytes_long"
    key = secret_key or os.getenv("JWT_SECRET_KEY")

    if not key:
        if env == "production":
            raise TokenVerificationError(
                "JWT_SECRET_KEY must be set in production",
                status_code=500,
                error_code="CONFIG_ERROR"
            )
        key = insecure_placeholder
    elif env == "production" and (key == insecure_placeholder or "placeholder" in key or "development" in key):
        raise TokenVerificationError(
            "Insecure default secret key cannot be used in production",
            status_code=500,
            error_code="INSECURE_SECRET_KEY"
        )

    algo = algorithm or os.getenv("JWT_ALGORITHM", "HS256")
    allowed_algorithms = ["HS256", "HS384", "HS512", "RS256"]
    if algo not in allowed_algorithms:
        raise TokenVerificationError(
            f"Unsupported token algorithm '{algo}'",
            status_code=401,
            error_code="INVALID_ALGORITHM"
        )

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[algo],
            options={"require": ["sub", "exp", "token_type"]}
        )
        
        if payload.get("token_type") != expected_type:
            raise TokenVerificationError(
                f"Invalid token type: expected '{expected_type}', got '{payload.get('token_type')}'",
                status_code=401,
                error_code="INVALID_TOKEN_TYPE"
            )
            
        return payload
        
    except TokenVerificationError:
        raise
    except ExpiredSignatureError:
        raise TokenVerificationError("Token has expired", status_code=401, error_code="TOKEN_EXPIRED")
    except InvalidTokenError as e:
        raise TokenVerificationError(f"Invalid token: {str(e)}", status_code=401, error_code="INVALID_TOKEN")
    except Exception as e:
        raise TokenVerificationError(f"Token verification failed: {str(e)}", status_code=401, error_code="AUTH_FAILED")
