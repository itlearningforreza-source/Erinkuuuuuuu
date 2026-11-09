"""Scaling - Auto-scaling, load balancing, circuit breaking, and rate limiting."""

import asyncio
import hashlib
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
import statistics

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ScalingDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class ScalingTrigger(str, Enum):
    CPU_UTILIZATION = "CPU_UTILIZATION"
    MEMORY_UTILIZATION = "MEMORY_UTILIZATION"
    REQUEST_RATE = "REQUEST_RATE"
    LATENCY = "LATENCY"
    QUEUE_DEPTH = "QUEUE_DEPTH"
    CUSTOM_METRIC = "CUSTOM_METRIC"
    SCHEDULE = "SCHEDULE"


class ScalingAction(str, Enum):
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    NO_ACTION = "NO_ACTION"


@dataclass
class ScalingConfig:
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    target_request_rate: float = 1000.0
    target_latency_ms: float = 200.0
    scale_up_stabilization: int = 60  # seconds
    scale_down_stabilization: int = 300  # seconds
    scale_up_step: int = 1
    scale_down_step: int = 1
    cooldown_period: int = 300  # seconds
    metrics_window: int = 300  # seconds
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.3


@dataclass
class ScalingMetrics:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    request_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    queue_depth: int = 0
    active_requests: int = 0
    error_rate: float = 0.0
    replica_count: int = 0
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScalingDecision:
    action: ScalingAction
    target_replicas: int
    current_replicas: int
    reason: str
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trigger: str = ""
    metrics: Dict = field(default_factory=dict)


