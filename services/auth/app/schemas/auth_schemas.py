from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    role: Optional[str] = Field(default="user", pattern=r"^(user|admin|moderator|researcher)$")

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    user_id: str
    email: str
    role: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=1800, description="Access token expiration in seconds")

class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=1800, description="Access token expiration in seconds")

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: str
