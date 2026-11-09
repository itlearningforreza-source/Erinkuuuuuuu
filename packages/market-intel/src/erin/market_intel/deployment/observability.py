"""Observability - Distributed tracing, metrics, and alerting."""

import asyncio
import hashlib
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
import threading
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TraceContext:
    """Distributed trace context."""
    
    def __init__(self, trace_id: str = None, span_id: str = None, parent_span_id: str = None):
        self.trace_id = trace_id or uuid.uuid4().hex[:16]
        self.span_id = span_id or uuid.uuid4().hex[:8]
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.tags: Dict[str, str] = {}
        self.logs: List[Dict] = []
    
    def set_tag(self, key: str, value: str):
        self.tags[key] = value
    
    def log(self, message: str, level: str = "info", **kwargs):
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        })
    
    def finish(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": (time.time() - self.start_time) * 1000,
            "tags": self.tags,
            "logs": self.logs,
        }


class TracingConfig:
    """Configuration for distributed tracing."""
    
    def __init__(
        self,
        enabled: bool = True,
        sample_rate: float = 0.1,
        service_name: str = "erin",
        exporter_endpoint: str = "http://localhost:4318/v1/traces",
        max_spans_per_trace: int = 1000,
    ):
        self.enabled = enabled
        self.sample_rate = sample_rate
        self.service_name = service_name
        self.exporter_endpoint = exporter_endpoint
        self.max_spans_per_trace = max_spans_per_trace


class Tracer:
    """Distributed tracer."""
    
    def __init__(self, config: TracingConfig = None):
        self.config = config or TracingConfig()
        self._active_spans: Dict[str, 'Span'] = {}
        self._lock = threading.Lock()
    
    @asynccontextmanager
    async def start_span(
        self,
        operation_name: str,
        parent_context: Optional[Dict] = None,
        tags: Dict[str, str] = None,
    ):
        """Start a new span."""
        if not self.config.enabled:
            yield None
            return
        
        # Check sampling
        if hash(uuid.uuid4().hex) % 100 / 100 > self.config.sample_rate:
            yield None
            return
        
        trace_id = uuid.uuid4().hex[:16]
        span_id = uuid.uuid4().hex[:8]
        parent_span_id = None
        
        if parent_context:
            trace_id = parent_context.get("trace_id")
            parent_span_id = parent_context.get("span_id")
        else:
            trace_id = uuid.uuid4().hex[:16]
            parent_span_id = None
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            tags=tags or {},
        )
        
        with self._lock:
            self._active_spans[span.span_id] = span
        
        try:
            yield span
        finally:
            span.finish()
            with self._lock:
                self._active_spans.pop(span.span_id, None)
            
            # Export if needed
            if self.config.exporter_endpoint:
                await self._export_span(span)
    
    def _export_span(self, span: 'Span'):
        """Export span to tracing backend."""
        # Would send to Jaeger, Zipkin, OTLP endpoint
        pass


class Span:
    """A single span in a trace."""
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str],
        operation_name: str,
        tags: Dict[str, str] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.logs: List[Dict] = []
        self.error: Optional[str] = None
    
    def set_tag(self, key: str, value: str):
        self.tags[key] = value
    
    def log(self, message: str, level: str = "info", **kwargs):
        self.logs.append({
            "timestamp": time.time(),
            "level": level,
            "message": message,
            **kwargs
        })
    
    def set_error(self, error: str):
        self.error = error
    
    def finish(self):
        self.end_time = time.time()
    
    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": (self.end_time - self.start_time) * 1000 if self.end_time else None,
            "tags": self.tags,
            "logs": self.logs,
            "error": self.error,
        }


class MetricsConfig:
    """Configuration for metrics collection."""
    
    def __init__(
        self,
        enabled: bool = True,
        port: int = 9090,
        path: str = "/metrics",
        pushgateway_url: str = "",
        job_name: str = "erin",
        push_interval: int = 60,
    ):
        self.enabled = enabled
        self.port = port
        self.path = path
        self.pushgateway_url = pushgateway_url
        self.job_name = job_name
        self.push_interval = push_interval


class LoggingConfig:
    """Configuration for structured logging."""
    
    def __init__(
        self,
        level: str = "INFO",
        format: str = "json",
        output: str = "stdout",
        file_path: str = "logs/erin.log",
        max_file_size_mb: int = 100,
        backup_count: int = 10,
        rotation: str = "daily",
        include_trace_id: bool = True,
    ):
        self.level = level
        self.format = format
        self.output = output
        self.file_path = file_path
        self.max_file_size_mb = max_file_size_mb
        self.backup_count = backup_count
        self.rotation = rotation
        self.include_trace_id = include_trace_id


class AlertingConfig:
    """Configuration for alerting."""
    
    def __init__(
        self,
        enabled: bool = True,
        alert_channels: List[str] = None,
        default_severity: str = "warning",
        group_by: List[str] = None,
        group_wait: int = 30,
        group_interval: int = 300,
        repeat_interval: int = 3600,
        receivers: List[Dict] = None,
    ):
        self.enabled = enabled
        self.alert_channels = alert_channels or ["slack", "email", "pagerduty"]
        self.default_severity = default_severity
        self.group_by = group_by or ["alertname", "severity"]
        self.group_wait = group_wait
        self.group_interval = group_interval
        self.repeat_interval = repeat_interval
        self.receivers = receivers or []