class ScalingPolicy:
    """Defines scaling rules and behavior."""

    def __init__(self, config: 'ScalingConfig'):
        self.config = config
        self._last_scale_up: Optional[datetime] = None
        self._last_scale_down: Optional[datetime] = None
        self._decision_history: List[Dict] = []

    def evaluate(self, metrics: ScalingMetrics, current_replicas: int) -> ScalingDecision:
        """Evaluate metrics and decide on scaling action."""
        
        # Check cooldown periods
        if self._in_cooldown():
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                target_replicas=current_replicas,
                current_replicas=current_replicas,
                reason="In cooldown period",
                confidence=1.0
            )

        # Calculate desired replicas based on metrics
        desired = self._calculate_desired_replicas(metrics, current_replicas)
        
        if desired > current_replicas:
            return self._create_scale_up_decision(current_replicas, desired, metrics)
        elif desired < current_replicas:
            return self._create_scale_down_decision(current_replicas, desired, metrics)
        else:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                target_replicas=current_replicas,
                current_replicas=current_replicas,
                reason="Within target range",
                confidence=1.0
            )

    def _calculate_desired_replicas(self, metrics: ScalingMetrics, current: int) -> int:
        """Calculate desired replica count based on metrics."""
        # CPU-based scaling
        cpu_scale = max(1, int(self.config.min_replicas * metrics.cpu_utilization / self.config.target_cpu_utilization))
        
        # Memory-based scaling
        memory_scale = max(1, int(self.config.min_replicas * metrics.memory_utilization / self.config.target_memory_utilization))
        
        # Request rate scaling
        rate_scale = max(1, int(self.config.min_replicas * metrics.request_rate / self.config.target_request_rate))
        
        # Latency-based scaling
        latency_scale = max(1, int(self.config.min_replicas * metrics.avg_latency_ms / self.config.target_latency_ms))
        
        # Take maximum of all scaling factors
        desired = max(cpu_scale, memory_scale, rate_scale, latency_scale, self.config.min_replicas)
        
        # Apply min/max bounds
        return max(self.config.min_replicas, min(self.config.max_replicas, desired))

    def _create_scale_up_decision(self, current: int, desired: int, metrics: ScalingMetrics) -> ScalingDecision:
        if self._last_scale_up and (datetime.utcnow() - self._last_scale_up).total_seconds() < self.config.cooldown_period:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                target_replicas=self.config.max_replicas,
                current_replicas=self.current_replicas,
                reason="Scale-up cooldown active",
                confidence=0.0
            )

        step = min(self.config.scale_up_step, self.config.max_replicas - current_replicas)
        target = min(current_replicas + step, self.config.max_replicas)
        
        return ScalingDecision(
            action=ScalingAction.SCALE_UP,
            target_replicas=target,
            current_replicas=current_replicas,
            reason=f"Scaling up: CPU={metrics.cpu_utilization:.1f}%, Memory={metrics.memory_utilization:.1f}%",
            confidence=0.8,
            trigger="scale_up",
            metrics={"cpu": metrics.cpu_utilization, "memory": metrics.memory_utilization}
        )

    def _create_scale_down_decision(self, current: int, desired: int, metrics: ScalingMetrics) -> ScalingDecision:
        if self._last_scale_down and (datetime.utcnow() - self._last_scale_down).total_seconds() < self.config.scale_down_stabilization:
            return ScalingDecision(
                action=ScalingAction.NO_ACTION,
                target_replicas=current_replicas,
                current_replicas=current_replicas,
                reason="Scale-down stabilization period active",
                confidence=0.0
            )

        # Only scale down if metrics are consistently low
        if metrics.cpu_utilization < self.config.scale_down_threshold * self.config.target_cpu_utilization:
            if metrics.memory_utilization < self.config.scale_down_threshold * self.config.target_memory_utilization:
                step = min(self.config.scale_down_step, current_replicas - self.config.min_replicas)
                target = max(current_replicas - step, self.config.min_replicas)
                
                return ScalingDecision(
                    action=ScalingAction.SCALE_DOWN,
                    target_replicas=target,
                    current_replicas=current_replicas,
                    reason=f"Scaling down: low utilization sustained",
                    confidence=0.7,
                    trigger="scale_down",
                    metrics={"cpu": metrics.cpu_utilization, "memory": metrics.memory_utilization}
                )

        return ScalingDecision(
            action=ScalingAction.NO_ACTION,
            target_replicas=current_replicas,
            current_replicas=current_replicas,
            reason="Not ready to scale down",
            confidence=0.0
        )

    def _in_cooldown(self) -> bool:
        now = datetime.utcnow()
        if self._last_scale_up and (datetime.utcnow() - self._last_scale_up).total_seconds() < self.config.cooldown_period:
            return True
        if self._last_scale_down and (datetime.utcnow() - self._last_scale_down).total_seconds() < self.config.cooldown_period:
            return True
        return False

    def record_decision(self, decision: ScalingDecision):
        self._decision_history.append({
            "timestamp": decision.timestamp.isoformat(),
            "action": decision.action.value,
            "from_replicas": decision.current_replicas,
            "to_replicas": decision.target_replicas,
            "reason": decision.reason,
        })

    @property
    def _last_scale_up(self):
        for d in reversed(self._decision_history):
            if d.get("action") == "SCALE_UP":
                return datetime.fromisoformat(d["timestamp"])
        return None

    @property
    def _last_scale_down(self):
        for d in reversed(self._decision_history):
            if d.get("action") == "SCALE_DOWN":
                return datetime.fromisoformat(d["timestamp"])
        return None


