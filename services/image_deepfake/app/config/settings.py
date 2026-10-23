from pydantic import Field
from shared.config.base_settings import BaseSettings

class ImageDeepfakeSettings(BaseSettings):
    SERVICE_NAME: str = Field(default="image_deepfake_service")
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9094",
        description="Kafka bootstrap servers"
    )
    KAFKA_CONSUMER_GROUP: str = Field(
        default="trustnet_image_deepfake_group",
        description="Kafka consumer group ID"
    )
    STORAGE_DIR: str = Field(
        default="./storage_uploads",
        description="Local storage directory fallback"
    )
    MAX_IMAGE_SIZE_MB: int = 10
    JWT_SECRET_KEY: str = 'trustnet_super_secret_jwt_key_for_development_purposes_only'
    JWT_ALGORITHM: str = 'HS256'
    ENABLE_KAFKA_CONSUMER: bool = Field(default=True)

settings = ImageDeepfakeSettings()
