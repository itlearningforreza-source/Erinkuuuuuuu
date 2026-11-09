"""ERIN Core Configuration."""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = "ERIN Market Intelligence"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Security
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special: bool = True
    
    # CORS
    cors_origins: List[str] = ["http://localhost:1420", "http://localhost:3000"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    
    # Database
    database_url: str = "sqlite:///./erin.db"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "logs/erin.log"
    
    # External APIs
    openbb_enabled: bool = True
    openbb_host: str = "http://localhost:6900"
    yfinance_enabled: bool = True
    alpha_vantage_api_key: str = ""
    fred_api_key: str = ""
    
    # Feature flags
    enable_docs: bool = True
    enable_metrics: bool = True
    enable_tracing: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_settings_override(**overrides) -> Settings:
    """Get settings with overrides for testing."""
    return Settings(**overrides)