class LoadBalancer:
    """Load balancer with multiple algorithms."""

    class Algorithm(str, Enum):
        ROUND_ROBIN = "ROUND_ROBIN"
        LEAST_CONNECTIONS = "LEAST_CONNECTIONS"
        WEIGHTED_ROUND_ROBIN = "WEIGHTED_ROUND_ROBIN"
        LEAST_RESPONSE_TIME = "LEAST_RESPONSE_TIME"
        IP_HASH = "IP_HASH"
        LEAST_REQUESTS = "LEAST_REQUESTS"

    def __init__(self, algorithm: Algorithm = Algorithm.LEAST_CONNECTIONS):
        self.algorithm = algorithm
        self.backends: List[Dict] = []
        self._current_index = 0
        self._connection_counts: Dict[str, int] = defaultdict(int)
        self._response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._lock = asyncio.Lock()

    def add_backend(self, url: str, weight: int = 1, metadata: Dict = None):
        self.backends.append({
            "url": url,
            "weight": weight,
            "healthy": True,
            "metadata": metadata or {},
            "connections": 0,
            "total_requests": 0,
            "total_errors": 0,
            "total_latency": 0.0,
        })

    def remove_backend(self, url: str):
        self.backends = [b for b in self.backends if b["url"] != url]

    async def get_backend(self, client_ip: str = None) -> Optional[Dict]:
        async with self._lock:
            healthy = [b for b in self.backends if b["healthy"]]
            if not healthy:
                return None

            if self.algorithm == self.Algorithm.ROUND_ROBIN:
                backend = healthy[self._current_index % len(healthy)]
                self._current_index = (self._current_index + 1) % len(healthy)
                return backend

            elif self.algorithm == self.Algorithm.LEAST_CONNECTIONS:
                return min(healthy, key=lambda b: b["connections"])

            elif self.algorithm == self.Algorithm.WEIGHTED_ROUND_ROBIN:
                # Weighted selection
                total_weight = sum(b["weight"] for b in healthy)
                r = random.uniform(0, total_weight)
                cumulative = 0
                for backend in healthy:
                    cumulative += backend["weight"]
                    if r <= cumulative:
                        return backend
                return healthy[-1]

            elif self.algorithm == self.Algorithm.LEAST_RESPONSE_TIME:
                # Use average response time
                best = min(healthy, key=lambda b: 
                    b["total_latency"] / max(1, b["total_requests"]) if b["total_requests"] > 0 else float('inf'))
                return best

            elif self.algorithm == self.Algorithm.IP_HASH:
                if not client_ip:
                    return random.choice(healthy)
                hash_val = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
                return healthy[hash_val % len(healthy)]

            return random.choice(healthy)

    async def record_request(self, url: str, latency_ms: float, success: bool):
        async with self._lock:
            for backend in self.backends:
                if backend["url"] == url:
                    backend["total_requests"] += 1
                    if not success:
                        backend["total_errors"] += 1
                    backend["total_latency"] += latency
                    break

    async def mark_unhealthy(self, url: str):
        async with self._lock:
            for backend in self.backends:
                if backend["url"] == url:
                    backend["healthy"] = False
                    break

    async def mark_healthy(self, url: str):
        async with self._lock:
            for backend in self.backends:
                if backend["url"] == url:
                    backend["healthy"] = True
                    break

    def get_stats(self) -> List[Dict]:
        return [{
            "url": b["url"],
            "healthy": b["healthy"],
            "connections": b["connections"],
            "total_requests": b["total_requests"],
            "error_rate": b["total_errors"] / max(1, b["total_requests"]),
            "avg_latency": b["total_latency"] / max(1, b["total_requests"]),
        } for b in self.backends]


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    class State(str, Enum):
        CLOSED = "CLOSED"      # Normal operation
        OPEN = "OPEN"          # Failing, reject requests
        HALF_OPEN = "HALF_OPEN"  # Testing recovery

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> State:
        if self._state == self.State.OPEN:
            # Check if timeout has passed to transition to half-open
            if self._last_failure_time and \
               (datetime.utcnow() - self._last_failure_time).total_seconds() >= self.timeout:
                return self.State.HALF_OPEN
        return self._state

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == self.State.OPEN:
            raise Exception("Circuit breaker is OPEN")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        async with self._lock:
            if self._state == self.State.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._success_threshold:
                    self._state = self.State.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            else:
                self._failure_count = 0

    async def _on_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            
            if self._state == self.State.HALF_OPEN:
                self._state = self.State.OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = self.State.OPEN

    def get_state(self) -> dict:
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
        }

    def reset(self):
        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None


