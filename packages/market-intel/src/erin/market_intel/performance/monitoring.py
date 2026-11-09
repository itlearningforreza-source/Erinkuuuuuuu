"""Monitoring - Metrics collection, aggregation, and export."""

import asyncio
import hashlib
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
import threading
import time
import json
import statistics

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    SUMMARY = "SUMMARY"


class AggregationMethod(str, Enum):
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    COUNT = "COUNT"
    RATE = "RATE"
    PERCENTILE = "PERCENTILE"


@dataclass
class MetricConfig:
    name: str
    metric_type: MetricType = MetricType.GAUGE
    description: str = ""
    unit: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    aggregation: AggregationMethod = AggregationMethod.AVG
    retention_seconds: int = 3600
    labels: List[str] = field(default_factory=list)


@dataclass
class MetricPoint:
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


@dataclass
class MetricSeries:
    config: MetricConfig
    points: List[MetricPoint] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def add_point(self, value: float, labels: Dict[str, str] = None, metadata: Dict = None):
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels or {},
            metadata=metadata or {},
        )
        self.points.append(point)
        self.last_updated = datetime.utcnow()
        self._enforce_retention()

    def _enforce_retention(self):
        cutoff = datetime.utcnow() - timedelta(seconds=self.config.retention_seconds)
        self.points = [p for p in self.points if p.timestamp > cutoff]

    def get_values(self, since: datetime = None, labels: Dict = None) -> List[float]:
        points = self.points
        if since:
            points = [p for p in points if p.timestamp >= since]
        if labels:
            points = [p for p in points if all(p.labels.get(k) == v for k, v in labels.items())]
        return [p.value for p in points]

    def get_latest(self, labels: Dict = None) -> Optional[float]:
        points = self.points
        if labels:
            points = [p for p in points if all(p.labels.get(k) == v for k, v in labels.items())]
        if points:
            return max(points, key=lambda p: p.timestamp).value
        return None

    def get_stats(self, since: datetime = None, labels: Dict = None) -> Dict:
        values = self.get_values(since, labels)
        if not values:
            return {}
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else None,
        }


