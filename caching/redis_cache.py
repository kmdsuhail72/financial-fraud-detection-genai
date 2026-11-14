"""
Phase 39: Redis Cache Adapter
Redis OSS and AWS ElastiCache compatible adapter with JSON serialization and metrics.
"""

import json
import logging
from typing import Any, Optional
from caching.base import BaseCache
from caching.models import CacheMetrics

logger = logging.getLogger("caching.redis")


class RedisCache(BaseCache):
    """Production Redis/ElastiCache adapter with JSON serialization."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        socket_timeout: float = 0.5,
        socket_connect_timeout: float = 0.2,
        auto_connect: bool = False,
        client: Optional[Any] = None,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.ssl = ssl
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._client = client
        self._connected = bool(client is not None)

        if client is not None:
            return

        if auto_connect:
            try:
                import redis
                self._client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    ssl=ssl,
                    socket_timeout=socket_timeout,
                    socket_connect_timeout=socket_connect_timeout,
                    decode_responses=True,
                )
                self._client.ping()
                self._connected = True
                logger.info("Successfully connected to Redis at %s:%s", host, port)
            except Exception as e:
                logger.debug("Redis connection unavailable (%s:%s): %s.", host, port, e)
                self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_client(self) -> Any:
        return self._client

    def get(self, key: str) -> Optional[Any]:
        if not self._connected or not self._client:
            self._misses += 1
            return None
        try:
            data = self._client.get(key)
            if data is None:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(data)
        except (json.JSONDecodeError, Exception) as err:
            logger.error("Redis get failed for key %s: %s", key, err)
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        if not self._connected or not self._client:
            return False
        try:
            payload = json.dumps(value)
            if ttl_seconds and ttl_seconds > 0:
                self._client.setex(name=key, time=ttl_seconds, value=payload)
            else:
                self._client.set(name=key, value=payload)
            return True
        except Exception as err:
            logger.error("Redis set failed for key %s: %s", key, err)
            return False

    def delete(self, key: str) -> bool:
        if not self._connected or not self._client:
            return False
        try:
            res = self._client.delete(key)
            return bool(res > 0)
        except Exception as err:
            logger.error("Redis delete failed for key %s: %s", key, err)
            return False

    def exists(self, key: str) -> bool:
        if not self._connected or not self._client:
            return False
        try:
            return bool(self._client.exists(key) > 0)
        except Exception as err:
            logger.error("Redis exists failed for key %s: %s", key, err)
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        if not self._connected or not self._client:
            return None
        try:
            ttl = self._client.ttl(key)
            if ttl == -2:  # Key does not exist
                return None
            if ttl == -1:  # No expiry
                return -1
            return ttl
        except Exception as err:
            logger.error("Redis ttl check failed for key %s: %s", key, err)
            return None

    def flush(self) -> bool:
        if not self._connected or not self._client:
            return False
        try:
            self._client.flushdb()
            return True
        except Exception as err:
            logger.error("Redis flushdb failed: %s", err)
            return False

    def get_metrics(self) -> CacheMetrics:
        total = self._hits + self._misses
        ratio = round(self._hits / total, 4) if total > 0 else 0.0
        keys_count = 0
        if self._connected and self._client:
            try:
                keys_count = self._client.dbsize()
            except Exception:
                keys_count = 0
        return CacheMetrics(
            hits=self._hits,
            misses=self._misses,
            hit_ratio=ratio,
            evictions=self._evictions,
            total_keys=keys_count,
            backend_type="redis",
        )
