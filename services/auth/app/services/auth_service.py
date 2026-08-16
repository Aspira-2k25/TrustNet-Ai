from typing import Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth.app.repositories.user_repository import UserRepository
from services.auth.app.schemas.auth_schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    TokenRefreshResponse
)
from services.auth.app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from services.auth.app.config.settings import settings
from shared.auth.verify_token import verify_token, TokenVerificationError

class AuthService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)

    async def register(self, req: UserRegisterRequest) -> TokenResponse:
        existing = await self.user_repo.get_by_email(req.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EMAIL_ALREADY_EXISTS", "message": "A user with this email already exists"}
            )
            
        hashed_pw = hash_password(req.password)
        role = req.role or "user"
        user = await self.user_repo.create(
            email=req.email,
            hashed_password=hashed_pw,
            role=role
        )
        
        access_token = create_access_token(user.id, user.email, user.role)
        refresh_token = create_refresh_token(user.id, user.email, user.role)
        
        return TokenResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def login(self, req: UserLoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCOUNT_DISABLED", "message": "Account has been deactivated"}
            )
            
        access_token = create_access_token(user.id, user.email, user.role)
        refresh_token = create_refresh_token(user.id, user.email, user.role)
        
        return TokenResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def refresh(self, req: RefreshTokenRequest) -> TokenRefreshResponse:
        try:
            payload = verify_token(
                req.refresh_token,
                secret_key=settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM,
                expected_type="refresh"
            )
        except TokenVerificationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": e.error_code, "message": e.message}
            )
            
        user_id = payload.get("sub")
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "USER_NOT_FOUND", "message": "User associated with token no longer exists or is inactive"}
            )
            
        new_access_token = create_access_token(user.id, user.email, user.role)
        return TokenRefreshResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
