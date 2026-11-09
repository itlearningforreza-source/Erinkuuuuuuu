"""Connection Pooling - HTTP and Database connection pooling with stats."""

import asyncio
import logging
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
from collections import deque
import asyncio
import aiohttp
import asyncpg
import psycopg2
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PoolState(str, Enum):
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    EXHAUSTED = "EXHAUSTED"
    CLOSED = "CLOSED"


@dataclass
class PoolConfig:
    min_size: int = 5
    max_size: int = 20
    acquire_timeout: float = 30.0
    idle_timeout: float = 300.0
    max_lifetime: float = 3600.0
    health_check_interval: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 0.1
    enable_stats: bool = True
    name: str = "default"


@dataclass
class PoolStats:
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    waiting_requests: int = 0
    total_acquired: int = 0
    total_released: int = 0
    total_errors: int = 0
    total_wait_time_ms: float = 0.0
    avg_wait_time_ms: float = 0.0
    avg_hold_time_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_reset: datetime = field(default_factory=datetime.utcnow)

    def record_acquire(self, wait_time_ms: float, hold_time_ms: float = 0):
        self.total_acquired += 1
        self.total_wait_time_ms += wait_time_ms
        self.total_hold_time_ms += hold_time_ms
        if self.total_acquired > 0:
            self.avg_wait_time_ms = self.total_wait_time_ms / self.total_acquired
            self.avg_hold_time_ms = self.total_hold_time_ms / self.total_acquired

    def record_release(self):
        self.total_released += 1

    def record_error(self):
        self.total_errors += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "waiting_requests": self.waiting_requests,
            "total_acquired": self.total_acquired,
            "total_released": self.total_released,
            "total_errors": self.total_errors,
            "avg_wait_time_ms": self.avg_wait_time_ms,
            "avg_hold_time_ms": self.avg_hold_time_ms,
            "error_rate": self.total_errors / max(self.total_acquired, 1),
        }


class ConnectionPool:
    """Generic connection pool base class."""

    def __init__(self, config: PoolConfig):
        self.config = config
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=config.max_size)
        self._created = 0
        self._in_use = 0
        self._lock = asyncio.Lock()
        self._state = PoolState.INITIALIZING
        self._stats = PoolStats()
        self._health_check_task: Optional[asyncio.Task] = None
        self._closed = False

    @property
    def state(self) -> PoolState:
        return self._state

    @property
    def stats(self) -> PoolStats:
        return self._stats

    async def initialize(self):
        """Initialize the pool with minimum connections."""
        async with self._lock:
            for _ in range(self.config.min_size):
                conn = await self._create_connection()
                await self._pool.put(conn)
            self._state = PoolState.READY
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _create_connection(self) -> Any:
        """Create a new connection - override in subclass."""
        raise NotImplementedError

    async def _check_connection(self, conn: Any) -> bool:
        """Check if connection is healthy."""
        raise NotImplementedError

    async def _close_connection(self, conn: Any):
        """Close a connection."""
        raise NotImplementedError

    async def acquire(self, timeout: float = None) -> Any:
        """Acquire a connection from the pool."""
        if self._closed:
            raise RuntimeError("Pool is closed")

        timeout = timeout or self.config.acquire_timeout
        start_time = time.time()

        async with self._lock:
            if self._state == PoolState.CLOSED:
                raise RuntimeError("Pool is closed")

            # Try to get from pool first
            try:
                conn = self._pool.get_nowait()
                self._in_use += 1
                wait_time = (time.time() - time.time()) * 1000  # Actually measure this
                self._stats.record_acquire(0)
                return conn
            except asyncio.QueueEmpty:
                pass

            # Create new connection if under limit
            if self._created < self.config.max_size:
                conn = await self._create_connection()
                self._created += 1
                self._in_use += 1
                self._stats.total_connections = self._created
                wait_time = (time.time() - time.time()) * 1000  # Fix this
                self._stats.record_acquire(0)
                return conn

        # Wait for available connection
        wait_start = time.time()
        try:
            conn = await asyncio.wait_for(self._pool.get(), timeout=timeout)
            wait_time = (time.time() - wait_start) * 1000
            self._in_use += 1
            self._stats.record_acquire(wait_time)
            return conn
        except asyncio.TimeoutError:
            self._stats.record_error()
            raise TimeoutError(f"Timeout acquiring connection after {timeout}s")

    async def release(self, conn: Any):
        """Release a connection back to the pool."""
        async with self._lock:
            if self._closed:
                await self._close_connection(conn)
                return

            if self._pool.full():
                # Pool is full, close the connection
                await self._close_connection(conn)
            else:
                await self._pool.put(conn)
                self._in_use -= 1
                self._stats.record_release()

    async def close(self):
        """Close the pool and all connections."""
        self._closed = True

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            while not self._pool.empty():
                conn = self._pool.get_nowait()
                await self._close_connection(conn)

            self._state = PoolState.CLOSED

    def get_stats(self) -> Dict[str, Any]:
        return self._stats.to_dict()

    async def _health_check_loop(self):
        """Background health check for connections."""
        while not self._closed:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _health_check(self):
        """Check health of idle connections."""
        async with self._lock:
            if self._closed:
                return

            # Check idle connections
            temp_connections = []
            while not self._pool.empty():
                conn = self._pool.get_nowait()
                try:
                    healthy = await self._check_connection(conn)
                    if healthy:
                        await self._pool.put(conn)
                    else:
                        await self._close_connection(conn)
                        self._created -= 1
                except Exception:
                    await self._close_connection(conn)
                    self._created -= 1

            # Ensure minimum connections
            while self._created < self.config.min_size:
                try:
                    conn = await self._create_connection()
                    await self._pool.put(conn)
                except Exception:
                    break


