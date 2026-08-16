from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.app.database.session import get_db
from services.auth.app.services.auth_service import AuthService
from services.auth.app.repositories.user_repository import UserRepository
from services.auth.app.schemas.auth_schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    TokenRefreshResponse,
    UserResponse
)
from shared.schemas.api_response import APIResponse, ResponseMeta
from shared.utils.ids import generate_request_id
from shared.auth.verify_token import verify_token, TokenVerificationError
from services.auth.app.config.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=APIResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(
    req: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    service = AuthService(db)
    result = await service.register(req)
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    req: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    service = AuthService(db)
    result = await service.login(req)
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.post("/refresh", response_model=APIResponse[TokenRefreshResponse])
async def refresh_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    service = AuthService(db)
    result = await service.refresh(req)
    return APIResponse(
        data=result,
        meta=ResponseMeta(request_id=request_id)
    )

@router.get("/me", response_model=APIResponse[UserResponse])
async def get_current_user(
    authorization: str = Header(..., description="Bearer JWT token"),
    db: AsyncSession = Depends(get_db)
):
    request_id = generate_request_id()
    try:
        payload = verify_token(
            authorization,
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            expected_type="access"
        )
    except TokenVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": e.error_code, "message": e.message}
        )
        
    user_id = payload.get("sub")
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"}
        )
        
    return APIResponse(
        data=UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        ),
        meta=ResponseMeta(request_id=request_id)
    )
