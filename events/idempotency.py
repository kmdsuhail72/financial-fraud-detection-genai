"""
FinGuard AI — Phase 33: Idempotency & Deduplication Engine.
Prevents duplicate event processing and transaction replays across distributed microservices.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple


class IdempotencyEngine:
    def __init__(self, ttl_seconds: int = 86400):
        self._lock = threading.RLock()
        self.ttl_seconds = ttl_seconds
        # key -> (result_dict, expires_at_timestamp)
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self.deduplication_count: int = 0

    def check_and_set(self, key: str, result: Optional[Any] = None) -> Tuple[bool, Optional[Any]]:
        """
        Returns (is_duplicate, cached_result).
        If not duplicate and result is supplied, stores it immediately.
        """
        now = time.time()
        with self._lock:
            # Clean expired keys
            if key in self._cache:
                cached_data, exp = self._cache[key]
                if now < exp:
                    self.deduplication_count += 1
                    return True, cached_data
                else:
                    del self._cache[key]

            if result is not None:
                self._cache[key] = (result, now + self.ttl_seconds)

            return False, None

    def store_result(self, key: str, result: Any):
        now = time.time()
        with self._lock:
            self._cache[key] = (result, now + self.ttl_seconds)

    def clear(self):
        with self._lock:
            self._cache.clear()
            self.deduplication_count = 0


# Global singleton engine
idempotency_engine = IdempotencyEngine()
