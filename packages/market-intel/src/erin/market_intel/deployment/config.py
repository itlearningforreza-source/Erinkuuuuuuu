"""Deployment Configuration - Configuration management for ERIN deployment."""

import os
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import yaml

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "erin"
    username: str = "erin"
    password: str = ""
    pool_min: int = 5
    pool_max: int = 20
    pool_timeout: float = 30.0
    ssl_mode: str = "prefer"
    migrations_path: str = "migrations"
    backup_retention_days: int = 30
    vacuum_schedule: str = "0 3 * * *"  # Daily at 3 AM


@dataclass
class CacheConfig:
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_max_connections: int = 50
    redis_timeout: float = 5.0
    default_ttl: int = 3600
    max_memory_mb: int = 512
    eviction_policy: str = "allkeys-lru"


@dataclass
class SecurityConfig:
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    jwt_refresh_expiration_days: int = 7
    bcrypt_rounds: int = 12
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special: bool = True
    mfa_required_for_roles: List[str] = field(default_factory=lambda: ["admin", "trader"])
    session_timeout_minutes: int = 60
    max_failed_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    api_rate_limit: int = 1000
    api_rate_window_seconds: int = 60
    cors_origins: List[str] = field(default_factory=list)
    allowed_hosts: List[str] = field(default_factory=lambda: ["localhost"])
    enable_hsts: bool = True
    hsts_max_age: int = 31536000
    content_security_policy: str = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"


@dataclass
class MonitoringConfig:
    metrics_enabled: bool = True
    metrics_port: int = 9090
    metrics_path: str = "/metrics"
    health_check_interval: int = 30
    log_level: str = "INFO"
    log_format: str = "json"
    log_output: str = "stdout"
    tracing_enabled: bool = True
    tracing_sample_rate: float = 0.1
    tracing_endpoint: str = "http://localhost:4318/v1/traces"
    alerting_enabled: bool = True
    alert_webhook_url: str = ""
    alert_cooldown_minutes: int = 15


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "json"
    output: str = "stdout"
    file_path: str = "logs/erin.log"
    max_file_size_mb: int = 100
    backup_count: int = 10
    rotation: str = "daily"
    compression: bool = True
    include_timestamp: bool = True
    include_level: bool = True
    include_module: bool = True
    include_trace_id: bool = True


@dataclass
class DeploymentConfig:
    environment: Environment = Environment.DEVELOPMENT
    app_name: str = "erin"
    version: str = "1.0.0"
    build_number: str = ""
    git_commit: str = ""
    build_timestamp: str = ""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    debug: bool = False
    testing: bool = False
    workers: int = 4
    max_request_size: int = 10485760  # 10MB
    request_timeout: int = 30
    keep_alive_timeout: int = 5
    graceful_shutdown_timeout: int = 30


def load_config(config_path: Optional[str] = None, env_prefix: str = "ERIN_") -> DeploymentConfig:
    """Load configuration from file and environment variables."""
    
    # Default config
    config = DeploymentConfig()
    
    # Load from file if provided
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                file_config = yaml.safe_load(f)
            elif config_path.endswith('.json'):
                file_config = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_path}")
            
            if file_config:
                config = _merge_config(config, file_config)
    
    # Override with environment variables
    config = _apply_env_overrides(config, env_prefix)
    
    # Set derived values
    if not config.build_number:
        config.build_number = os.environ.get("BUILD_NUMBER", "local")
    if not config.git_commit:
        config.git_commit = os.environ.get("GIT_COMMIT", "unknown")
    if not config.build_timestamp:
        config.build_timestamp = datetime.utcnow().isoformat()
    
    return config


def _merge_config(base: DeploymentConfig, override: Dict) -> DeploymentConfig:
    """Merge override dict into base config."""
    # This is a simplified merge - in production would use a proper deep merge
    for key, value in override.items():
        if hasattr(base, key):
            if isinstance(value, dict) and hasattr(getattr(base, key), '__dataclass_fields__'):
                # Merge nested dataclass
                nested = getattr(base, key)
                for k, v in value.items():
                    if hasattr(nested, k):
                        setattr(nested, k, v)
            else:
                setattr(base, key, value)
    return base


def _apply_env_overrides(config: DeploymentConfig, prefix: str) -> DeploymentConfig:
    """Apply environment variable overrides."""
    env_mappings = {
        f"{prefix}ENVIRONMENT": ("environment", lambda v: Environment(v)),
        f"{prefix}DEBUG": ("debug", lambda v: v.lower() == "true"),
        f"{prefix}DATABASE_HOST": ("database.host", str),
        f"{prefix}DATABASE_PORT": ("database.port", int),
        f"{prefix}DATABASE_NAME": ("database.database", str),
        f"{prefix}DATABASE_USER": ("database.username", str),
        f"{prefix}DATABASE_PASSWORD": ("database.password", str),
        f"{prefix}REDIS_HOST": ("cache.redis_host", str),
        f"{prefix}REDIS_PORT": ("cache.redis_port", int),
        f"{prefix}REDIS_PASSWORD": ("cache.redis_password", str),
        f"{prefix}JWT_SECRET": ("security.jwt_secret_key", str),
        f"{prefix}LOG_LEVEL": ("logging.level", str),
        f"{prefix}WORKERS": ("workers", int),
    }
    
    for env_var, (attr_path, converter) in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            try:
                converted = converter(value)
                obj = config
                path_parts = attr_path.split('.')
                for part in path_parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, path_parts[-1], converter(value))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to apply env override {env_var}: {e}")
    
    return config


def validate_config(config: DeploymentConfig) -> List[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    if not config.security.jwt_secret_key:
        errors.append("JWT secret key is required")
    
    if len(config.security.jwt_secret_key) < 32:
        errors.append("JWT secret key must be at least 32 characters")
    
    if config.environment == Environment.PRODUCTION:
        if config.debug:
            errors.append("Debug mode should be disabled in production")
        
        if not config.security.cors_origins:
            errors.append("CORS origins must be configured in production")
        
        if not config.security.allowed_hosts:
            errors.append("Allowed hosts must be configured in production")
        
        if config.database.password == "":
            errors.append("Database password is required in production")
        
        if not config.security.jwt_secret_key or config.security.jwt_secret_key == "dev-secret":
            errors.append("Strong JWT secret key required in production")
    
    if config.database.pool_min > config.database.pool_max:
        errors.append("Database pool_min cannot exceed pool_max")
    
    if config.cache.redis_max_connections < config.cache.redis_max_connections:
        pass  # This would be a typo check
    
    return errors


def get_config_summary(config: DeploymentConfig) -> Dict[str, Any]:
    """Get a summary of configuration for logging (without secrets)."""
    return {
        "environment": config.environment.value,
        "version": config.version,
        "build_number": config.build_number,
        "git_commit": config.git_commit[:8] if config.git_commit else "unknown",
        "database": {
            "host": config.database.host,
            "port": config.database.port,
            "database": config.database.database,
        },
        "cache": {
            "host": config.cache.redis_host,
            "port": config.cache.redis_port,
        },
        "security": {
            "jwt_algorithm": config.security.jwt_algorithm,
            "mfa_required": bool(config.security.mfa_required_for_roles),
            "password_min_length": config.security.password_min_length,
        },
        "monitoring": {
            "metrics_enabled": config.monitoring.metrics_enabled,
            "tracing_enabled": config.monitoring.tracing_enabled,
        },
        "workers": config.workers,
    }