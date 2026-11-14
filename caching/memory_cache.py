"""
Phase 39: In-Memory Cache Adapter
Thread-safe local development and testing cache with TTL expiration and metrics.
"""

import math
import time
import threading
from typing import Any, Dict, Optional, Tuple
from caching.base import BaseCache
from caching.models import CacheMetrics


class MemoryCache(BaseCache):
    """Thread-safe in-memory key-value cache with TTL enforcement."""

    def __init__(self, max_keys: int = 10000):
        self._max_keys = max_keys
        # Store tuple: (value, expires_at_epoch)
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _purge_expired(self) -> None:
        """Internal helper to clean up expired keys if capacity is reached."""
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if exp is not None and exp <= now]
        for k in expired_keys:
            del self._store[k]
            self._evictions += 1

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            if key in self._store:
                val, expires_at = self._store[key]
                if expires_at is not None and expires_at <= now:
                    del self._store[key]
                    self._misses += 1
                    self._evictions += 1
                    return None
                self._hits += 1
                return val
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        now = time.time()
        expires_at = now + ttl_seconds if ttl_seconds is not None and ttl_seconds > 0 else None
        with self._lock:
            if len(self._store) >= self._max_keys and key not in self._store:
                self._purge_expired()
                if len(self._store) >= self._max_keys:
                    # Evict oldest key
                    first_key = next(iter(self._store))
                    del self._store[first_key]
                    self._evictions += 1
            self._store[key] = (value, expires_at)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def get_ttl(self, key: str) -> Optional[int]:
        now = time.time()
        with self._lock:
            if key in self._store:
                _, expires_at = self._store[key]
                if expires_at is None:
                    return -1  # Persistent key
                if expires_at <= now:
                    del self._store[key]
                    self._evictions += 1
                    return None
                return max(1, int(math.ceil(expires_at - now)))
            return None

    def flush(self) -> bool:
        with self._lock:
            self._store.clear()
            return True

    def get_metrics(self) -> CacheMetrics:
        with self._lock:
            total_requests = self._hits + self._misses
            ratio = round(self._hits / total_requests, 4) if total_requests > 0 else 0.0
            return CacheMetrics(
                hits=self._hits,
                misses=self._misses,
                hit_ratio=ratio,
                evictions=self._evictions,
                total_keys=len(self._store),
                backend_type="memory",
            )