class MetricAggregator:
    """Aggregates metrics over time windows."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = asyncio.Lock()

    async def add(self, name: str, value: float, labels: Dict = None, timestamp: datetime = None):
        ts = timestamp or datetime.utcnow()
        async with self._lock:
            self._buffers[name].append({
                "value": value,
                "timestamp": timestamp,
                "labels": labels or {},
            })

    async def get_aggregated(self, name: str, method: str = "avg", window_seconds: int = None) -> Optional[float]:
        window = window_seconds or self.window_seconds
        cutoff = datetime.utcnow() - timedelta(seconds=window)
        
        async with self._lock:
            buffer = self._buffers.get(name)
            if not buffer:
                return None

            values = [
                p["value"] for p in buffer
                if p["timestamp"] >= datetime.utcnow() - timedelta(seconds=window)
            ]
            
            if not values:
                return None

            if method == "avg":
                return sum(values) / len(values)
            elif method == "sum":
                return sum(values)
            elif method == "min":
                return min(values)
            elif method == "max":
                return max(values)
            elif method == "count":
                return len(values)
            elif method == "rate":
                return len(values) / (window / 60)  # per minute
            return None

    def get_all_metrics(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                name: {
                    "count": len(buf),
                    "latest": buf[-1]["value"] if buf else None,
                    "avg": sum(p["value"] for p in buf) / len(buf) if buf else None,
                }
                for name, buf in self._buffers.items()
            }


class MetricCollector:
    """Collects metrics from various sources."""

    def __init__(self):
        self._metrics: Dict[str, MetricSeries] = {}
        self._aggregator = MetricAggregator()
        self._collectors: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._collection_task: Optional[asyncio.Task] = None

    def register_metric(self, config: MetricConfig):
        with self._lock:
            if config.name in self._metrics:
                raise ValueError(f"Metric {config.name} already registered")
            self._metrics[config.name] = MetricSeries(config=config)

    def register_collector(self, name: str, collector: Callable, interval: float = 60.0):
        """Register a periodic metric collector."""
        self._collectors[name] = {
            "fn": collector,
            "interval": interval,
            "last_run": None,
        }

    async def start_collection(self, interval: float = 60.0):
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop(interval))

    async def stop_collection(self):
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

    async def _collection_loop(self, interval: float):
        while self._running:
            try:
                await self._run_collectors()
            except Exception as e:
                logger.error(f"Collection error: {e}")
            await asyncio.sleep(interval)

    async def _run_collectors(self):
        for name, collector_info in self._collectors.items():
            if collector_info["last_run"]:
                elapsed = (datetime.utcnow() - collector_info["last_run"]).total_seconds()
                if elapsed < collector_info["interval"]:
                    continue

            try:
                if asyncio.iscoroutinefunction(collector_info["fn"]):
                    await collector_info["fn"]()
                else:
                    collector_info["fn"]()
                collector_info["last_run"] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Collector {name} failed: {e}")

    def record(self, name: str, value: float, labels: Dict = None, metadata: Dict = None):
        with self._lock:
            if name in self._metrics:
                self._metrics[name].add_point(value, labels, metadata)
                self._aggregator.add(name, value, labels)

    def increment(self, name: str, value: float = 1.0, labels: Dict = None):
        with self._lock:
            if name in self._metrics:
                current = self._metrics[name].get_latest() or 0
                self._metrics[name].add_point(current + value, labels)

    def gauge(self, name: str, value: float, labels: Dict = None):
        self.record(name, value, labels)

    def histogram(self, name: str, value: float, labels: Dict = None):
        self.record(name, value, labels)

    def timing(self, name: str, duration_ms: float, labels: Dict = None):
        self.record(f"{name}.duration_ms", duration_ms, labels)

    def get_metric(self, name: str) -> Optional[MetricSeries]:
        return self._metrics.get(name)

    def get_all_metrics(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                name: series.get_stats()
                for name, series in self._metrics.items()
            }

    def get_metric_stats(self, name: str, since: datetime = None, labels: Dict = None) -> Optional[Dict]:
        if name in self._metrics:
            return self._metrics[name].get_stats(since, labels)
        return None


class MetricExporter:
    """Exports metrics to various formats and destinations."""

    def __init__(self, collector: MetricCollector):
        self.collector = collector

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        for name, series in self.collector._metrics.items():
            config = series.config
            for point in series.points:
                labels_str = ",".join(f'{k}="{v}"' for k, v in point.labels.items())
                labels_str = f"{{{labels_str}}}" if labels_str else ""
                lines.append(f"{name}{labels_str} {point.value} {int(point.timestamp.timestamp() * 1000)}")
            lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        data = {}
        for name, series in self.collector._metrics.items():
            data[name] = series.get_stats()
        return json.dumps(data, indent=2)

    async def export_to_prometheus(self, pushgateway_url: str, job_name: str = "erin"):
        """Push metrics to Prometheus Pushgateway."""
        import aiohttp
        data = self.to_prometheus()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{pushgateway_url}/metrics/job/{job_name}",
                data=data,
                headers={"Content-Type": "text/plain"}
            ) as resp:
                return resp.status == 202

    def to_datadog(self) -> List[Dict]:
        series = []
        for name, series_obj in self.collector._metrics.items():
            for point in series_obj.points[-100:]:  # Last 100 points
                series.append({
                    "metric": name,
                    "points": [[int(point.timestamp.timestamp()), point.value]],
                    "type": series_obj.config.metric_type.value.lower(),
                    "tags": [f"{k}:{v}" for k, v in point.labels.items()],
                })
        return series

    def to_cloudwatch(self, namespace: str = "ERIN") -> List[Dict]:
        metrics = []
        for name, series in self.collector._metrics.items():
            for point in series.points[-100:]:
                metrics.append({
                    "MetricName": name,
                    "Dimensions": [{"Name": k, "Value": v} for k, v in point.labels.items()],
                    "Timestamp": point.timestamp,
                    "Value": point.value,
                    "Unit": series.config.unit or "None",
                })
        return {
            "Namespace": namespace,
            "MetricData": metrics,
        }


class MetricsServer:
    """HTTP server exposing metrics endpoints."""

    def __init__(self, collector: MetricCollector, host: str = "0.0.0.0", port: int = 9090):
        self.collector = collector
        self.host = host
        self.port = port
        self._app = None
        self._server = None

    def create_app(self):
        from aiohttp import web

        app = web.Application()
        app.router.add_get("/metrics", self.metrics_handler)
        app.router.add_get("/health", self.health_handler)
        app.router.add_get("/metrics/json", self.json_metrics_handler)
        app.router.add_get("/metrics/prometheus", self.prometheus_handler)
        return app

    async def metrics_handler(self, request):
        format = request.query.get("format", "prometheus")
        if format == "json":
            exporter = MetricExporter(self.collector)
            return web.json_response(json.loads(exporter.to_json()))
        else:
            exporter = MetricExporter(self.collector)
            return web.Response(text=exporter.to_prometheus(), content_type="text/plain")

    async def json_metrics_handler(self, request):
        exporter = MetricExporter(self.collector)
        return web.json_response(json.loads(exporter.to_json()))

    async def prometheus_handler(self, request):
        exporter = MetricExporter(self.collector)
        return web.Response(text=exporter.to_prometheus(), content_type="text/plain")

    async def health_handler(self, request):
        return web.json_response({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

    async def start(self):
        self._app = self.create_app()
        runner = web.AppRunner(self._app)
        await runner.setup()
        self._server = web.TCPSite(runner, self.host, self.port)
        await self._server.start()
        logger.info(f"Metrics server started on {self.host}:{self.port}")

    async def stop(self):
        if self._server:
            await self._server.stop()


class MetricsClient:
    """Client for sending metrics to metrics server."""

    def __init__(self, server_url: str = "http://localhost:9090"):
        self.server_url = server_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def send_metric(self, name: str, value: float, labels: Dict = None, metric_type: str = "gauge"):
        session = await self._get_session()
        payload = {
            "name": name,
            "value": value,
            "labels": labels or {},
            "type": metric_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        async with aiohttp.ClientSession() as session:
            await session.post(f"{self.server_url}/api/metrics", json=payload)

    async def send_batch(self, metrics: List[Dict]):
        async with aiohttp.ClientSession() as session:
            await session.post(f"{self.server_url}/api/metrics/batch", json={"metrics": metrics})

    async def send_histogram(self, name: str, value: float, labels: Dict = None):
        await self.send_metric(name, value, labels, "histogram")

    async def increment_counter(self, name: str, value: float = 1.0, labels: Dict = None):
        await self.send_metric(name, value, labels, "counter")

    async def set_gauge(self, name: str, value: float, labels: Dict = None):
        await self.send_metric(name, value, labels, "gauge")

    async def record_timing(self, name: str, duration_ms: float, labels: Dict = None):
        await self.send_metric(f"{name}.duration_ms", duration_ms, labels, "histogram")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


# Built-in collectors
class SystemMetricsCollector:
    """Collects system-level metrics."""

    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, interval: float = 10.0):
        self._running = True
        self._task = asyncio.create_task(self._collect_loop(interval))

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _collect_loop(self, interval: float):
        while self._running:
            try:
                await self._collect_metrics()
            except Exception as e:
                logger.error(f"System metrics collection error: {e}")
            await asyncio.sleep(interval)

    async def _collect_metrics(self):
        import psutil

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.collector.gauge("system.cpu.usage_percent", cpu_percent)

        # Memory
        mem = psutil.virtual_memory()
        self.collector.gauge("system.memory.total_bytes", mem.total)
        self.collector.gauge("system.memory.available_bytes", mem.available)
        self.collector.gauge("system.memory.used_percent", mem.percent)

        # Disk
        disk = psutil.disk_usage("/")
        self.collector.gauge("system.disk.total_bytes", disk.total)
        self.collector.gauge("system.disk.used_percent", disk.percent)

        # Network
        net = psutil.net_io_counters()
        self.collector.gauge("system.network.bytes_sent", net.bytes_sent)
        self.collector.gauge("system.network.bytes_recv", net.bytes_recv)

        # Process
        process = psutil.Process()
        self.collector.gauge("process.cpu_percent", process.cpu_percent())
        self.collector.gauge("process.memory_bytes", process.memory_info().rss)
        self.collector.gauge("process.threads", process.num_threads())


class ApplicationMetricsCollector:
    """Collects application-level metrics."""

    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self._request_counts = defaultdict(int)
        self._error_counts = defaultdict(int)
        self._latencies = defaultdict(list)
        self._lock = threading.Lock()

    def record_request(self, method: str, endpoint: str, status_code: int, duration_ms: float):
        with self._lock:
            key = f"{method}:{endpoint}"
            self._request_counts[key] += 1
            if status_code >= 400:
                self._error_counts[key] += 1
            self._latencies[key].append(duration_ms)

            # Record metrics
            self.collector.increment("http.requests.total", 1, {"method": method, "endpoint": endpoint})
            if status_code >= 400:
                self.collector.increment("http.errors.total", 1, {"method": method, "endpoint": endpoint, "status": str(status_code)})
            self.collector.histogram("http.request.duration_ms", duration_ms, {"method": method, "endpoint": endpoint})

    def record_db_query(self, query_type: str, duration_ms: float, success: bool):
        self.collector.histogram("db.query.duration_ms", duration_ms, {"type": query_type, "success": str(success)})

    def record_cache_operation(self, operation: str, hit: bool, latency_ms: float):
        self.collector.increment("cache.operations.total", 1, {"operation": operation, "hit": str(hit)})
        self.collector.histogram("cache.operation.latency_ms", latency_ms, {"operation": operation})

    def record_external_call(self, service: str, duration_ms: float, success: bool):
        self.collector.histogram("external.call.duration_ms", duration_ms, {"service": service, "success": str(success)})

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "request_counts": dict(self._request_counts),
                "error_counts": dict(self._error_counts),
                "avg_latencies": {
                    k: sum(v) / len(v) if v else 0
                    for k, v in self._latencies.items()
                },
            }


# Decorators for automatic instrumentation
def timed(metric_name: str = None, collector: MetricCollector = None):
    """Decorator to time function execution."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                if collector:
                    collector.histogram(metric_name, duration, {"status": "success"})
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                if collector:
                    collector.histogram(metric_name, duration, {"status": "error", "error": type(e).__name__})
                raise
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                if collector:
                    collector.histogram(metric_name, duration, {"status": "success"})
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                if collector:
                    collector.histogram(metric_name, duration, {"status": "error", "error": type(e).__name__})
                raise
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def traced(operation_name: str, collector: MetricCollector = None):
    """Decorator to trace function execution with spans."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_id = secrets.token_hex(8)
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                if collector:
                    collector.histogram(f"{operation_name}.duration_ms", duration, {"status": "success"})
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                if collector:
                    collector.histogram(f"{operation_name}.duration_ms", duration, {"status": "error", "error": type(e).__name__})
                raise
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def instrumented(collector: MetricCollector = None):
    """Decorator to add automatic metrics to a class."""
    def decorator(cls):
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._metrics_collector = collector
            
        cls.__init__ = new_init
        
        # Wrap public methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith("_"):
                setattr(cls, name, timed(f"{cls.__name__}.{name}", collector)(method))
        
        return cls
    
    return decorator