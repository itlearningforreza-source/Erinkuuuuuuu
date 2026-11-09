"""ERIN Market Intelligence - Deployment & Production Module."""

from erin.market_intel.deployment.config import (
    DeploymentConfig,
    Environment,
    DatabaseConfig,
    CacheConfig,
    SecurityConfig,
    MonitoringConfig,
    LoggingConfig,
    load_config,
    validate_config,
)

from erin.market_intel.deployment.health import (
    HealthCheck,
    HealthStatus,
    HealthCheckResult,
    HealthChecker,
    ReadinessProbe,
    LivenessProbe,
    StartupProbe,
    create_health_checker,
)

from erin.market_intel.deployment.lifecycle import (
    LifecycleManager,
    ShutdownSignal,
    GracefulShutdown,
    StartupSequence,
    LifecycleHook,
    create_lifecycle_manager,
)

from erin.market_intel.deployment.migrations import (
    Migration,
    MigrationManager,
    MigrationStatus,
    create_migration_manager,
    run_migrations,
)

from erin.market_intel.deployment.backup import (
    BackupConfig,
    BackupResult,
    BackupManager,
    RestoreResult,
    RestoreManager,
    create_backup_manager,
    create_restore_manager,
)

from erin.market_intel.deployment.logging import (
    LogConfig,
    LogLevel,
    LogFormat,
    StructuredLogger,
    LogAggregator,
    LogRotator,
    create_logger,
    setup_logging,
)

from erin.market_intel.deployment.observability import (
    ObservabilityConfig,
    TracingConfig,
    MetricsConfig,
    LoggingConfig,
    AlertingConfig,
    ObservabilityStack,
    create_observability_stack,
)

from erin.market_intel.deployment.release import (
    ReleaseInfo,
    ReleaseManager,
    VersionInfo,
    BuildInfo,
    ReleaseNotes,
    create_release_manager,
    generate_release_notes,
)

__all__ = [
    # Config
    "DeploymentConfig",
    "Environment",
    "DatabaseConfig",
    "CacheConfig",
    "SecurityConfig",
    "MonitoringConfig",
    "LoggingConfig",
    "load_config",
    "validate_config",
    
    # Health
    "HealthCheck",
    "HealthStatus",
    "HealthCheckResult",
    "HealthChecker",
    "ReadinessProbe",
    "LivenessProbe",
    "StartupProbe",
    "create_health_checker",
    
    # Lifecycle
    "LifecycleManager",
    "ShutdownSignal",
    "GracefulShutdown",
    "StartupSequence",
    "LifecycleHook",
    "create_lifecycle_manager",
    
    # Migrations
    "Migration",
    "MigrationManager",
    "MigrationStatus",
    "create_migration_manager",
    "run_migrations",
    
    # Backup
    "BackupConfig",
    "BackupResult",
    "BackupManager",
    "RestoreResult",
    "RestoreManager",
    "create_backup_manager",
    "create_restore_manager",
    
    # Logging
    "LogConfig",
    "LogLevel",
    "LogFormat",
    "StructuredLogger",
    "LogAggregator",
    "LogRotator",
    "create_logger",
    "setup_logging",
    
    # Observability
    "ObservabilityConfig",
    "TracingConfig",
    "MetricsConfig",
    "LoggingConfig",
    "AlertingConfig",
    "ObservabilityStack",
    "create_observability_stack",
    
    # Release
    "ReleaseInfo",
    "ReleaseManager",
    "VersionInfo",
    "BuildInfo",
    "ReleaseNotes",
    "create_release_manager",
    "generate_release_notes",
]