@dataclass
class ObservabilityConfig:
    tracing: TracingConfig = field(default_factory=TracingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)


class ObservabilityStack:
    """Complete observability stack."""
    
    def __init__(self, config: ObservabilityConfig = None):
        self.config = config or ObservabilityConfig()
        self.tracer = Tracer(self.config.tracing)
        self.metrics_collector = MetricsCollector()
        self.logger = setup_logging(self.config.logging)
        self.alert_manager = AlertManager(self.config.alerting)
    
    async def initialize(self):
        """Initialize all observability components."""
        # Start metrics collection
        if self.config.metrics.enabled:
            await self.metrics_collector.start_collection()
        
        # Start tracing if enabled
        if self.config.tracing.enabled:
            pass  # Tracer is ready to use
        
        logger.info("Observability stack initialized")
    
    async def shutdown(self):
        """Graceful shutdown."""
        await self.metrics_collector.stop_collection()
        logger.info("Observability stack shutdown complete")
    
    def get_tracer(self) -> Tracer:
        return self.tracer
    
    def get_metrics(self) -> MetricCollector:
        return self.metrics_collector
    
    def get_logger(self) -> StructuredLogger:
        return self.logger
    
    def get_alert_manager(self) -> 'AlertManager':
        return self.alert_manager


class AlertManager:
    """Manages alerting rules and notifications."""
    
    def __init__(self, config: AlertingConfig):
        self.config = config
        self._rules: Dict[str, 'AlertRule'] = {}
        self._active_alerts: Dict[str, 'Alert'] = {}
        self._notification_handlers: Dict[str, Callable] = {}
        self._lock = asyncio.Lock()
    
    def register_channel(self, name: str, handler: Callable):
        """Register a notification channel handler."""
        self._notification_handlers[name] = handler
    
    def add_rule(self, rule: 'AlertRule'):
        self._rules[rule.name] = rule
    
    def remove_rule(self, name: str):
        self._rules.pop(name, None)
    
    async def evaluate(self, metrics: Dict[str, float]):
        """Evaluate all rules against current metrics."""
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            try:
                triggered = rule.evaluate(metrics)
                if triggered:
                    await self._fire_alert(rule)
                else:
                    await self._resolve_alert(rule.name)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
    
    async def _fire_alert(self, rule: 'AlertRule'):
        alert_key = rule.name
        if alert_key in self._active_alerts:
            return  # Already firing
        
        alert = Alert(
            name=rule.name,
            severity=rule.severity,
            message=rule.message_template.format(**{"value": "current_value"}),
            labels=rule.labels,
            annotations=rule.annotations,
            started_at=datetime.utcnow(),
        )
        
        self._active_alerts[alert_key] = alert
        
        # Send notifications
        for channel in self.config.alert_channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
    
    async def _resolve_alert(self, rule_name: str):
        if rule_name in self._active_alerts:
            alert = self._active_alerts.pop(rule_name)
            alert.resolved_at = datetime.utcnow()
            # Send resolution notification
            for channel in self.config.alert_channels:
                handler = self._notification_handlers.get(channel)
                if handler:
                    try:
                        await handler(alert, resolved=True)
                    except Exception as e:
                        logger.error(f"Failed to send resolution via {channel}: {e}")


@dataclass
class AlertRule:
    name: str
    condition: str  # e.g., "cpu_usage > 80"
    severity: str = "warning"
    message_template: str = "Alert: {condition}"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    cooldown_seconds: int = 300
    last_fired: Optional[datetime] = None
    
    def evaluate(self, metrics: Dict[str, float]) -> bool:
        """Evaluate alert condition."""
        try:
            # Simple expression evaluation
            # In production, use a proper expression evaluator
            return eval(self.condition, {"__builtins__": {}}, metrics)
        except Exception:
            return False


@dataclass
class Alert:
    name: str
    severity: str
    message: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    started_at: datetime
    resolved_at: Optional[datetime] = None


def create_observability_stack(config: ObservabilityConfig = None) -> ObservabilityStack:
    return ObservabilityStack(config)


def create_tracing_config(
    enabled: bool = True,
    sample_rate: float = 0.1,
    service_name: str = "erin",
    exporter_endpoint: str = "http://localhost:4318/v1/traces",
) -> TracingConfig:
    return TracingConfig(
        enabled=enabled,
        sample_rate=sample_rate,
        service_name=service_name,
        exporter_endpoint=exporter_endpoint,
    )


def create_metrics_config(
    enabled: bool = True,
    port: int = 9090,
    path: str = "/metrics",
) -> MetricsConfig:
    return MetricsConfig(enabled=enabled, port=port, path=path)


def create_logging_config(
    level: str = "INFO",
    format: str = "json",
    file_path: str = "logs/erin.log",
) -> LoggingConfig:
    return LoggingConfig(level=level, format=format, file_path=file_path)


def create_alerting_config(
    enabled: bool = True,
    channels: List[str] = None,
) -> AlertingConfig:
    return AlertingConfig(enabled=enabled, alert_channels=channels or ["slack", "email"])