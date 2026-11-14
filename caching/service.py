"""
Phase 39: Caching Architecture Service
Unified service orchestrating Redis/memory caching, rate limiting, idempotency, and policies.
"""

from datetime import datetime, timezone
from typing import List, Optional
from caching.base import BaseCache
from caching.memory_cache import MemoryCache
from caching.redis_cache import RedisCache
from caching.cache_aside import CacheAsideManager
from caching.rate_limiter import DistributedRateLimiter
from caching.idempotency import IdempotencyManager
from caching.models import CachePolicy, CachingHealthResponse

# Standard FinGuard Enterprise Cache Policies
ENTERPRISE_CACHE_POLICIES: List[CachePolicy] = [
    CachePolicy(
        data_type="Customer Profile",
        ttl_seconds=300,
        ttl_display="5 minutes",
        invalidation_trigger="Profile update / KYC verification event",
        description="Cached customer metadata and risk tiers used in real-time fraud scoring",
    ),
    CachePolicy(
        data_type="Merchant Metadata",
        ttl_seconds=900,
        ttl_display="15 minutes",
        invalidation_trigger="Merchant category or risk status update",
        description="High-traffic merchant reputation scores and MCC classifications",
    ),
    CachePolicy(
        data_type="Transaction Lookup",
        ttl_seconds=60,
        ttl_display="1 minute",
        invalidation_trigger="Short-lived TTL expiry",
        description="Short-lived deduplication and velocity lookup during payment settlement",
    ),
    CachePolicy(
        data_type="Idempotency Response",
        ttl_seconds=86400,
        ttl_display="24 hours",
        invalidation_trigger="Time-based expiry",
        description="Tenant-scoped response replay cache preventing double transactions",
    ),
    CachePolicy(
        data_type="Rate-Limit Counter",
        ttl_seconds=60,
        ttl_display="60 seconds",
        invalidation_trigger="Sliding/fixed window expiry",
        description="Distributed quota counters preventing API flooding and brute force attacks",
    ),
]


class CachingService:
    """Central manager for FinGuard caching architecture and coordination."""

    def __init__(self, prefer_redis: bool = False, redis_host: str = "localhost", redis_port: int = 6379):
        self._memory_cache = MemoryCache()
        self._redis_cache = RedisCache(host=redis_host, port=redis_port, auto_connect=prefer_redis)

        # Select primary backend
        if prefer_redis and self._redis_cache.is_connected:
            self._backend: BaseCache = self._redis_cache
            self._backend_type = "redis"
        else:
            self._backend: BaseCache = self._memory_cache
            self._backend_type = "memory"

        self.cache_aside = CacheAsideManager(self._backend)
        self.rate_limiter = DistributedRateLimiter(
            redis_client=self._redis_cache.get_client() if self._redis_cache.is_connected else None
        )
        self.idempotency = IdempotencyManager(self._backend)

    @property
    def backend(self) -> BaseCache:
        return self._backend

    @property
    def backend_type(self) -> str:
        return self._backend_type

    @property
    def is_redis_connected(self) -> bool:
        return self._redis_cache.is_connected

    def get_policies(self) -> List[CachePolicy]:
        return ENTERPRISE_CACHE_POLICIES

    def get_health(self) -> CachingHealthResponse:
        metrics = self._backend.get_metrics()
        return CachingHealthResponse(
            status="healthy",
            backend=self._backend_type,
            redis_connected=self._redis_cache.is_connected,
            metrics=metrics,
            policies=ENTERPRISE_CACHE_POLICIES,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# Global singleton instance
caching_service = CachingService()
