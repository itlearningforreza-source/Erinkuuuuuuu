"""Lifecycle Management - Application lifecycle hooks and graceful shutdown."""

import asyncio
import logging
import signal
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ShutdownSignal(str, Enum):
    SIGTERM = "SIGTERM"
    SIGINT = "SIGINT"
    SIGHUP = "SIGHUP"
    SIGQUIT = "SIGQUIT"


class LifecyclePhase(str, Enum):
    STARTING = "STARTING"
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"


@dataclass
class LifecycleHook:
    name: str
    fn: Callable
    stage: str
    async_fn: bool = True
    timeout: float = 30.0
    order: int = 0
    enabled: bool = True
    metadata: Dict = field(default_factory=dict)


class LifecycleManager:
    """Manages application lifecycle with hooks and graceful shutdown."""
    
    def __init__(self, app_name: str = "erin"):
        self.app_name = app_name
        self._hooks: List[LifecycleHook] = []
        self._phase = LifecyclePhase.STARTING
        self._shutdown_event = asyncio.Event()
        self._shutdown_signal: Optional[str] = None
        self._lock = asyncio.Lock()
        self._startup_complete = asyncio.Event()
        self._shutdown_complete = asyncio.Event()
        self._signal_handlers_installed = False
        
    def add_hook(self, hook: LifecycleHook):
        """Add a lifecycle hook."""
        self._hooks.append(hook)
        # Sort by order
        self._hooks.sort(key=lambda h: h.order)
    
    def add_startup_hook(self, name: str, fn: Callable, async_fn: bool = True, 
                         timeout: float = 30.0, order: int = 0):
        """Add a startup hook."""
        self.add_hook(LifecycleHook(
            name=name,
            fn=fn,
            stage="startup",
            async_fn=async_fn,
            timeout=timeout,
            order=order,
        ))
    
    def add_shutdown_hook(self, name: str, fn: Callable, async_fn: bool = True,
                          timeout: float = 30.0, order: int = 0):
        """Add a shutdown hook."""
        self.add_hook(LifecycleHook(
            name=name,
            fn=fn,
            stage="shutdown",
            async_fn=async_fn,
            timeout=timeout,
            order=order,
        ))
    
    def add_before_shutdown_hook(self, name: str, fn: Callable, async_fn: bool = True,
                                  timeout: float = 30.0, order: int = 0):
        """Add a hook that runs before shutdown sequence."""
        self.add_hook(LifecycleHook(
            name=name,
            fn=fn,
            stage="before_shutdown",
            async_fn=async_fn,
            timeout=timeout,
            order=order,
        ))
    
    def add_after_shutdown_hook(self, name: str, fn: Callable, async_fn: bool = True,
                                  timeout: float = 30.0, order: int = 0):
        """Add a hook that runs after shutdown sequence."""
        self.add_hook(LifecycleHook(
            name=name,
            fn=fn,
            stage="after_shutdown",
            async_fn=async_fn,
            timeout=timeout,
            order=order,
        ))
    
    async def startup(self):
        """Run startup sequence."""
        self._phase = LifecyclePhase.STARTING
        
        # Run startup hooks
        startup_hooks = [h for h in self._hooks if h.stage == "startup" and h.enabled]
        for hook in sorted(self._hooks, key=lambda h: h.order):
            if hook.stage == "startup" and hook.enabled:
                try:
                    if hook.async_fn:
                        await asyncio.wait_for(hook.fn(), timeout=hook.timeout)
                    else:
                        hook.fn()
                except Exception as e:
                    logger.error(f"Startup hook {hook.name} failed: {e}")
                    raise
        
        self._phase = LifecyclePhase.STARTED
        self._startup_complete.set()
    
    async def shutdown(self, signal: str = "SIGTERM"):
        """Graceful shutdown sequence."""
        if self._phase == LifecyclePhase.SHUTTING_DOWN:
            return  # Already shutting down
        
        self._phase = LifecyclePhase.SHUTTING_DOWN
        self._shutdown_signal = signal
        
        # Run before_shutdown hooks
        await self._run_hooks("before_shutdown")
        
        # Run shutdown hooks
        await self._run_hooks("shutdown")
        
        # Run after_shutdown hooks
        await self._run_hooks("after_shutdown")
        
        self._phase = LifecyclePhase.STOPPED
        self._shutdown_complete.set()
    
    async def _run_hooks(self, stage: str):
        """Run hooks for a specific stage."""
        hooks = [h for h in self._hooks if h.stage == stage and h.enabled]
        
        for hook in sorted(self._hooks, key=lambda h: h.order):
            if hook.stage == stage and hook.enabled:
                try:
                    if hook.async_fn:
                        await asyncio.wait_for(hook.fn(), timeout=hook.timeout)
                    else:
                        hook.fn()
                except Exception as e:
                    logger.error(f"Lifecycle hook {hook.name} failed: {e}")
                    # Don't raise - continue with other hooks
    
    async def wait_for_startup(self, timeout: float = 60.0):
        """Wait for startup to complete."""
        try:
            await asyncio.wait_for(self._startup_complete.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Startup timed out")
    
    async def wait_for_shutdown(self, timeout: float = 60.0):
        """Wait for shutdown to complete."""
        try:
            await asyncio.wait_for(self._shutdown_complete.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError("Shutdown timed out")
    
    def install_signal_handlers(self):
        """Install signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return
            
        def signal_handler(signum, frame):
            signal_name = ShutdownSignal(signum).name
            logger.info(f"Received signal {signal_name}, initiating shutdown")
            asyncio.create_task(self.shutdown(ShutdownSignal(signum).name))
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        # SIGHUP is not available on Windows
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
        
        self._signal_handlers_installed = True
    
    @property
    def phase(self) -> LifecyclePhase:
        return self._phase
    
    @property
    def is_running(self) -> bool:
        return self._phase == LifecyclePhase.RUNNING
    
    @property
    def is_shutting_down(self) -> bool:
        return self._phase == LifecyclePhase.SHUTTING_DOWN
    
    def get_status(self) -> Dict:
        return {
            "phase": self._phase.value,
            "app_name": self.app_name,
            "hooks_registered": len(self._hooks),
            "startup_complete": self._startup_complete.is_set(),
            "shutdown_complete": self._shutdown_complete.is_set(),
        }


class StartupSequence:
    """Manages the startup sequence with dependencies."""
    
    def __init__(self):
        self.steps: List[Dict] = []
        self._results: Dict[str, Any] = {}
    
    def add_step(self, name: str, fn: Callable, depends_on: List[str] = None, 
                 timeout: float = 30.0, critical: bool = True):
        """Add a startup step."""
        self.steps.append({
            "name": name,
            "fn": fn,
            "depends_on": depends_on or [],
            "timeout": timeout,
            "critical": critical,
        })
    
    async def execute(self) -> Dict[str, Any]:
        """Execute startup steps in dependency order."""
        completed = set()
        remaining = list(self.steps)
        
        while remaining:
            progress = False
            for step in remaining[:]:
                if all(dep in completed for dep in step["depends_on"]):
                    try:
                        if asyncio.iscoroutinefunction(step["fn"]):
                            result = await asyncio.wait_for(step["fn"](), timeout=step["timeout"])
                        else:
                            result = step["fn"]()
                        
                        self._results[step["name"]] = result
                        completed.add(step["name"])
                        remaining.remove(step)
                        progress = True
                    except Exception as e:
                        logger.error(f"Startup step {step['name']} failed: {e}")
                        if step["critical"]:
                            raise
                        else:
                            completed.add(step["name"])
                            remaining.remove(step)
            
            if not progress:
                # Circular dependency or all remaining failed
                raise RuntimeError(f"Cannot resolve dependencies for: {[s['name'] for s in remaining]}")
        
        return self._results


class GracefulShutdown:
    """Handles graceful shutdown with timeout and force options."""
    
    def __init__(self, timeout: float = 30.0, force_after: float = 60.0):
        self.timeout = timeout
        self.force_after = force_after
        self._shutdown_started = False
        self._shutdown_complete = asyncio.Event()
        self._force_task: Optional[asyncio.Task] = None
    
    async def rebalance(self, 
                       current_weights: Dict[str, float],
                       target_weights: Dict[str, float],
                       max_turnover: float = 0.2,
                       transaction_cost_bps: float = 10.0,
                       allow_short: bool = False
    ) -> Dict[str, float]:
        """Rebalance portfolio with constraints."""
        
        config = OptimizationConfig(
            method=OptimizationMethod.MEAN_VARIANCE,
            current_weights=current_weights,
            target_weights=target_weights,
            max_turnover=max_turnover,
            transaction_cost_bps=transaction_cost_bps,
            allow_short=allow_short
        )
        
        result = self.optimize(config)
        return result.weights
    
    def get_portfolio_metrics(self, weights: Dict[str, float], 
                              returns: np.ndarray,
                              risk_free: float = 0.02) -> Dict:
        """Calculate portfolio metrics."""
        weights = np.array([weights.get(k, 0) for k in sorted(weights.keys())])
        returns_array = np.array([returns.get(k, 0) for k in sorted(returns.keys())])
        
        port_return = np.dot(weights, np.mean(returns_array, axis=1) * 252)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(np.cov(returns_array) * 252, weights)))
        
        sharpe = (port_return - 0.02) / port_vol if port_vol > 0 else 0
        
        return {
            "expected_return": float(port_return),
            "volatility": float(port_vol),
            "sharpe_ratio": float(sharpe),
            "weights": dict(zip(sorted(weights.keys()), weights)) if isinstance(weights, dict) else {}
        }