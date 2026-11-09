"""Load Testing - Event-driven load testing with realistic scenarios."""

import asyncio
import logging
import statistics
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
import aiohttp
import random
import statistics

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LoadTestMode(str, Enum):
    CONSTANT = "CONSTANT"           # Constant RPS
    RAMP_UP = "RAMP_UP"            # Gradually increase load
    SPIKE = "SPIKE"                # Sudden spike
    STEP = "STEP"                  # Step-wise increase
    SOAK = "SOAK"                  # Long-running steady load
    SPIKE_AND_RECOVER = "SPIKE_AND_RECOVER"  # Spike then recovery


class LoadTestStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class LoadTestConfig:
    mode: LoadTestMode = LoadTestMode.CONSTANT
    target_url: str = ""
    duration_seconds: int = 60
    target_rps: float = 100.0
    max_concurrent_users: int = 100
    ramp_up_seconds: int = 10
    warmup_seconds: int = 5
    cooldown_seconds: int = 5
    timeout_seconds: float = 30.0
    headers: Dict = field(default_factory=dict)
    payload: Optional[Dict] = None
    method: str = "GET"
    success_criteria: Dict = field(default_factory=dict)
    think_time_seconds: float = 0.0
    think_time_std: float = 0.0


@dataclass
class LoadTestScenario:
    name: str
    weight: float = 1.0
    method: str = "GET"
    path: str = "/"
    headers: Dict = field(default_factory=dict)
    payload: Optional[Dict] = None
    expected_status: int = 200
    weight_percent: float = 100.0


@dataclass
class RequestMetrics:
    timestamp: datetime
    method: str
    url: str
    status_code: int
    response_time_ms: float
    response_size: int
    success: bool
    error: str = ""
    latency_percentiles: Dict[str, float] = field(default_factory=dict)


@dataclass
class LoadTestResult:
    test_id: str = field(default_factory=lambda: f"lt_{uuid.uuid4().hex[:8]}")
    config: 'LoadTestConfig' = None
    status: LoadTestStatus = LoadTestStatus.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    errors: List[str] = field(default_factory=list)
    latency_ms: Dict[str, float] = field(default_factory=dict)  # p50, p95, p99
    throughput_rps: float = 0.0
    error_rate: float = 0.0
    requests_per_second: float = 0.0
    latency_percentiles: Dict[str, float] = field(default_factory=dict)
    throughput_over_time: List[Dict] = field(default_factory=list)
    latency_over_time: List[Dict] = field(default_factory=list)
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def add_request(self, metrics: 'RequestMetrics'):
        self.total_requests += 1
        if metrics.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            self.errors_by_type[metrics.error] = self.errors_by_type.get(metrics.error, 0) + 1


@dataclass
class RequestMetrics:
    timestamp: datetime
    method: str
    url: str
    status_code: int
    response_time_ms: float
    response_size: int
    success: bool
    error: str = ""


