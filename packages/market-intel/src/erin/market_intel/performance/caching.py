"""Caching - Multi-level caching with multiple strategies and backends."""

import asyncio
import hashlib
import logging
import pickle
import threading
import time
import uuid
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
from collections import OrderedDict, defaultdict
from pathlib import Path
import asyncio
import pickle

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    LRU = "LRU"
    LFU = "LFU"
    FIFO = "FIFO"
    TTL = "TTL"
    ADAPTIVE = "ADAPTIVE"


class CacheBackendType(str, Enum):
    MEMORY = "MEMORY"
    REDIS = "REDIS"
    MEMCACHED = "MEMCACHED"
    DISK = "DISK"


@dataclass
class CacheConfig:
    strategy: CacheStrategy = CacheStrategy.LRU
    max_size: int = 10000
    ttl_seconds: int = 3600
    max_memory_mb: int = 512
    enable_compression: bool = False
    enable_stats: bool = True
    eviction_batch_size: int = 100
    async_write: bool = True
    backend: str = "MEMORY"
    backend_config: Dict = field(default_factory=dict)


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds

    def touch(self):
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

    def size_estimate(self) -> int:
        try:
            return len(pickle.dumps(self.value))
        except:
            return len(str(self.value).encode())


class CacheBackend:
    """Abstract base class for cache backends."""

    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        raise NotImplementedError

    async def clear(self) -> bool:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    async def get_stats(self) -> Dict[str, Any]:
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with multiple eviction strategies."""

    def __init__(self, config: 'CacheConfig'):
        self.config = config
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: OrderedDict[str, None] = OrderedDict()
        self._frequency: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "memory_bytes": 0,
        }

    def _estimate_size(self, value: Any) -> int:
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode())

    def _evict_lru(self, count: int = None):
        """Evict least recently used entries."""
        count = count or self.config.eviction_batch_size
        evicted = 0
        for key in list(self._access_order.keys()):
            if evicted >= count:
                break
            if key in self._cache:
                self._stats["memory_bytes"] -= self._cache[key].size_bytes
                del self._cache[key]
                self._access_order.pop(key, None)
                self._frequency.pop(key, None)
                evicted += 1
        self._stats["evictions"] += evicted

    def _evict_lfu(self, count: int = None):
        """Evict least frequently used entries."""
        count = count or self.config.eviction_batch_size
        sorted_items = sorted(self._frequency.items(), key=lambda x: x[1])
        evicted = 0
        for key, _ in sorted_items[:count]:
            if key in self._cache:
                self._stats["memory_bytes"] -= self._cache[key].size_bytes
                del self._cache[key]
                self._access_order.pop(key, None)
                self._frequency.pop(key, None)
                evicted += 1
        self._stats["evictions"] += evicted

    def _evict_ttl(self):
        """Evict expired entries."""
        now = datetime.utcnow()
        expired = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                self._stats["memory_bytes"] -= entry.size_bytes
                self._access_order.pop(key, None)
                self._frequency.pop(key, None)
                self._cache.pop(key, None)
                self._stats["evictions"] += 1

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired():
                self._stats["memory_bytes"] -= entry.size_bytes
                self._access_order.pop(key, None)
                self._frequency.pop(key, None)
                self._cache.pop(key, None)
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                return None

            entry.touch()
            self._access_order[key] = None
            self._access_order.move_to_end(key)
            self._frequency[key] += 1
            self._stats["hits"] += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            size = self._estimate_size(value)
            ttl = ttl or self.config.ttl_seconds

            # Check if we need to evict
            while (self._stats["memory_bytes"] + size > self.config.max_memory_mb * 1024 * 1024
                   or len(self._cache) >= self.config.max_size):
                self._evict_lru(1)

            entry = CacheEntry(
                key=key,
                value=value,
                ttl_seconds=ttl,
                size_bytes=size,
            )
            self._cache[key] = entry
            self._access_order[key] = None
            self._access_order.move_to_end(key)
            self._frequency[key] = 1
            self._stats["memory_bytes"] += size
            self._stats["sets"] += 1
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                self._stats["memory_bytes"] -= self._cache[key].size_bytes
                self._cache.pop(key, None)
                self._access_order.pop(key, None)
                self._frequency.pop(key, None)
                self._stats["deletes"] += 1
                return True
            return False

    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._frequency.clear()
            self._stats["memory_bytes"] = 0
            return True

    async def exists(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                self._stats["memory_bytes"] -= entry.size_bytes
                self._access_order.pop(key, None)
                self._frequency.pop(key, None)
                self._cache.pop(key, None)
                return False
            return True

    async def get_stats(self) -> Dict[str, Any]:
        async with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0
            return {
                **self._stats,
                "hit_rate": hit_rate,
                "entry_count": len(self._cache),
            }

    def _estimate_size(self, value: Any) -> int:
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode())


class RedisCacheBackend(CacheBackend):
    """Redis cache backend (requires redis-py)."""

    def __init__(self, config: 'CacheConfig'):
        self.config = config
        self._client = None
        self._config = config.backend_config

    async def _get_client(self):
        if self._client is None:
            import redis.asyncio as redis
            self._client = redis.Redis(
                host=self._config.get("host", "localhost"),
                port=self._config.get("port", 6379),
                db=self._config.get("db", 0),
                password=self._config.get("password"),
                decode_responses=False,
            )
        return self._client

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        data = await client.get(key)
        if data:
            return pickle.loads(data)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        client = await self._get_client()
        data = pickle.dumps(value)
        ttl = ttl or self.config.ttl_seconds
        await client.setex(key, ttl, data)
        return True

    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        result = await client.delete(key)
        return result > 0

    async def clear(self) -> bool:
        client = await self._get_client()
        await client.flushdb()
        return True

    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        return await client.exists(key) > 0

    async def get_stats(self) -> Dict[str, Any]:
        client = await self._get_client()
        info = await client.info()
        return {
            "used_memory": info.get("used_memory", 0),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
        }


class DiskCacheBackend(CacheBackend):
    """Disk-based cache backend using filesystem."""

    def __init__(self, config: 'CacheConfig'):
        self.config = config
        self.cache_dir = Path(config.backend_config.get("path", "~/.erin/cache")).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _get_path(self, key: str) -> Path:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash[:2]}" / key_hash

    def _get_meta_path(self, key: str) -> Path:
        path = self._get_path(key)
        return path.with_suffix(".meta.json")

    async def get(self, key: str) -> Optional[Any]:
        path = self._get_path(key)
        meta_path = self._get_meta_path(key)
        if not meta_path.exists():
            return None

        meta = json.loads(meta_path.read_text())
        if datetime.fromisoformat(meta["expires_at"]) < datetime.utcnow():
            await self.delete(key)
            return None

        data = await asyncio.to_thread(self._read_file, key)
        return pickle.loads(data)

    def _read_file(self, key: str) -> bytes:
        path = self._get_path(key)
        return path.read_bytes()

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        data = pickle.dumps(value)
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "wb") as f:
            await f.write(data)

        meta = {
            "key": key,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=ttl or 3600)).isoformat(),
            "size": len(data),
        }
        meta_path = self._get_meta_path(key)
        meta_path.write_text(json.dumps(meta))
        return True

    def _get_meta_path(self, key: str) -> Path:
        path = self._get_path(key)
        return path.with_suffix(".meta.json")

    async def delete(self, key: str) -> bool:
        path = self._get_path(key)
        meta_path = self._get_meta_path(key)
        if path.exists():
            path.unlink()
        if self._get_meta_path(key).exists():
            self._get_meta_path(key).unlink()
        return True

    async def clear(self) -> bool:
        for path in self.cache_dir.rglob("*"):
            path.unlink()
        return True

    async def exists(self, key: str) -> bool:
        meta_path = self._get_meta_path(key)
        return meta_path.exists()

    async def get_stats(self) -> Dict[str, Any]:
        total_size = sum(f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file())
        return {
            "backend": "disk",
            "size_bytes": total_size,
            "entries": len(list(self.cache_dir.rglob("*"))),
        }


class MultiLevelCache:
    """Multi-level cache with L1 (memory) and L2 (Redis/Disk) tiers."""

    def __init__(
        self,
        l1_config: CacheConfig,
        l2_config: CacheConfig = None,
    ):
        self.l1 = MemoryCacheBackend(l1_config)
        self.l2 = None
        if l2_config:
            if l2_config.backend == "REDIS":
                self.l2 = RedisCacheBackend(l2_config)
            elif l2_config.backend == "DISK":
                self.l2 = DiskCacheBackend(l2_config)

    async def get(self, key: str) -> Optional[Any]:
        # Try L1 first
        value = await self.l1.get(key)
        if value is not None:
            return value

        # Try L2
        if self.l2:
            value = await self.l2.get(key)
            if value is not None:
                # Promote to L1
                await self.l1.set(key, value)
                return value
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        # Write to both levels
        await self.l1.set(key, value, ttl)
        if self.l2:
            await self.l2.set(key, value, ttl)
        return True

    async def delete(self, key: str) -> bool:
        r1 = await self.l1.delete(key)
        r2 = True
        if self.l2:
            r2 = await self.l2.delete(key)
        return r1 or r2

    async def clear(self) -> bool:
        await self.l1.clear()
        if self.l2:
            await self.l2.clear()
        return True

    async def get_stats(self) -> Dict[str, Any]:
        l1_stats = await self.l1.get_stats()
        l2_stats = await self.l2.get_stats() if self.l2 else {}
        return {
            "l1": l1_stats,
            "l2": l2_stats,
        }


class CacheManager:
    """High-level cache manager with multiple named caches."""

    def __init__(self):
        self._caches: Dict[str, MultiLevelCache] = {}
        self._configs: Dict[str, Tuple[CacheConfig, CacheConfig]] = {}
        self._lock = asyncio.Lock()

    async def create_cache(
        self,
        name: str,
        l1_config: CacheConfig,
        l2_config: CacheConfig = None,
    ) -> MultiLevelCache:
        async with self._lock:
            if name in self._caches:
                raise ValueError(f"Cache '{name}' already exists")

            cache = MultiLevelCache(l1_config, l2_config)
            self._caches[name] = cache
            self._configs[name] = (l1_config, l2_config)
            return cache

    def get_cache(self, name: str) -> Optional[MultiLevelCache]:
        return self._caches.get(name)

    def remove_cache(self, name: str) -> bool:
        with self._lock:
            if name in self._caches:
                del self._caches[name]
                del self._configs[name]
                return True
            return False

    def list_caches(self) -> List[str]:
        return list(self._caches.keys())

    async def get_all_stats(self) -> Dict[str, Dict]:
        stats = {}
        for name, cache in self._caches.items():
            stats[name] = await cache.get_stats()
        return stats

    async def clear_all(self):
        for cache in self._caches.values():
            await cache.clear()


def create_cache_manager() -> CacheManager:
    return CacheManager()


def create_cache_config(
    strategy: str = "LRU",
    max_size: int = 10000,
    ttl_seconds: int = 3600,
    max_memory_mb: int = 512,
    backend: str = "MEMORY",
    backend_config: Dict = None,
) -> CacheConfig:
    return CacheConfig(
        strategy=CacheStrategy(strategy),
        max_size=max_size,
        ttl_seconds=ttl_seconds,
        max_memory_mb=max_memory_mb,
        backend=backend,
        backend_config=backend_config or {},
    )