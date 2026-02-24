from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "voice_biometric"
    SIMILARITY_THRESHOLD: float = 0.75
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_HEARTBEAT_TIMEOUT: int = 60
    WS_MAX_MESSAGE_SIZE: int = 1048576
    WS_MAX_BUFFER_SIZE: int = 10000000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