class MetricsCollector:
    """Collects and aggregates metrics during load test."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._requests: List[RequestMetrics] = []
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._throughput_samples: List[Tuple[datetime, int]] = []
        self._latency_samples: List[Tuple[datetime, float]] = []

    def start(self):
        self._start_time = datetime.utcnow()

    def stop(self):
        self._end_time = datetime.utcnow()

    def record(self, metrics: RequestMetrics):
        self._requests.append(metrics)
        self._latency_samples.append((metrics.timestamp, metrics.response_time_ms))

        # Sample throughput every second
        now = metrics.timestamp
        if not self._throughput_samples or (now - self._throughput_samples[-1][0]).total_seconds() >= 1:
            self._throughput_samples.append((now, 1))
        else:
            self._throughput_samples[-1] = (self._throughput_samples[-1][0], self._throughput_samples[-1][1] + 1)

    def get_result(self, config: LoadTestConfig) -> LoadTestResult:
        if not self._requests:
            return LoadTestResult(
                config=config,
                status=LoadTestStatus.COMPLETED,
                started_at=self._start_time,
                completed_at=self._end_time or datetime.utcnow(),
            )

        successful = [r for r in self._requests if r.success]
        failed = [r for r in self._requests if not r.success]

        latencies = [r.response_time_ms for r in self._requests]
        latencies.sort()

        def percentile(p):
            if not latencies:
                return 0.0
            idx = int(len(latencies) * p / 100)
            return latencies[min(idx, len(latencies) - 1)]

        error_types = {}
        for r in self._requests:
            if not r.success:
                error_type = r.error.split(':')[0] if ':' in r.error else r.error
                error_types[error_type] = error_types.get(error_type, 0) + 1

        duration = (self._end_time - self._start_time).total_seconds() if self._end_time and self._start_time else 0

        return LoadTestResult(
            config=self._config,
            status=LoadTestStatus.COMPLETED,
            started_at=self._start_time,
            completed_at=self._end_time,
            duration_seconds=duration,
            total_requests=len(self._requests),
            successful_requests=len(successful),
            failed_requests=len(failed),
            errors=[r.error for r in failed],
            latency_ms={
                'p50': percentile(latencies, 50),
                'p95': percentile(latencies, 95),
                'p99': percentile(latencies, 99),
            },
            throughput_rps=len(self._requests) / duration if duration > 0 else 0,
            error_rate=len(failed) / len(self._requests) if self._requests else 0,
            requests_per_second=len(self._requests) / duration if duration > 0 else 0,
            latency_percentiles={
                'p50': percentile(latencies, 50),
                'p95': percentile(latencies, 95),
                'p99': percentile(latencies, 99),
            },
            errors_by_type=error_types,
            throughput_over_time=throughput_over_time,
            latency_over_time=latency_over_time,
            errors_by_type=error_types,
            duration_seconds=duration,
        )


class LoadGenerator:
    """Generates load according to configured pattern."""

    def __init__(self, config):
        self.config = config
        self._running = False
        self._session = None
        self._semaphore = None

    async def start(self):
        self._running = True
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=1000, limit_per_host=100)
        )
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_users)

    async def stop(self):
        self._running = False
        if self._session:
            await self._session.close()
            self._session = None

    async def _make_request(self, metrics):
        """Make a single HTTP request."""
        start = time.time()
        try:
            async with self._semaphore:
                async with self._session.request(
                    self.config.method,
                    self.config.target_url,
                    headers=self.config.headers,
                    json=self.config.payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as resp:
                    await resp.read()
                    elapsed = (time.time() - start) * 1000
                    metrics.record(RequestMetrics(
                        timestamp=datetime.utcnow(),
                        method=self.config.method,
                        url=self.config.target_url,
                        status_code=resp.status,
                        response_time_ms=elapsed,
                        response_size=len(await resp.read()),
                        success=200 <= resp.status < 400,
                        error="" if 200 <= resp.status < 400 else f"HTTP {resp.status}"
                    ))
        except asyncio.TimeoutError:
            metrics.record(RequestMetrics(
                timestamp=datetime.utcnow(),
                method=self.config.method,
                url=self.config.target_url,
                status_code=0,
                response_time_ms=self.config.timeout_seconds * 1000,
                response_size=0,
                success=False,
                error="Timeout"
            ))
        except Exception as e:
            metrics.record(RequestMetrics(
                timestamp=datetime.utcnow(),
                method=self.config.method,
                url=self.config.target_url,
                status_code=0,
                response_time_ms=(time.time() - start) * 1000,
                response_size=0,
                success=False,
                error=str(e)
            ))

    async def run(self, metrics, duration=None):
        self._running = True
        duration = duration or self.config.duration_seconds
        end_time = time.time() + duration

        # Warmup
        if self.config.warmup_seconds > 0:
            warmup_end = time.time() + self.config.warmup_seconds
            while time.time() < warmup_end and self._running:
                await self._make_request()
                await asyncio.sleep(0.1)

        # Main load
        request_interval = 1.0 / max(1, self.config.target_rps)
        next_request = time.time()

        while time.time() < end_time and self._running:
            current_rps = self.config.target_rps
            if self.config.mode == 'ramp_up':
                progress = min(1.0, (time.time() - start_time) / self.config.ramp_up_seconds)
                current_rps = self.config.target_rps * progress
                request_interval = 1.0 / max(1, current_rps)
            else:
                request_interval = 1.0 / max(1, self.config.target_rps)

            # Wait for next request time
            sleep_time = max(0, next_request - time.time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            # Fire request
            asyncio.create_task(self._make_request())

            next_request += request_interval

        # Wait for pending
        await asyncio.sleep(2)


class MetricsCollector:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._requests = []
        self._start_time = None
        self._end_time = None
        self._throughput_samples = []
        self._latency_samples = []

    def start(self):
        self._start_time = datetime.utcnow()

    def stop(self):
        self._end_time = datetime.utcnow()

    def record(self, metrics):
        self._requests.append(metrics)
        self._latency_samples.append((metrics.timestamp, metrics.response_time_ms))
        now = metrics.timestamp
        if not self._throughput_samples or (now - self._throughput_samples[-1][0]).total_seconds() >= 1:
            self._throughput_samples.append((now, 1))
        else:
            self._throughput_samples[-1] = (self._throughput_samples[-1][0], self._throughput_samples[-1][1] + 1)

    def get_result(self, config):
        if not self._requests:
            return LoadTestResult(
                config=self.config,
                status=LoadTestStatus.COMPLETED,
                started_at=self._start_time,
                completed_at=self._end_time or datetime.utcnow(),
            )

        successful = [r for r in self._requests if r.success]
        failed = [r for r in self._requests if not r.success]

        latencies = [r.response_time_ms for r in self._requests]
        latencies.sort()

        def percentile(p):
            if not latencies:
                return 0.0
            idx = int(len(latencies) * p / 100)
            return latencies[min(idx, len(latencies) - 1)]

        error_types = {}
        for r in self._requests:
            if not r.success:
                error_type = r.error.split(':')[0] if ':' in r.error else r.error
                error_types[error_type] = error_types.get(error_type, 0) + 1

        duration = (self._end_time - self._start_time).total_seconds() if self._end_time and self._start_time else 0

        return LoadTestResult(
            config=self.config,
            status=LoadTestStatus.COMPLETED,
            started_at=self._start_time,
            completed_at=self._end_time,
            duration_seconds=duration,
            total_requests=len(self._requests),
            successful_requests=len(successful),
            failed_requests=len(failed),
            errors=[r.error for r in failed],
            latency_ms={
                'p50': percentile(latencies, 50),
                'p95': percentile(latencies, 95),
                'p99': percentile(latencies, 99),
            },
            throughput_rps=len(self._requests) / duration if duration > 0 else 0,
            error_rate=len(failed) / len(self._requests) if self._requests else 0,
            requests_per_second=len(self._requests) / duration if duration > 0 else 0,
            latency_percentiles={
                'p50': percentile(latencies, 50),
                'p95': percentile(latencies, 95),
                'p99': percentile(latencies, 99),
            },
            throughput_over_time=[],
            latency_over_time=[],
            errors_by_type={},
            duration_seconds=duration,
        )


class LoadTestRunner:
    def __init__(self, config):
        self.config = config
        self.metrics = MetricsCollector()
        self.generator = LoadGenerator(config)

    async def run(self):
        self.metrics.start()
        self.generator.start()
        try:
            await self.generator.run(self.metrics, self.config.duration_seconds)
        finally:
            await self.generator.stop()
            self.metrics.stop()
        return self.metrics.get_result(self.config)


class LoadTestScenarioBuilder:
    def __init__(self):
        self._scenarios = []
        self._config = LoadTestConfig()

    def with_config(self, config):
        self._config = config
        return self

    def add_scenario(self, scenario):
        self._scenarios.append(scenario)
        return self

    def set_rps(self, rps):
        self._config.target_rps = rps
        return self

    def set_duration(self, seconds):
        self._config.duration_seconds = seconds
        return self

    def set_mode(self, mode):
        self._config.mode = mode
        return self

    def build(self):
        return LoadTestRunner(self._config)


def create_load_test_config(target_url, target_rps=100, duration_seconds=60, mode=LoadTestMode.CONSTANT, **kwargs):
    return LoadTestConfig(
        target_url=target_url,
        target_rps=target_rps,
        duration_seconds=duration_seconds,
        mode=mode,
        **kwargs
    )

def create_load_test_runner(config):
    return LoadTestRunner(config)