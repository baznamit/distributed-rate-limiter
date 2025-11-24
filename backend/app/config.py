from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # FastAPI Configuration
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = True
    
    # Rate Limiter Configuration
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()