"""ERIN Market Intelligence - Performance & Scalability Module."""

from erin.market_intel.performance.caching import (
    CacheBackend,
    CacheConfig,
    CacheEntry,
    CacheStrategy,
    LRUCache,
    LFUCache,
    TTLCache,
    MultiLevelCache,
    CacheManager,
    create_cache_manager,
    create_cache_config,
)

from erin.market_intel.performance.connection_pool import (
    PoolConfig,
    PoolStats,
    ConnectionPool,
    HTTPConnectionPool,
    DatabaseConnectionPool,
    PoolManager,
    create_pool_manager,
    create_pool_config,
)

from erin.market_intel.performance.profiling import (
    ProfileConfig,
    ProfileResult,
    Profiler,
    CPUProfiler,
    MemoryProfiler,
    AsyncProfiler,
    ProfilerManager,
    ProfilerManager,
    create_profiler,
    create_profile_config,
)

from erin.market_intel.performance.load_testing import (
    LoadTestConfig,
    LoadTestResult,
    LoadTestScenario,
    LoadTestRunner,
    LoadGenerator,
    MetricsCollector,
    create_load_test_config,
    create_load_test_runner,
)

from erin.market_intel.performance.optimization import (
    OptimizationConfig,
    OptimizationResult,
    OptimizationStrategy,
    QueryOptimizer,
    IndexAdvisor,
    ConnectionPoolOptimizer,
    CacheOptimizer,
    OptimizationEngine,
    create_optimization_engine,
    create_optimization_config,
)

from erin.market_intel.performance.scaling import (
    ScalingConfig,
    ScalingPolicy,
    ScalingMetrics,
    AutoScaler,
    LoadBalancer,
    CircuitBreaker,
    RateLimiter,
    ScalingManager,
    create_scaling_manager,
    create_scaling_config,
)

from erin.market_intel.performance.monitoring import (
    MetricConfig,
    MetricPoint,
    MetricSeries,
    MetricAggregator,
    MetricCollector,
    MetricExporter,
    MetricsServer,
    MetricsClient,
    create_metrics_server,
    create_metrics_client,
)

__all__ = [
    # Caching
    "CacheBackend",
    "CacheConfig",
    "CacheEntry",
    "CacheStrategy",
    "LRUCache",
    "LFUCache",
    "TTLCache",
    "MultiLevelCache",
    "CacheManager",
    "create_cache_manager",
    "create_cache_config",
    
    # Connection Pooling
    "PoolConfig",
    "PoolStats",
    "ConnectionPool",
    "HTTPConnectionPool",
    "DatabaseConnectionPool",
    "PoolManager",
    "create_pool_manager",
    "create_pool_config",
    
    # Profiling
    "ProfileConfig",
    "ProfileResult",
    "Profiler",
    "CPUProfiler",
    "MemoryProfiler",
    "AsyncProfiler",
    "ProfilerManager",
    "create_profiler",
    "create_profile_config",
    
    # Load Testing
    "LoadTestConfig",
    "LoadTestResult",
    "LoadTestScenario",
    "LoadTestRunner",
    "LoadGenerator",
    "MetricsCollector",
    "create_load_test_config",
    "create_load_test_runner",
    
    # Optimization
    "OptimizationConfig",
    "OptimizationResult",
    "OptimizationStrategy",
    "QueryOptimizer",
    "IndexAdvisor",
    "ConnectionPoolOptimizer",
    "CacheOptimizer",
    "OptimizationEngine",
    "create_optimization_engine",
    "create_optimization_config",
    
    # Scaling
    "ScalingConfig",
    "ScalingPolicy",
    "ScalingMetrics",
    "AutoScaler",
    "LoadBalancer",
    "CircuitBreaker",
    "RateLimiter",
    "ScalingManager",
    "create_scaling_manager",
    "create_scaling_config",
    
    # Monitoring
    "MetricConfig",
    "MetricPoint",
    "MetricSeries",
    "MetricAggregator",
    "MetricCollector",
    "MetricExporter",
    "MetricsServer",
    "MetricsClient",
    "create_metrics_server",
    "create_metrics_client",
]