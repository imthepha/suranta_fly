from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from dotenv import load_dotenv
from functools import lru_cache
import json

load_dotenv()

class Settings(BaseSettings):
    # PostgreSQL Database Configuration
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    DATABASE_URL: str
    SQL_ECHO: bool = False

    # Redis Configuration
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_DB: str
    REDIS_PASSWORD: str = ""
    REDIS_URL: str
    REDIS_USE_SSL: bool = False
    REDIS_SSL_CA_CERTS: Optional[str] = None

    # JWT Security Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SSL Configuration
    SSL_ENABLED: bool = False
    SSL_CERT_PATH: Optional[str] = None
    SSL_CERT_STORE: Optional[str] = None
    SSL_CA_CERTS: Optional[str] = None
    SSL_CERT_FILE: Optional[str] = None
    SSL_KEY_FILE: Optional[str] = None

    # Gmail SMTP Settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False

    # Application Settings
    APP_NAME: str
    APP_VERSION: str
    APP_ENV: str
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API Settings
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str
    BACKEND_CORS_ORIGINS: List[str]

    # Monitoring Settings
    MONITORING_INTERVAL_MINUTES: int = 5
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 60
    LOCK_TIMEOUT_SECONDS: int = 300

    # Alibaba.ir API (Placeholder)
    ALIBABA_API_BASE_URL: str = os.getenv("ALIBABA_API_BASE_URL", "https://api.alibaba.ir/v1")
    ALIBABA_API_KEY: str = os.getenv("ALIBABA_API_KEY", "")
    
    # Notification Settings
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    
    # Monitoring Settings
    DEFAULT_MONITORING_INTERVAL: int = 300  # 5 minutes
    MAX_CONCURRENT_MONITORS: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == "BACKEND_CORS_ORIGINS":
                return json.loads(raw_val)
            return raw_val

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 