class RateLimiter:
    """Token bucket rate limiter with sliding window."""

    def __init__(
        self,
        rate: float,  # requests per second
        burst: int = 10,
        key_func: Callable = None,
    ):
        self.rate = rate
        self.burst = burst
        self.key_func = key_func or (lambda *args, **kwargs: "default")
        self._buckets: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str = None, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if allowed."""
        key = key or "default"
        
        async with self._lock:
            now = time.time()
            bucket = self._buckets.get(key)
            
            if bucket is None:
                bucket = {
                    "tokens": self.burst,
                    "last_update": time.time(),
                }
                self._buckets[key] = bucket
            
            # Refill tokens based on elapsed time
            elapsed = time.time() - bucket["last_update"]
            bucket["tokens"] = min(self.burst, bucket["tokens"] + elapsed * self.rate)
            bucket["last_update"] = time.time()
            
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True
            return False

    async def wait_for_token(self, key: str = None, timeout: float = 30.0) -> bool:
        """Wait until a token is available."""
        start = time.time()
        while time.time() - start < timeout:
            if await self.acquire(key):
                return True
            await asyncio.sleep(0.1)
        return False

    def get_stats(self, key: str = None) -> Dict:
        key = key or "default"
        bucket = self._buckets.get(key)
        if not bucket:
            return {"tokens": self.burst, "rate": self.rate}
        return {
            "tokens": bucket["tokens"],
            "rate": self.rate,
            "burst": self.burst,
        }


class SlidingWindowRateLimiter:
    """Sliding window rate limiter with precise control."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        key_func: Callable = None,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or (lambda *args, **kwargs: "default")
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str = None) -> Tuple[bool, Dict]:
        """Check if request is allowed. Returns (allowed, metadata)."""
        key = key or "default"
        now = time.time()
        cutoff = now - self.window_seconds

        async with self._lock:
            requests = self._requests[key]
            # Remove old requests
            while requests and requests[0] < cutoff:
                requests.popleft()

            allowed = len(requests) < self.max_requests
            if allowed:
                requests.append(time.time())

            return allowed, {
                "allowed": allowed,
                "current_requests": len(requests),
                "max_requests": self.max_requests,
                "window_seconds": self.window_seconds,
                "retry_after": (requests[0] + self.window_seconds - time.time()) if not allowed and requests else 0,
            }

    def get_usage(self, key: str = None) -> Dict:
        key = key or "default"
        now = time.time()
        cutoff = now - self.window_seconds
        requests = [r for r in self._requests[key] if r > cutoff]
        return {
            "current": len(requests),
            "max": self.max_requests,
            "remaining": max(0, self.max_requests - len(requests)),
            "reset_at": requests[0] + self.window_seconds if requests else time.time() + self.window_seconds,
        }


