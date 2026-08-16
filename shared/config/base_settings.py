from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict
from pydantic import Field

class BaseSettings(PydanticBaseSettings):
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    SERVICE_NAME: str = Field(default="trustnet_service")

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8"
    )