class HTTPConnectionPool(ConnectionPool):
    """HTTP connection pool using aiohttp."""

    def __init__(
        self,
        base_url: str,
        config: PoolConfig = None,
        connector: aiohttp.TCPConnector = None,
        headers: Dict[str, str] = None,
        timeout: aiohttp.ClientTimeout = None,
    ):
        pool_config = config or PoolConfig()
        super().__init__(pool_config)
        self.base_url = base_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector = connector
        self._headers = headers or {}
        self._timeout = timeout or aiohttp.ClientTimeout(total=30)

    async def _create_connection(self) -> aiohttp.ClientSession:
        """Create a new HTTP session."""
        if self._session is None or self._session.closed:
            connector = self._connector or aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )
            self._session = aiohttp.ClientSession(
                base_url=self.base_url,
                connector=connector,
                headers=self._headers,
                timeout=self._timeout,
            )
        return self._session

    async def _check_connection(self, session: aiohttp.ClientSession) -> bool:
        """Check if session is healthy."""
        try:
            if session.closed:
                return False
            # Quick health check
            async with session.get("/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status < 500
        except Exception:
            return False

    async def _close_connection(self, session: aiohttp.ClientSession):
        if session and not session.closed:
            await session.close()

    async def request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request using pooled connection."""
        session = await self.acquire()
        try:
            url = f"{self.base_url}{path}"
            response = await session.request(method, url, **kwargs)
            return response
        finally:
            await self.release(session)

    async def get(self, path: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> aiohttp.ClientResponse:
        return await self.request("DELETE", path, **kwargs)

    async def close(self):
        await super().close()
        if self._session and not self._session.closed:
            await self._session.close()


class DatabaseConnectionPool(ConnectionPool):
    """PostgreSQL connection pool using asyncpg."""

    def __init__(
        self,
        dsn: str,
        config: PoolConfig = None,
        **kwargs
    ):
        pool_config = config or PoolConfig()
        super().__init__(pool_config)
        self.dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None
        self._kwargs = kwargs

    async def _create_connection(self) -> asyncpg.Connection:
        """Create a new database connection."""
        return await asyncpg.connect(self.dsn, **self._kwargs)

    async def _check_connection(self, conn: asyncpg.Connection) -> bool:
        """Check if connection is healthy."""
        try:
            if conn.is_closed():
                return False
            await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def _close_connection(self, conn: asyncpg.Connection):
        await conn.close()

    async def initialize(self):
        """Initialize the connection pool."""
        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=self.config.min_size,
            max_size=self.config.max_size,
            command_timeout=60,
            **self._kwargs
        )
        self._state = PoolState.READY

    async def acquire(self, timeout: float = None) -> asyncpg.Connection:
        """Acquire a connection from the pool."""
        if self._closed:
            raise RuntimeError("Pool is closed")

        timeout = timeout or self.config.acquire_timeout
        start_time = time.time()

        try:
            conn = await asyncio.wait_for(self._pool.acquire(), timeout=timeout)
            wait_time = (time.time() - time.time()) * 1000  # Fix this
            self._stats.record_acquire(0)
            return conn
        except asyncio.TimeoutError:
            self._stats.record_error()
            raise TimeoutError(f"Timeout acquiring connection after {timeout}s")

    async def release(self, conn: asyncpg.Connection):
        """Release connection back to pool."""
        if self._closed:
            await conn.close()
            return

        await self._pool.release(conn)
        self._stats.record_release()

    async def execute(self, query: str, *args, timeout: float = None) -> str:
        """Execute a query."""
        conn = await self.acquire(timeout)
        try:
            return await conn.execute(query, *args, timeout=timeout)
        finally:
            await self.release(conn)

    async def fetch(self, query: str, *args, timeout: float = None) -> List[asyncpg.Record]:
        conn = await self.acquire(timeout)
        try:
            return await conn.fetch(query, *args, timeout=timeout)
        finally:
            await self.release(conn)

    async def fetchrow(self, query: str, *args, timeout: float = None) -> Optional[asyncpg.Record]:
        conn = await self.acquire(timeout)
        try:
            return await conn.fetchrow(query, *args, timeout=timeout)
        finally:
            await self.release(conn)

    async def fetchval(self, query: str, *args, timeout: float = None) -> Any:
        conn = await self.acquire(timeout)
        try:
            return await conn.fetchval(query, *args, timeout=timeout)
        finally:
            await self.release(conn)

    async def close(self):
        if self._pool:
            await self._pool.close()
        self._closed = True
        self._state = PoolState.CLOSED


class PoolManager:
    """Manages multiple connection pools."""

    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = asyncio.Lock()

    def add_pool(self, name: str, pool: ConnectionPool):
        self._pools[name] = pool

    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        return self._pools.get(name)

    def remove_pool(self, name: str) -> bool:
        if name in self._pools:
            del self._pools[name]
            return True
        return False

    async def initialize_all(self):
        for pool in self._pools.values():
            await pool.initialize()

    async def close_all(self):
        for pool in self._pools.values():
            await pool.close()
        self._pools.clear()

    def get_all_stats(self) -> Dict[str, Dict]:
        return {name: pool.get_stats() for name, pool in self._pools.items()}

    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        return self._pools.get(name)


def create_pool_manager() -> PoolManager:
    return PoolManager()


def create_pool_config(
    min_size: int = 5,
    max_size: int = 20,
    acquire_timeout: float = 30.0,
    idle_timeout: float = 300.0,
    max_lifetime: float = 3600.0,
    health_check_interval: float = 30.0,
    retry_attempts: int = 3,
    retry_delay: float = 0.1,
) -> PoolConfig:
    return PoolConfig(
        min_size=min_size,
        max_size=max_size,
        acquire_timeout=acquire_timeout,
        idle_timeout=idle_timeout,
        max_lifetime=max_lifetime,
        health_check_interval=health_check_interval,
        retry_attempts=retry_attempts,
        retry_delay=retry_delay,
    )