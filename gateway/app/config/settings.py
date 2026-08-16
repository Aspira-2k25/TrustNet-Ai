from pydantic import Field
from shared.config.base_settings import BaseSettings

class GatewaySettings(BaseSettings):
    SERVICE_NAME: str = Field(default="gateway_service")
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    
    AUTH_SERVICE_URL: str = Field(
        default="http://localhost:8001",
        description="URL for downstream Auth Service"
    )
    SCAN_SERVICE_URL: str = Field(
        default="http://localhost:8002",
        description="URL for downstream Scan Management Service"
    )
    TRUST_ENGINE_SERVICE_URL: str = Field(
        default="http://localhost:8004",
        description="URL for downstream Trust Engine Service"
    )
    
    JWT_SECRET_KEY: str = Field(
        default="trustnet_super_secret_jwt_key_for_development_purposes_only"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    RATE_LIMIT_PER_MINUTE: int = Field(default=120)

settings = GatewaySettings()
