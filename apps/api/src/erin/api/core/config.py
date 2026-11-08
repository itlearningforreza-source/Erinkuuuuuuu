from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "ERIN API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production-min-32-chars")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database
    SQLITE_PATH: str = os.path.expanduser("~/.erin/data/erin.db")
    DUCKDB_PATH: str = os.path.expanduser("~/.erin/data/erin_analytics.duckdb")
    PARQUET_DIR: str = os.path.expanduser("~/.erin/data/parquet")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
    ]
    
    # Data Providers
    OPENBB_BASE_URL: str = os.getenv("OPENBB_BASE_URL", "http://localhost:6900")
    OPENBB_API_KEY: str = os.getenv("OPENBB_API_KEY", "")
    YFINANCE_ENABLED: bool = True
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    
    # AI/LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Vector DB
    LANCE_DB_PATH: str = os.path.expanduser("~/.erin/data/lancedb")
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = os.path.expanduser("~/.erin/logs/erin.log")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()