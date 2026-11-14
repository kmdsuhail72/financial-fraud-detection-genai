"""
Phase 39: Enterprise Idempotency Layer
Tenant-scoped, SHA-256 hashed idempotency keys with response caching and replay.
"""

import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
from caching.base import BaseCache
from caching.models import IdempotencyRecord, IdempotencyRequest

DEFAULT_IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours


class IdempotencyManager:
    """Manages tenant-scoped idempotent request execution and response replay."""

    def __init__(self, cache_backend: BaseCache, ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS):
        self._cache = cache_backend
        self._ttl = ttl_seconds

    @staticmethod
    def compute_key_hash(tenant_id: str, idempotency_key: str) -> str:
        """Compute SHA-256 digest of tenant_id and idempotency key."""
        raw = f"tenant:{tenant_id}:key:{idempotency_key}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_payload_hash(payload: Dict[str, Any]) -> str:
        """Compute stable hash of request payload to detect payload mismatches."""
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def check_or_reserve(
        self,
        tenant_id: str,
        idempotency_key: str,
        request_payload: Dict[str, Any],
    ) -> Tuple[bool, Optional[IdempotencyRecord]]:
        """
        Check if an idempotency key exists.
        Returns:
            (is_new, record)
            - If is_new is True: operation should proceed and save_result called later.
            - If is_new is False: record contains previously executed result or in-progress state.
        """
        key_hash = self.compute_key_hash(tenant_id, idempotency_key)
        cache_key = f"idempotency:{key_hash}"
        cached = self._cache.get(cache_key)

        if cached is not None:
            # Parse record
            record_data = cached if isinstance(cached, dict) else json.loads(cached)
            record = IdempotencyRecord(**record_data)
            record.is_replayed = True
            return False, record

        # Reserve key in IN_PROGRESS state
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self._ttl)
        record = IdempotencyRecord(
            tenant_id=tenant_id,
            key_hash=key_hash,
            status="IN_PROGRESS",
            response_payload={
                "_payload_hash": self.compute_payload_hash(request_payload),
                "_initiated_at": now.isoformat(),
            },
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            is_replayed=False,
        )
        self._cache.set(cache_key, record.model_dump(), ttl_seconds=self._ttl)
        return True, record

    def save_result(
        self,
        tenant_id: str,
        idempotency_key: str,
        response_payload: Dict[str, Any],
    ) -> IdempotencyRecord:
        """Save the completed response payload against the idempotency record."""
        key_hash = self.compute_key_hash(tenant_id, idempotency_key)
        cache_key = f"idempotency:{key_hash}"
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self._ttl)

        record = IdempotencyRecord(
            tenant_id=tenant_id,
            key_hash=key_hash,
            status="COMPLETED",
            response_payload=response_payload,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            is_replayed=False,
        )
        self._cache.set(cache_key, record.model_dump(), ttl_seconds=self._ttl)
        return record

