from pydantic import Field
from shared.config.base_settings import BaseSettings

class AuthSettings(BaseSettings):
    SERVICE_NAME: str = Field(default="auth_service")
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./auth_dev.db",
        description="Database connection URL (PostgreSQL async or SQLite for local dev/testing)"
    )
    JWT_SECRET_KEY: str = Field(
        default="trustnet_super_secret_jwt_key_for_development_purposes_only",
        description="Secret key for signing JWTs"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token lifespan in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token lifespan in days"
    )

settings = AuthSettings()
