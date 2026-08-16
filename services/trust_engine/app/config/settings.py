import os
from pydantic import Field
from shared.config.base_settings import BaseSettings

class TrustEngineSettings(BaseSettings):
    SERVICE_NAME: str = Field(default="trust_engine_service")
    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9094",
        description="Kafka bootstrap servers connection string"
    )
    KAFKA_CONSUMER_GROUP: str = Field(
        default="trustnet_trust_engine_group",
        description="Kafka consumer group ID"
    )
    MONGO_URL: str = Field(
        default="mongodb://localhost:27017/trustnet_dev",
        description="MongoDB connection string"
    )
    FUSION_WEIGHTS_FILE: str = Field(
        default=os.path.join(os.path.dirname(__file__), "fusion_weights.yaml"),
        description="Path to fusion_weights.yaml"
    )
    ENABLE_KAFKA_CONSUMER: bool = Field(default=True)

settings = TrustEngineSettings()
