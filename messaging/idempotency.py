"""
Phase 40: Tenant-Scoped Message Idempotency
Enforces at-least-once message processing without duplicate business execution.
"""

import hashlib
import threading
import time
from typing import Any, Dict, Optional


class MessageIdempotencyManager:
    """Tracks message processing to ensure deduplication within and across tenants."""

    def __init__(self, ttl_seconds: int = 86400):
        self._ttl_seconds = ttl_seconds
        # key_hash -> (result_data, expires_at_epoch)
        self._processed: Dict[str, Tuple_Type] = {}
        self._lock = threading.Lock()

    @staticmethod
    def compute_key(tenant_id: str, deduplication_id: str) -> str:
        """Compute SHA-256 hash for tenant-scoped message deduplication."""
        raw = f"tenant:{tenant_id}:dedup:{deduplication_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_duplicate(self, tenant_id: str, deduplication_id: str) -> bool:
        """Check if message has already been processed and its record is still valid."""
        key = self.compute_key(tenant_id, deduplication_id)
        now = time.time()
        with self._lock:
            if key in self._processed:
                _, expires_at = self._processed[key]
                if expires_at > now:
                    return True
                else:
                    del self._processed[key]
            return False

    def record_processed(
        self,
        tenant_id: str,
        deduplication_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record successful execution of a message."""
        key = self.compute_key(tenant_id, deduplication_id)
        expires_at = time.time() + self._ttl_seconds
        with self._lock:
            self._processed[key] = (result or {}, expires_at)
            return True

    def get_result(self, tenant_id: str, deduplication_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored outcome of previously processed message."""
        key = self.compute_key(tenant_id, deduplication_id)
        now = time.time()
        with self._lock:
            if key in self._processed:
                result, expires_at = self._processed[key]
                if expires_at > now:
                    return result
                del self._processed[key]
            return None

    def clear(self) -> None:
        """Clear all idempotency records."""
        with self._lock:
            self._processed.clear()


# Type alias helper
Tuple_Type = tuple[Dict[str, Any], float]
