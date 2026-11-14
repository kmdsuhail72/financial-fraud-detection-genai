"""
Phase 39: Base Cache Adapter Interface
Defines the standard abstraction for high-performance key-value caching backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from caching.models import CacheMetrics


class BaseCache(ABC):
    """Abstract interface for FinGuard caching implementations."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from cache by key. Returns None if missing or expired."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store an item with an optional TTL in seconds."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove an item from cache. Returns True if item was present and deleted."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a valid unexpired key exists."""
        pass

    @abstractmethod
    def get_ttl(self, key: str) -> Optional[int]:
        """Return remaining TTL in seconds, or None if expired or key does not exist."""
        pass

    @abstractmethod
    def flush(self) -> bool:
        """Evict all cached entries."""
        pass

    @abstractmethod
    def get_metrics(self) -> CacheMetrics:
        """Return real-time access statistics (hits, misses, ratio)."""
        pass
