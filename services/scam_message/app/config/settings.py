from pydantic import Field, SecretStr
from shared.config.base_settings import BaseSettings
class ScamSettings(BaseSettings):
    SERVICE_NAME: str = 'scam_message_service'
    SCAM_PORT: int = 8005
    SCAM_MAX_CONCURRENCY: int = Field(default=2,ge=1,le=8)
    SCAM_TIMEOUT_SECONDS: float = 20
    PHISHING_SERVICE_URL: str = 'http://127.0.0.1:8007'
    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = 'localhost:9094'
    SCAM_OPTIONAL_ANALYSIS_ENABLED: bool = False
    GROQ_API_KEY: SecretStr = SecretStr('')
    GROQ_MODEL: str = Field(default='openai/gpt-oss-20b',max_length=100)
settings=ScamSettings()
