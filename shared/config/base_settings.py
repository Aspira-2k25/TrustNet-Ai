from typing import List
from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict
from pydantic import Field

class BaseSettings(PydanticBaseSettings):
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    SERVICE_NAME: str = Field(default="trustnet_service")
    CORS_ALLOWED_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    )

    @property
    def cors_origins(self) -> List[str]:
        raw = self.CORS_ALLOWED_ORIGINS
        if not raw:
            return ["http://localhost:5173"]
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        # Disallow wildcard in production when credentials are used
        if self.ENVIRONMENT.lower() == "production" and "*" in origins:
            origins = [o for o in origins if o != "*"]
            if not origins:
                origins = ["https://trustnet.ai"]
        return origins

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )
