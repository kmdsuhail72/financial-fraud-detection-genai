"""
FinGuard AI — Phase 33: Transactional Outbox Pattern Manager.
Guarantees dual-write consistency by persisting events locally before asynchronous bus dispatch.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import List, Optional

from events.event_bus import EventBus
from events.models import EventContract, OutboxRecord, OutboxStatus

logger = logging.getLogger("finguard-outbox")


class TransactionalOutbox:
    def __init__(self):
        self._lock = threading.RLock()
        self._records: List[OutboxRecord] = []

    def record_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event: EventContract,
    ) -> OutboxRecord:
        """
        Stores an outgoing domain event in the local transactional outbox with PENDING status.
        In a relational DB, this runs within the same database transaction as the entity state.
        """
        with self._lock:
            record = OutboxRecord(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event=event,
                status=OutboxStatus.PENDING,
            )
            self._records.append(record)
            logger.info("Outbox recorded pending event %s for %s %s", event.event_id, aggregate_type, aggregate_id)
            return record

    def flush(self, bus: EventBus) -> int:
        """
        Scans all PENDING outbox records, dispatches them to the EventBus,
        and marks them PUBLISHED (or FAILED if rejected).
        Returns number of successfully published events.
        """
        published_count = 0
        with self._lock:
            pending = [r for r in self._records if r.status == OutboxStatus.PENDING]

            for record in pending:
                try:
                    success = bus.publish(record.event)
                    if success:
                        record.status = OutboxStatus.PUBLISHED
                        record.published_at = datetime.now(timezone.utc)
                        published_count += 1
                    else:
                        record.retry_count += 1
                        if record.retry_count >= record.max_retries:
                            record.status = OutboxStatus.FAILED
                            record.error_message = "Retry limit reached during event publication"
                except Exception as exc:
                    record.retry_count += 1
                    record.error_message = str(exc)
                    if record.retry_count >= record.max_retries:
                        record.status = OutboxStatus.FAILED

        return published_count

    def list_records(self, status: Optional[OutboxStatus] = None) -> List[OutboxRecord]:
        with self._lock:
            if status:
                return [r for r in self._records if r.status == status]
            return list(self._records)

    def get_pending_count(self) -> int:
        with self._lock:
            return sum(1 for r in self._records if r.status == OutboxStatus.PENDING)

    def clear(self):
        with self._lock:
            self._records.clear()


# Global singleton outbox
transactional_outbox = TransactionalOutbox()