class TokenBucketRateLimiter:
    """Token bucket rate limiter with async support."""

    def __init__(
        self,
        rate: float,  # tokens per second
        capacity: int = 100,
        key_func: Callable = None,
    ):
        self.rate = rate
        self.capacity = capacity
        self.key_func = key_func or (lambda *args, **kwargs: "default")
        self._buckets: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str = None, tokens: int = 1) -> bool:
        key = key or "default"
        async with self._lock:
            now = time.time()
            bucket = self._buckets.get(key)
            
            if bucket is None:
                bucket = {"tokens": self.capacity, "last_update": time.time()}
                self._buckets[key] = bucket
            
            # Refill tokens
            elapsed = now - bucket["last_update"]
            bucket["tokens"] = min(self.capacity, bucket["tokens"] + elapsed * self.rate)
            bucket["last_update"] = now
            
            if bucket["tokens"] >= tokens:
                bucket["tokens"] -= tokens
                return True
            return False

    async def wait_for_tokens(self, key: str = None, tokens: int = 1, timeout: float = 30) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if await self.consume(key, tokens):
                return True
            await asyncio.sleep(0.1)
        return False


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on error rates."""

    def __init__(
        self,
        min_rate: float = 1.0,
        max_rate: float = 1000.0,
        target_error_rate: float = 0.01,
        adjustment_factor: float = 1.5,
    ):
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.current_rate = max_rate
        self.target_error_rate = target_error_rate
        self.adjustment_factor = adjustment_factor
        self._lock = asyncio.Lock()
        self._error_window = deque(maxlen=100)
        self._request_window = deque(maxlen=1000)

    async def record_request(self, success: bool):
        async with self._lock:
            self._request_window.append((time.time(), success))
            if not success:
                self._error_window.append(time.time())
            self._adjust_rate()

    def _adjust_rate(self):
        if len(self._request_window) < 10:
            return

        error_rate = len(self._error_window) / len(self._request_window)
        
        if error_rate > self.target_error_rate * 2:
            # Reduce rate aggressively
            self.current_rate = max(self.min_rate, self.current_rate / 2)
        elif error_rate > self.target_error_rate:
            # Reduce rate gradually
            self.current_rate = max(self.min_rate, self.current_rate * 0.8)
        elif error_rate < self.target_error_rate / 2:
            # Increase rate gradually
            self.current_rate = min(self.max_rate, self.current_rate * 1.1)

    def get_current_rate(self) -> float:
        return self.current_rate

    def get_stats(self) -> Dict:
        return {
            "current_rate": self.current_rate,
            "min_rate": self.min_rate,
            "max_rate": self.max_rate,
            "error_rate": len(self._error_window) / max(1, len(self._request_window)),
            "target_error_rate": self.target_error_rate,
        }


class ScalingManager:
    """Manages auto-scaling across multiple services."""

    def __init__(self, config: ScalingConfig = None):
        self.config = config or ScalingConfig()
        self.policies: Dict[str, ScalingPolicy] = {}
        self.metrics_history: Dict[str, List[ScalingMetrics]] = defaultdict(list)
        self.decisions_history: List[ScalingDecision] = []
        self._lock = asyncio.Lock()

    def register_service(self, service_name: str, policy: ScalingPolicy = None):
        self.policies[service_name] = policy or ScalingPolicy(ScalingConfig())

    async def evaluate_all(self, metrics: Dict[str, ScalingMetrics], current_replicas: Dict[str, int]) -> Dict[str, ScalingDecision]:
        decisions = {}
        for service, policy in self.policies.items():
            if service in metrics:
                decision = policy.evaluate(metrics[service], current_replicas.get(service, 1))
                decisions[service] = decision
        return decisions

    async def execute_scaling(self, decisions: Dict[str, ScalingDecision]) -> Dict[str, bool]:
        """Execute scaling decisions (would integrate with Kubernetes, AWS, etc.)."""
        results = {}
        for service, decision in decisions.items():
            if decision.action != ScalingAction.NO_ACTION:
                # In production, would call Kubernetes API, AWS API, etc.
                success = await self._execute_scaling(service, decision.target_replicas)
                results[service] = success
                if success:
                    self._record_decision(decision)
        return results

    async def _execute_scaling(self, service: str, target_replicas: int) -> bool:
        # Integrate with Kubernetes HPA, AWS ASG, etc.
        logger.info(f"Scaling {service} to {target_replicas} replicas")
        return True

    def get_scaling_history(self, service: str = None, limit: int = 100) -> List[ScalingDecision]:
        if service:
            return [d for d in self.decisions_history if d.metrics.get("service") == service][-limit:]
        return self.decisions_history[-limit:]

    def get_scaling_recommendations(self, service: str, metrics: ScalingMetrics) -> Dict:
        """Get scaling recommendations without executing."""
        if service not in self.policies:
            return {"error": "Service not registered"}
        
        policy = self.policies[service]
        decision = policy.evaluate(metrics, 1)  # Default current=1 for recommendation
        
        return {
            "current_replicas": 1,
            "recommended_replicas": decision.target_replicas,
            "action": decision.action.value,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "metrics": decision.metrics,
        }


class AutoScaler:
    """High-level auto-scaler with ML-based predictions."""

    def __init__(self, config: ScalingConfig = None):
        self.config = config or ScalingConfig()
        self.scaling_manager = ScalingManager(config)
        self._metrics_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._prediction_model = None

    async def collect_metrics(self, service: str, metrics: ScalingMetrics):
        """Collect and buffer metrics for a service."""
        self._metrics_buffer[service].append(metrics)

    async def predict_scaling_need(self, service: str, horizon_minutes: int = 15) -> Dict:
        """Predict future scaling needs using simple trend analysis."""
        history = self._metrics_buffer.get(service, deque())
        if len(history) < 10:
            return {"predicted_action": "NO_ACTION", "confidence": 0.0}

        # Simple linear trend prediction
        cpu_trend = self._calculate_trend([m.cpu_utilization for m in history])
        memory_trend = self._calculate_trend([m.memory_utilization for m in history])
        request_trend = self._calculate_trend([m.request_rate for m in history])

        predicted_cpu = history[-1].cpu_utilization + cpu_trend * (horizon_minutes / 5)
        predicted_memory = history[-1].memory_utilization + memory_trend * (horizon_minutes / 5)

        predicted_action = "NO_ACTION"
        if predicted_cpu > 85 or predicted_memory > 85:
            predicted_action = "SCALE_UP"
        elif predicted_cpu < 30 and predicted_memory < 30:
            predicted_action = "SCALE_DOWN"

        return {
            "predicted_action": predicted_action,
            "confidence": 0.7,
            "predicted_cpu": predicted_cpu,
            "predicted_memory": predicted_memory,
            "horizon_minutes": horizon_minutes,
        }

    def _calculate_trend(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        x = list(range(len(values)))
        y = values
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i]**2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2) if n * sum_x2 != sum_x**2 else 0
        return slope


class HealthChecker:
    """Health checking for services and dependencies."""

    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._results: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    def register_check(self, name: str, check_fn: Callable[[], Awaitable[bool]], 
                       interval: float = 30.0, timeout: float = 5.0):
        self._checks[name] = {
            "fn": check_fn,
            "interval": interval,
            "timeout": timeout,
            "last_run": None,
            "last_result": None,
        }

    async def run_checks(self) -> Dict[str, bool]:
        results = {}
        async with self._lock:
            for name, check in self._checks.items():
                try:
                    result = await asyncio.wait_for(check["fn"](), timeout=check["timeout"])
                    self._results[name] = {
                        "healthy": result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    results[name] = result
                except asyncio.TimeoutError:
                    self._results[name] = {
                        "healthy": False,
                        "error": "timeout",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    results[name] = False
                except Exception as e:
                    self._results[name] = {
                        "healthy": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    results[name] = False
                self._checks[name]["last_run"] = datetime.utcnow()
                self._checks[name]["last_result"] = results[name]
        return results

    def get_status(self) -> Dict:
        with self._lock:
            return {
                name: result.get("healthy", False)
                for name, result in self._results.items()
            }

    def is_healthy(self) -> bool:
        return all(r.get("healthy", False) for r in self._results.values())


class ServiceMesh:
    """Service mesh capabilities for microservices."""

    def __init__(self):
        self.services: Dict[str, Dict] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.load_balancers: Dict[str, LoadBalancer] = {}

    def register_service(self, name: str, config: Dict):
        self.services[name] = config
        # Create circuit breaker
        self.circuit_breakers[name] = CircuitBreaker(
            failure_threshold=config.get("failure_threshold", 5),
            success_threshold=config.get("success_threshold", 2),
            timeout=config.get("timeout", 60.0),
        )
        # Create rate limiter
        self.rate_limiters[name] = AdaptiveRateLimiter(
            min_rate=config.get("min_rate", 10),
            max_rate=config.get("max_rate", 10000),
        )
        # Create load balancer
        self.load_balancers[name] = LoadBalancer()

    async def call_service(self, service: str, func: Callable, *args, **kwargs):
        """Call a service with circuit breaker and rate limiting."""
        if service not in self.circuit_breakers:
            raise ValueError(f"Service {service} not registered")

        # Check rate limit
        limiter = self.rate_limiters[service]
        allowed, meta = await limiter.is_allowed()
        if not allowed:
            raise Exception(f"Rate limit exceeded for {service}: {meta}")

        # Execute with circuit breaker
        cb = self.circuit_breakers[service]
        return await cb.call(func)

    def get_service_health(self) -> Dict:
        return {
            name: {
                "circuit_breaker": cb.get_state(),
                "rate_limiter": rl.get_stats(),
                "load_balancer": lb.get_stats(),
            }
            for name, cb in self.circuit_breakers.items()
            for rl in [self.rate_limiters[name]]
            for lb in [self.load_balancers[name]]
        }


def create_scaling_manager(config: ScalingConfig = None) -> ScalingManager:
    return ScalingManager(config)


def create_scaling_config(
    min_replicas: int = 1,
    max_replicas: int = 10,
    target_cpu: float = 70.0,
    target_memory: float = 80.0,
    **kwargs
) -> ScalingConfig:
    return ScalingConfig(
        min_replicas=min_replicas,
        max_replicas=max_replicas,
        target_cpu_utilization=target_cpu,
        target_memory_utilization=target_memory,
        **kwargs
    )