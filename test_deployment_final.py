import sys
sys.path.insert(0, 'packages/data-infra/src')
sys.path.insert(0, 'packages/market-intel/src')

from erin.market_intel.deployment import (
    DeploymentConfig, Environment, load_config, validate_config,
    HealthChecker, HealthStatus, HealthCheckResult, create_health_checker,
    LifecycleManager, ShutdownSignal, GracefulShutdown, StartupSequence, create_lifecycle_manager,
    MigrationManager, Migration, MigrationStatus, create_migration_manager, run_migrations,
    BackupConfig, BackupResult, BackupManager, RestoreResult, RestoreManager, create_backup_manager, create_restore_manager,
    LogConfig, LogLevel, LogFormat, StructuredLogger, LogAggregator, LogRotator, create_logger, setup_logging,
    ObservabilityConfig, TracingConfig, MetricsConfig, LoggingConfig, AlertingConfig, ObservabilityStack, create_observability_stack,
    ReleaseInfo, ReleaseManager, VersionInfo, BuildInfo, ReleaseNotes, create_release_manager, generate_release_notes,
)

print('All Deployment imports: OK')

config = DeploymentConfig()
print(f'Config loaded: {config.environment.value}')

errors = validate_config(config)
print(f'Validation errors: {errors}')

from erin.market_intel.deployment.health import create_health_checker
hc = create_health_checker('test')
hc.add_check('test_check', lambda: True, component='test', critical=True)
print('Health checker created')

from erin.market_intel.deployment.lifecycle import LifecycleManager
lm = LifecycleManager('test')
lm.add_startup_hook('test_hook', lambda: None)
print('Lifecycle manager created')

from erin.market_intel.deployment.backup import BackupConfig
bm = BackupConfig()
print('Backup config created')

from erin.market_intel.deployment.release import ReleaseManager, VersionInfo
rm = ReleaseManager()
v = VersionInfo(1, 0, 0)
print(f'Version: {v}')

print('ALL DEPLOYMENT MODULES WORKING!')