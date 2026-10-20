from pydantic import Field
from shared.config.base_settings import BaseSettings

class ScanSettings(BaseSettings):
    SERVICE_NAME: str = Field(default="scan_management_service")
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./scan_dev.db",
        description="Database connection URL"
    )
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9094",
        description="Kafka bootstrap servers connection string"
    )
    STORAGE_DIR: str = Field(
        default="./storage_uploads",
        description="Local storage directory for media uploads fallback"
    )
    KAFKA_ENABLED: bool = False
    SCAM_SERVICE_URL: str = "http://localhost:8005"
    SCAM_SERVICE_TIMEOUT_SECONDS: float = 35
    PHISHING_SERVICE_URL: str = 'http://127.0.0.1:8007'
    IMAGE_SERVICE_URL: str = "http://127.0.0.1:8003"
    IMAGE_SERVICE_TIMEOUT_SECONDS: float = 130
    MAX_IMAGE_SIZE_MB: int = Field(default=10)
    MAX_AUDIO_SIZE_MB: int = Field(default=25)
    MAX_VIDEO_SIZE_MB: int = Field(default=200)
    JWT_SECRET_KEY: str = Field(
        default="trustnet_super_secret_jwt_key_for_development_purposes_only"
    )
    JWT_ALGORITHM: str = Field(default="HS256")

settings = ScanSettings()
