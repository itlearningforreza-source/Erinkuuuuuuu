"""Profiling - CPU, Memory, and Async profiling for performance analysis."""

import asyncio
import cProfile
import io
import logging
import pstats
import sys
import threading
import time
import tracemalloc
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
import cProfile
import pstats
import tracemalloc
import sys
import threading

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ProfileType(str, Enum):
    CPU = "CPU"
    MEMORY = "MEMORY"
    ASYNC = "ASYNC"
    BLOCKING = "BLOCKING"
    IO = "IO"


@dataclass
class ProfileConfig:
    profile_type: ProfileType = ProfileType.CPU
    duration_seconds: float = 60.0
    interval: float = 0.001
    output_format: str = "pstats"  # pstats, json, text
    sort_by: str = "cumulative"  # cumulative, time, calls, ncalls
    limit: int = 50
    async_mode: bool = False
    include_memory: bool = False
    sample_interval: float = 0.001


@dataclass
class ProfileResult:
    profile_type: ProfileType
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    stats: Dict = field(default_factory=dict)
    top_functions: List[Dict] = field(default_factory=list)
    memory_stats: Dict = field(default_factory=dict)
    async_stats: Dict = field(default_factory=dict)
    raw_data: Any = None
    error: Optional[str] = None


class Profiler:
    """Base profiler class."""

    def __init__(self, config: ProfileConfig):
        self.config = config
        self._running = False
        self._start_time: Optional[datetime] = None
        self._profiler: Optional[cProfile.Profile] = None
        self._tracemalloc_started = False
        self._results: Optional[ProfileResult] = None

    def start(self):
        """Start profiling."""
        self._running = True
        self._start_time = datetime.utcnow()
        self._profiler = cProfile.Profile()
        self._profiler.enable()
        self._start_time = time.time()
        if self.config.include_memory:
            tracemalloc.start()
            self._tracemalloc_started = True

    def stop(self) -> ProfileResult:
        """Stop profiling and return results."""
        if not self._running:
            return ProfileResult(
                profile_type=self.config.profile_type,
                started_at=datetime.utcnow(),
                error="Profiler not running"
            )

        self._running = False
        end_time = datetime.utcnow()
        duration = (datetime.utcnow() - self._start_time).total_seconds()

        self._profiler.disable()
        self._profiler.create_stats()

        # Get profiling stats
        s = io.StringIO()
        ps = pstats.Stats(self._profiler, stream=s).sort_stats(self.config.sort_by)
        ps.print_stats(self.config.limit)

        stats_output = s.getvalue()

        # Get top functions
        ps.sort_stats(self.config.sort_by)
        top_functions = []
        for func, (cc, nc, tt, ct, callers) in ps.stats.items():
            top_functions.append({
                "function": f"{func[0]}:{func[1]}({func[2]})",
                "ncalls": nc,
                "tottime": tt,
                "cumtime": ct,
                "percall": tt / nc if nc else 0,
            })
            if len(top_functions) >= self.config.limit:
                break

        # Memory stats
        memory_stats = {}
        if self.config.include_memory and self._tracemalloc_started:
            tracemalloc.stop()
            self._tracemalloc_started = False
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            memory_stats = {
                "total_mb": sum(stat.size for stat in top_stats) / 1024 / 1024,
                "top_allocations": [
                    {
                        "file": str(stat.traceback),
                        "size_mb": stat.size / 1024 / 1024,
                        "count": stat.count,
                    }
                    for stat in top_stats[:10]
                ]

        result = ProfileResult(
            profile_type=self.config.profile_type,
            started_at=self._start_time,
            completed_at=datetime.utcnow(),
            duration_seconds=time.time() - self._start_time,
            stats={"raw": "captured"},
            top_functions=top_functions[:self.config.limit],
            memory_stats=memory_stats,
            async_stats={},
        )
        self._results = result
        return result


class CPUProfiler(Profiler):
    """CPU profiler using cProfile."""

    def __init__(self, config: ProfileConfig = None):
        config = config or ProfileConfig(profile_type=ProfileType.CPU)
        super().__init__(config)

    def profile_function(self, func: Callable, *args, **kwargs):
        """Profile a single function call."""
        self.start()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            return self.stop()


class MemoryProfiler(Profiler):
    """Memory profiler using tracemalloc."""

    def __init__(self, config: ProfileConfig = None):
        config = config or ProfileConfig(
            profile_type=ProfileType.MEMORY,
            include_memory=True,
        )
        super().__init__(config)

    def start(self):
        super().start()
        tracemalloc.start()

    def stop(self) -> ProfileResult:
        if not self._running:
            return ProfileResult(
                profile_type=ProfileType.MEMORY,
                started_at=datetime.utcnow(),
                error="Profiler not running"
            )

        self._running = False
        end_time = datetime.utcnow()

        # Get memory snapshot
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()

        top_stats = snapshot.statistics('lineno')
        top_stats_count = top_stats[:50]

        memory_stats = {
            "total_mb": sum(stat.size for stat in top_stats) / 1024 / 1024,
            "peak_mb": sum(stat.size for stat in top_stats) / 1024 / 1024,
            "top_allocations": [
                {
                    "file": str(stat.traceback),
                    "size_mb": stat.size / 1024 / 1024,
                    "count": stat.count,
                }
                for stat in top_stats_count[:20]
            ]

        result = ProfileResult(
            profile_type=ProfileType.MEMORY,
            started_at=self._start_time,
            completed_at=datetime.utcnow(),
            duration_seconds=(datetime.utcnow() - self._start_time).total_seconds(),
            stats={},
            top_functions=[],
            memory_stats=memory_stats,
        )
        return result


class AsyncProfiler(Profiler):
    """Async-aware profiler for asyncio applications."""

    def __init__(self, config: ProfileConfig = None):
        config = config or ProfileConfig(
            profile_type=ProfileType.ASYNC,
            async_mode=True,
        )
        super().__init__(config)
        self._task_stats: Dict[str, Dict] = {}

    def start(self):
        self._running = True
        self._start_time = datetime.utcnow()
        self._profiler = cProfile.Profile()
        self._profiler.enable()
        self._start_time = time.time()

        if self.config.include_memory:
            tracemalloc.start()
            self._tracemalloc_started = True

        # Hook asyncio task creation
        self._original_create_task = asyncio.create_task
        asyncio.create_task = self._wrapped_create_task

    def _wrapped_create_task(self, coro, *, name=None):
        task = self._original_create_task(coro, name=name)
        self._task_stats[id(task)] = {
            "name": name or getattr(coro, "__name__", "unknown"),
            "created_at": datetime.utcnow(),
        }
        return task

    def stop(self) -> ProfileResult:
        # Restore original
        asyncio.create_task = self._original_create_task

        # Collect task stats
        async_stats = {
            "total_tasks": len(self._task_stats),
            "task_details": [
                {
                    "name": stats["name"],
                    "duration_seconds": (datetime.utcnow() - stats["created_at"]).total_seconds(),
                }
                for stats in self._task_stats.values()
            ]

        return super().stop()


class ProfilerManager:
    """Manages multiple profilers and coordinates profiling sessions."""

    def __init__(self):
        self._profilers: Dict[str, Profiler] = {}
        self._active_sessions: Dict[str, ProfileResult] = {}
        self._lock = threading.Lock()

    def create_profiler(
        self,
        name: str,
        config: ProfileConfig = None
    ) -> Profiler:
        """Create a new profiler."""
        with self._lock:
            if name in self._profilers:
                raise ValueError(f"Profiler '{name}' already exists")

            config = config or ProfileConfig()
            profiler = Profiler(config)
            self._profilers[name] = profiler
            return profiler

    def get_profiler(self, name: str) -> Optional[Profiler]:
        with self._lock:
            return self._profilers.get(name)

    def remove_profiler(self, name: str) -> bool:
        with self._lock:
            if name in self._profilers:
                del self._profilers[name]
                return True
            return False

    async def profile_async(
        self,
        name: str,
        coro: Callable,
        config: ProfileConfig = None
    ) -> ProfileResult:
        """Profile an async coroutine."""
        profiler = self.create_profiler(name, config)
        profiler.start()

        async def wrapper():
            try:
                return await coro
            finally:
                return profiler.stop()

        return await wrapper()

    def profile_function(
        self,
        func: Callable,
        config: ProfileConfig = None
    ) -> Callable:
        """Decorator to profile a function."""
        profiler = Profiler(config or ProfileConfig())

        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler.start()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.stop()

        return wrapper

    async def profile_async_function(
        self,
        func: Callable,
        config: ProfileConfig = None
    ) -> Callable:
        """Decorator to profile an async function."""
        profiler = AsyncProfiler(config or ProfileConfig(profile_type=ProfileType.ASYNC))

        @wraps(func)
        async def wrapper(*args, **kwargs):
            profiler.start()
            try:
                return await func(*args, **kwargs)
            finally:
                profiler.stop()

        return wrapper

    def get_all_results(self) -> Dict[str, ProfileResult]:
        with self._lock:
            return {name: profiler._results for name, profiler in self._profilers.items() if profiler._results}

    def clear_results(self):
        with self._lock:
            for profiler in self._profilers.values():
                profiler._results = None


class ProfilerManager:
    """High-level profiler manager for application-wide profiling."""

    def __init__(self):
        self._manager = ProfilerManager()
        self._global_profiler: Optional[Profiler] = None

    def start_global(self, config: ProfileConfig = None):
        """Start global profiling."""
        self._global_profiler = Profiler(config or ProfileConfig())
        self._global_profiler.start()

    def stop_global(self) -> ProfileResult:
        if self._global_profiler:
            result = self._global_profiler.stop()
            self._global_profiler = None
            return result
        return None

    def get_global_results(self) -> Optional[ProfileResult]:
        if self._global_profiler:
            return self._global_profiler._results
        return None

    def profile_context(
        self,
        name: str,
        config: ProfileConfig = None
    ) -> 'ProfilingContext':
        """Context manager for profiling a code block."""
        return ProfilingContext(self, name, config)

    def get_manager(self) -> ProfilerManager:
        return self._manager


class ProfilingContext:
    """Context manager for profiling."""

    def __init__(self, manager: ProfilerManager, name: str, config: ProfileConfig = None):
        self.manager = manager
        self.name = name
        self.config = config or ProfileConfig()
        self.profiler = None
        self.result = None

    def __enter__(self):
        self.profiler = self.manager.create_profiler(self.name, self.config)
        self.profiler.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.result = self.profiler.stop()
        return False


def create_profiler(config: ProfileConfig = None) -> Profiler:
    return Profiler(config or ProfileConfig())


def create_profile_config(
    profile_type: str = "CPU",
    duration: float = 60.0,
    interval: float = 0.001,
    limit: int = 50,
    sort_by: str = "cumulative",
    **kwargs
) -> ProfileConfig:
    return ProfileConfig(
        profile_type=ProfileType(profile_type),
        duration_seconds=duration,
        interval=interval,
        limit=limit,
        sort_by=sort_by,
        **kwargs
    )


class ContinuousProfiler:
    """Continuous profiling with periodic sampling."""

    def __init__(
        self,
        interval: float = 60.0,
        duration: float = 10.0,
        config: ProfileConfig = None
    ):
        self.interval = interval
        self.duration = duration
        self.config = config or ProfileConfig()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._results: List[ProfileResult] = []
        self._lock = asyncio.Lock()

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self):
        while True:
            profiler = Profiler(ProfileConfig(
                profile_type=ProfileType.CPU,
                duration_seconds=self.duration,
                include_memory=True,
            ))
            profiler.start()
            await asyncio.sleep(self.duration)
            result = profiler.stop()

            async with self._lock:
                self._results.append(result)

            await asyncio.sleep(self.interval)

    def get_results(self) -> List[ProfileResult]:
        return self._results.copy()

    def get_summary(self) -> Dict:
        if not self._results:
            return {}

        total_duration = sum(r.duration_seconds for r in self._results)
        avg_cpu_time = sum(
            sum(f["cumtime"] for f in r.top_functions)
            for r in self._results
        ) / len(self._results) if self._results else 0

        return {
            "total_profiles": len(self._results),
            "total_duration": sum(r.duration_seconds for r in self._results),
            "average_cpu_time": avg_cpu_time,
            "total_functions_profiled": sum(len(r.top_functions) for r in self._results),
        }


def create_profiler(config: ProfileConfig = None) -> Profiler:
    return Profiler(config or ProfileConfig())


def create_profile_config(
    profile_type: str = "CPU",
    duration: float = 60.0,
    interval: float = 0.001,
    limit: int = 50,
    sort_by: str = "cumulative",
    **kwargs
) -> ProfileConfig:
    return ProfileConfig(
        profile_type=ProfileType(profile_type),
        duration_seconds=duration,
        interval=interval,
        limit=limit,
        sort_by=sort_by,
        **kwargs
    )


class BlockingDetector:
    """Detect blocking calls in async code."""

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
        self._running = False
        self._blocking_calls: List[Dict] = []
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._running = True
        # Hook into asyncio event loop
        self._original_slow_callback_duration = asyncio.get_event_loop().slow_callback_duration
        asyncio.get_event_loop().slow_callback_duration = self.threshold
        self._running = True

    async def stop(self):
        self._running = False
        if hasattr(asyncio.get_event_loop(), 'slow_callback_duration'):
            asyncio.get_event_loop().slow_callback_duration = self._original_slow_callback_duration

    def get_blocking_calls(self) -> List[Dict]:
        return self._blocking_calls.copy()

    def clear(self):
        self._blocking_calls.clear()


class IOProfiler:
    """Profile I/O operations."""

    def __init__(self):
        self._operations: List[Dict] = []
        self._lock = threading.Lock()

    def record_io(self, operation: str, path: str, size: int, duration: float):
        with self._lock:
            self._operations.append({
                "operation": operation,
                "path": path,
                "size": size,
                "duration": duration,
                "timestamp": datetime.utcnow(),
            })

    def get_stats(self) -> Dict:
        with self._lock:
            if not self._operations:
                return {}

            total_ops = len(self._operations)
            total_size = sum(op["size"] for op in self._operations)
            total_time = sum(op["duration"] for op in self._operations)

            by_op = defaultdict(int)
            for op in self._operations:
                by_op[op["operation"]] += 1

            return {
                "total_operations": total_ops,
                "total_bytes": total_size,
                "total_time_seconds": total_time,
                "by_operation": dict(by_op),
                "avg_latency_ms": (total_time / total_ops * 1000) if total_ops > 0 else 0,
            }


def create_profiler(config: ProfileConfig = None) -> Profiler:
    return Profiler(config or ProfileConfig())


def create_profile_config(
    profile_type: str = "CPU",
    duration: float = 60.0,
    interval: float = 0.001,
    limit: int = 50,
    sort_by: str = "cumulative",
    **kwargs
) -> ProfileConfig:
    return ProfileConfig(
        profile_type=ProfileType(profile_type),
        duration_seconds=duration,
        interval=interval,
        limit=limit,
        sort_by=sort_by,
        **kwargs
    )