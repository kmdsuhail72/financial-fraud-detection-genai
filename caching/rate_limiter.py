"""
Phase 39: Distributed Rate Limiter
Atomic Redis Lua script fixed-window rate limiter with memory fallback.
"""

import math
import time
import threading
from typing import Any, Dict, Optional, Tuple
from caching.models import RateLimitRequest, RateLimitResult

# Production-grade atomic Lua script for Redis fixed-window rate limiting
REDIS_LUA_RATE_LIMITER = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local cost = tonumber(ARGV[3]) or 1

local current = redis.call('INCRBY', key, cost)
if current == cost then
    redis.call('EXPIRE', key, window)
end

local ttl = redis.call('TTL', key)
if ttl < 0 then
    redis.call('EXPIRE', key, window)
    ttl = window
end

local allowed = 0
if current <= limit then
    allowed = 1
end

return {allowed, current, limit, ttl}
"""


class DistributedRateLimiter:
    """
    Fixed-window rate limiter utilizing atomic Redis Lua execution
    when available, with transparent thread-safe memory fallback.
    """

    def __init__(self, redis_client: Optional[Any] = None):
        self._redis = redis_client
        self._lua_script = None
        self._memory_store: Dict[str, Tuple[int, float]] = {}  # key -> (count, window_start)
        self._lock = threading.Lock()

        if self._redis:
            try:
                self._lua_script = self._redis.register_script(REDIS_LUA_RATE_LIMITER)
            except Exception:
                self._lua_script = None

    def check_rate_limit(self, req: RateLimitRequest) -> RateLimitResult:
        """Evaluate rate limit request against active backend."""
        key = f"rate_limit:{req.identifier}:{req.window_seconds}"

        # 1. Try Redis Lua script execution if connected
        if self._redis and self._lua_script:
            try:
                # Returns [allowed_int, current_count, limit, ttl]
                res = self._lua_script(
                    keys=[key],
                    args=[req.limit, req.window_seconds, req.cost],
                )
                allowed = bool(res[0] == 1)
                current = int(res[1])
                limit = int(res[2])
                ttl = max(1, int(res[3]))
                remaining = max(0, limit - current)
                retry_after = ttl if not allowed else None

                return RateLimitResult(
                    allowed=allowed,
                    current_count=current,
                    limit=limit,
                    remaining=remaining,
                    reset_seconds=ttl,
                    retry_after=retry_after,
                )
            except Exception:
                # Fallback to local memory limiter on connection error
                pass

        # 2. In-Memory Atomic Rate Limiter Fallback
        now = time.time()
        with self._lock:
            if key in self._memory_store:
                count, window_start = self._memory_store[key]
                elapsed = now - window_start
                if elapsed >= req.window_seconds:
                    # Reset window
                    count = req.cost
                    window_start = now
                else:
                    count += req.cost
            else:
                count = req.cost
                window_start = now

            self._memory_store[key] = (count, window_start)

            elapsed = now - window_start
            reset_seconds = max(1, math.ceil(req.window_seconds - elapsed))
            allowed = count <= req.limit
            remaining = max(0, req.limit - count)
            retry_after = reset_seconds if not allowed else None

            return RateLimitResult(
                allowed=allowed,
                current_count=count,
                limit=req.limit,
                remaining=remaining,
                reset_seconds=reset_seconds,
                retry_after=retry_after,
            )

    def reset_key(self, identifier: str, window_seconds: int = 60) -> bool:
        """Force reset of a specific rate limiter key."""
        key = f"rate_limit:{identifier}:{window_seconds}"
        with self._lock:
            if key in self._memory_store:
                del self._memory_store[key]
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                pass
        return True
