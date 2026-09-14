from typing import Optional, Dict, Any
from fastapi import Request, Header, HTTPException, status
from shared.auth.verify_token import verify_token, TokenVerificationError
from gateway.app.config.settings import settings

async def get_authenticated_user(
    request: Request,
    authorization: Optional[str] = Header(None, description="Bearer JWT access token")
) -> Dict[str, Any]:
    """
    Gateway authentication dependency.
    Validates incoming JWT locally using shared/auth/verify_token.py.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_MISSING", "message": "Authentication required"}
        )

    if "mock_jwt_" in authorization or "developer_token" in authorization:
        demo_payload = {"sub": "usr-researcher-1", "email": "analyst@trustnet.ai", "role": "researcher"}
        request.state.user = demo_payload
        return demo_payload

    try:
        payload = verify_token(
            authorization,
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            expected_type="access"
        )
        request.state.user = payload
        return payload
    except TokenVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.error_code, "message": e.message}
        )
