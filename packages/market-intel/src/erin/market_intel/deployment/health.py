"""Health Checks - Health checks, readiness, and liveness probes."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, TYPE_CHECKING
import asyncio
import psutil
import socket

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    component: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
        }


@dataclass
class HealthCheck:
    name: str
    check_fn: Callable[[], Awaitable[bool]]
    component: str = ""
    timeout: float = 5.0
    interval: float = 30.0
    critical: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    # Runtime fields
    _last_run: Optional[datetime] = None
    _last_result: Optional[bool] = None
    _consecutive_failures: int = 0
    _consecutive_successes: int = 0


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self, name: str = "erin"):
        self.name = name
        self._checks: Dict[str, HealthCheck] = {}
        self._results: Dict[str, bool] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
        self._start_time = datetime.utcnow()
    
    def register_check(self, check: HealthCheck):
        """Register a health check."""
        self._checks[check.name] = check
    
    def register_callback(self, callback: Callable[[str, bool], None]):
        """Register a callback for health check results."""
        self._callbacks.append(callback)
    
    def add_check(
        self,
        name: str,
        check_fn: Callable[[], Awaitable[bool]],
        component: str = "",
        timeout: float = 5.0,
        interval: float = 30.0,
        critical: bool = True,
        tags: List[str] = None,
    ):
        """Add a health check."""
        check = HealthCheck(
            name=name,
            check_fn=check_fn,
            component=component,
            timeout=timeout,
            interval=interval,
            critical=critical,
            tags=tags or [],
        )
        self.register_check(check)
    
    async def run_check(self, check: HealthCheck) -> bool:
        """Run a single health check."""
        start = time.time()
        try:
            result = await asyncio.wait_for(check.check_fn(), timeout=check.timeout)
            duration_ms = (time.time() - start) * 1000
            
            check._last_run = datetime.utcnow()
            check._last_result = True
            check._consecutive_failures = 0
            check._consecutive_successes += 1
            
            return True
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            check._last_run = datetime.utcnow()
            check._last_result = False
            check._consecutive_failures += 1
            check._consecutive_successes = 0
            return False
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            check._last_run = datetime.utcnow()
            check._last_result = False
            check._consecutive_failures += 1
            check._consecutive_successes = 0
            logger.warning(f"Health check {check.name} failed: {e}")
            return False
    
    async def run_check(self, check: HealthCheck) -> bool:
        """Run a single health check."""
        start = time.time()
        try:
            result = await asyncio.wait_for(check.check_fn(), timeout=check.timeout)
            duration_ms = (time.time() - start) * 1000
            
            check._last_run = datetime.utcnow()
            check._last_result = True
            check._consecutive_failures = 0
            check._consecutive_successes += 1
            
            return True
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            check._last_run = datetime.utcnow()
            check._last_result = False
            check._consecutive_failures += 1
            check._consecutive_successes = 0
            return False
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            check._last_run = datetime.utcnow()
            check._last_result = False
            check._consecutive_failures += 1
            check._consecutive_successes = 0
            logger.warning(f"Health check {check.name} failed: {e}")
            return False
    
    async def run_checks(self, tags: List[str] = None) -> Dict[str, bool]:
        """Run all registered health checks."""
        results = {}
        
        checks_to_run = []
        for check in self._checks.values():
            if tags is None or any(tag in check.tags for tag in tags):
                checks_to_run.append(check)
        
        # Run checks concurrently
        tasks = [self.run_check(check) for check in checks_to_run]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for check, result in zip(checks_to_run, results_list):
            if isinstance(result, Exception):
                logger.error(f"Health check {check.name} failed with exception: {result}")
                results[check.name] = False
            else:
                results[check.name] = result
                
                # Call callbacks
                for callback in self._callbacks:
                    try:
                        callback(check.name, result)
                    except Exception as e:
                        logger.error(f"Health check callback failed: {e}")
        
        return results
    
    async def run_all_checks(self) -> Dict[str, bool]:
        """Run all registered health checks."""
        return await self.run_checks()
    
    async def run_checks(self, tags: List[str] = None) -> Dict[str, bool]:
        """Run all registered health checks with optional tag filtering."""
        return await self.run_checks(tags)
    
    def get_status(self, tags: List[str] = None) -> Dict:
        """Get overall health status."""
        results = asyncio.run(self.run_checks(tags))
        
        if not self._checks:
            return {
                "status": "UNKNOWN",
                "checks": {},
                "summary": "No health checks registered"
            }
        
        # Filter by tags if provided
        results = {}
        for name, check in self._checks.items():
            if tags is None or any(tag in check.tags for tag in tags):
                results[name] = check._last_result
        
        # Calculate overall status
        critical_results = [r for name, r in results.items() 
                           if self._checks[name].critical]
        non_critical_results = [r for name, r in results.items() 
                               if not self._checks[name].critical]
        
        critical_failed = any(not r for r in critical_results)
        non_critical_failed = any(not r for r in non_critical_results)
        
        if critical_results and critical_failed:
            overall = "UNHEALTHY"
        elif non_critical_failed:
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"
        
        return {
            "status": overall,
            "checks": {
                name: {
                    "healthy": result,
                    "component": self._checks[name].component,
                    "critical": self._checks[name].critical,
                    "last_run": self._checks[name]._last_run.isoformat() if self._checks[name]._last_run else None,
                    "consecutive_failures": self._checks[name]._consecutive_failures,
                }
                for name, result in results.items()
            },
            "summary": {
                "total": len(results),
                "healthy": sum(1 for r in results.values() if r),
                "unhealthy": sum(1 for r in results.values() if not r),
                "critical_unhealthy": sum(1 for name, r in results.items() 
                                         if not r and self._checks[name].critical),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_check_details(self, name: str) -> Optional[Dict]:
        """Get detailed information about a specific check."""
        check = self._checks.get(name)
        if not check:
            return None
        
        return {
            "name": check.name,
            "component": check.component,
            "critical": check.critical,
            "timeout": check.timeout,
            "interval": check.interval,
            "tags": check.tags,
            "last_run": check._last_run.isoformat() if check._last_run else None,
            "last_result": check._last_result,
            "consecutive_failures": check._consecutive_failures,
            "consecutive_successes": check._consecutive_successes,
        }
    
    def get_all_checks(self) -> List[Dict]:
        """Get details of all registered checks."""
        return [self.get_check_details(name) for name in self._checks]


class ReadinessProbe:
    """Kubernetes-style readiness probe."""
    
    def __init__(self, health_checker: HealthChecker, required_tags: List[str] = None):
        self.health_checker = health_checker
        self.required_tags = required_tags or ["readiness"]
    
    async def check(self) -> Dict:
        """Check readiness."""
        status = await self.health_checker.get_status(self.required_tags)
        ready = status["status"] in ["HEALTHY", "DEGRADED"]
        return {
            "ready": ready,
            "status": status["status"],
            "checks": status["checks"],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_handler(self):
        """Get ASGI/HTTP handler for readiness endpoint."""
        async def handler(request):
            result = await self.check()
            status_code = 200 if result["ready"] else 503
            return {"status": status_code, "body": result}
        return handler


class LivenessProbe:
    """Kubernetes-style liveness probe."""
    
    def __init__(self, health_checker: HealthChecker, critical_only: bool = True):
        self.health_checker = health_checker
        self.critical_only = critical_only
    
    async def check(self) -> Dict:
        """Check liveness."""
        tags = ["liveness"] if not self.critical_only else None
        status = await self.health_checker.get_status(self.critical_only and ["liveness"] or None)
        alive = status["status"] != "UNHEALTHY"
        return {
            "alive": alive,
            "status": status["status"],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_handler(self):
        """Get ASGI/HTTP handler for liveness endpoint."""
        async def handler(request):
            result = await self.check()
            status_code = 200 if result["alive"] else 503
            return {"status": status_code, "body": result}
        return handler


class StartupProbe:
    """Kubernetes-style startup probe."""
    
    def __init__(self, health_checker: HealthChecker, startup_checks: List[str] = None):
        self.health_checker = health_checker
        self.startup_checks = startup_checks or ["startup"]
    
    async def check(self) -> Dict:
        """Check startup readiness."""
        status = await self.health_checker.get_status(self.startup_checks)
        started = status["status"] in ["HEALTHY", "DEGRADED"]
        return {
            "started": started,
            "status": status["status"],
            "checks": status["checks"],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_handler(self):
        async def handler(request):
            result = await self.check()
            status_code = 200 if result["started"] else 503
            return {"status": status_code, "body": result}
        return handler


def create_health_checker(name: str = "erin") -> HealthChecker:
    """Create a health checker instance."""
    return HealthChecker(name)


def create_readiness_probe(health_checker: HealthChecker) -> ReadinessProbe:
    """Create a readiness probe."""
    return ReadinessProbe(health_checker)


def create_liveness_probe(health_checker: HealthChecker) -> LivenessProbe:
    """Create a liveness probe."""
    return LivenessProbe(health_checker)


def create_startup_probe(health_checker: HealthChecker) -> StartupProbe:
    """Create a startup probe."""
    return StartupProbe(health_checker)