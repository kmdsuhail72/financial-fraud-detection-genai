"""
FinGuard AI — Phase 31: In-Memory Data Integration Store.
Thread-safe storage for canonical events, dead-letter items, audit events, and metrics.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from integrations.models import (
    CanonicalEvent,
    DeadLetterEvent,
    EventSource,
    EventStatus,
    EventType,
    IntegrationAuditEntry,
    IntegrationMetrics,
)


class IntegrationStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._events: Dict[str, CanonicalEvent] = {}
        self._idempotency_index: Dict[str, str] = {}  # idempotency_key -> event_id
        self._dead_letters: Dict[str, DeadLetterEvent] = {}
        self._audit_log: List[IntegrationAuditEntry] = []
        self._seed_default_data()

    def _seed_default_data(self):
        """Seeds initial synthetic core banking and payment gateway events."""
        now = datetime.now(timezone.utc)

        # 1. Seed Core Banking Transaction
        cbs_evt = CanonicalEvent(
            event_id="EVT-CBS-BENCHMARK-01",
            idempotency_key="cbs:TXN-CBS-992014",
            source=EventSource.CORE_BANKING,
            event_type=EventType.TRANSACTION_POSTED,
            customer_id="CIF-990142",
            account_id="ACC-HDFC-991203",
            amount=450000.0,
            currency="INR",
            status=EventStatus.PROCESSED,
            received_at=now,
            raw_payload={
                "cbs_txn_id": "TXN-CBS-992014",
                "account_number": "ACC-HDFC-991203",
                "customer_cif": "CIF-990142",
                "amount": 450000.0,
                "txn_type": "DEBIT",
                "channel": "NETBANKING",
            },
            normalized_payload={
                "cbs_transaction_id": "TXN-CBS-992014",
                "account_id": "ACC-HDFC-991203",
                "customer_id": "CIF-990142",
                "amount": 450000.0,
                "currency": "INR",
                "transaction_type": "DEBIT",
                "channel": "NETBANKING",
            },
        )
        self._events[cbs_evt.event_id] = cbs_evt
        self._idempotency_index[cbs_evt.idempotency_key] = cbs_evt.event_id
        self._record_audit("EVENT_INGESTED", "CORE_BANKING", cbs_evt.event_id, {"amount": 450000.0})

        # 2. Seed Payment Gateway Captured Event
        gw_evt = CanonicalEvent(
            event_id="EVT-GW-BENCHMARK-02",
            idempotency_key="gateway:razorpay:pay_rzp_990148",
            source=EventSource.PAYMENT_GATEWAY,
            event_type=EventType.PAYMENT_CAPTURED,
            customer_id="customer.alex@example.com",
            account_id="order_990148",
            amount=125000.0,
            currency="INR",
            status=EventStatus.PROCESSED,
            received_at=now,
            raw_payload={
                "gateway_payment_id": "pay_rzp_990148",
                "order_id": "order_990148",
                "gateway_provider": "RAZORPAY",
                "event_name": "payment.captured",
                "amount": 125000.0,
            },
            normalized_payload={
                "gateway_payment_id": "pay_rzp_990148",
                "order_id": "order_990148",
                "provider": "RAZORPAY",
                "amount": 125000.0,
            },
        )
        self._events[gw_evt.event_id] = gw_evt
        self._idempotency_index[gw_evt.idempotency_key] = gw_evt.event_id
        self._record_audit("EVENT_INGESTED", "PAYMENT_GATEWAY", gw_evt.event_id, {"amount": 125000.0})

    def _record_audit(self, action: str, source: str, event_id: Optional[str], details: Dict):
        audit_entry = IntegrationAuditEntry(
            audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            event_id=event_id,
            action=action,
            source=source,
            details=details,
            timestamp=datetime.now(timezone.utc),
        )
        self._audit_log.append(audit_entry)

    def check_idempotency(self, idempotency_key: str) -> Optional[CanonicalEvent]:
        with self._lock:
            existing_event_id = self._idempotency_index.get(idempotency_key)
            if existing_event_id:
                return self._events.get(existing_event_id)
            return None

    def save_event(self, event: CanonicalEvent) -> CanonicalEvent:
        with self._lock:
            self._events[event.event_id] = event
            self._idempotency_index[event.idempotency_key] = event.event_id
            self._record_audit("EVENT_INGESTED", event.source.value, event.event_id, {"type": event.event_type.value})
            return event

    def record_duplicate(self, existing_event: CanonicalEvent) -> CanonicalEvent:
        with self._lock:
            self._record_audit(
                "DUPLICATE_DETECTED",
                existing_event.source.value,
                existing_event.event_id,
                {"idempotency_key": existing_event.idempotency_key},
            )
            # Return duplicate copy with DUPLICATE status
            dupe = existing_event.model_copy()
            dupe.status = EventStatus.DUPLICATE
            return dupe

    def record_dead_letter(
        self,
        source: str,
        payload: Dict,
        failure_reason: str,
        retry_attempts: int,
        original_event_id: Optional[str] = None,
    ) -> DeadLetterEvent:
        with self._lock:
            dlq_id = f"DLQ-{uuid.uuid4().hex[:8].upper()}"
            dlq_event = DeadLetterEvent(
                dlq_id=dlq_id,
                original_event_id=original_event_id,
                source=source,
                payload=payload,
                failure_reason=failure_reason,
                retry_attempts=retry_attempts,
                failed_at=datetime.now(timezone.utc),
            )
            self._dead_letters[dlq_id] = dlq_event
            self._record_audit("SENT_TO_DLQ", source, original_event_id, {"dlq_id": dlq_id, "reason": failure_reason})
            return dlq_event

    def list_events(self, limit: int = 50) -> List[CanonicalEvent]:
        with self._lock:
            items = list(self._events.values())
            items.sort(key=lambda x: x.received_at, reverse=True)
            return items[:limit]

    def list_dead_letters(self, limit: int = 50) -> List[DeadLetterEvent]:
        with self._lock:
            items = list(self._dead_letters.values())
            items.sort(key=lambda x: x.failed_at, reverse=True)
            return items[:limit]

    def list_audit_trail(self, limit: int = 100) -> List[IntegrationAuditEntry]:
        with self._lock:
            items = list(self._audit_log)
            items.sort(key=lambda x: x.timestamp, reverse=True)
            return items[:limit]

    def get_metrics(self) -> IntegrationMetrics:
        with self._lock:
            events = list(self._events.values())
            dlqs = list(self._dead_letters.values())
            total = len(events) + len(dlqs)

            processed = len(events)
            dlq_count = len(dlqs)
            dupes = sum(1 for e in self._audit_log if e.action == "DUPLICATE_DETECTED")

            cbs = sum(1 for e in events if e.source == EventSource.CORE_BANKING)
            gw = sum(1 for e in events if e.source == EventSource.PAYMENT_GATEWAY)
            webhooks = sum(1 for e in events if e.source == EventSource.WEBHOOK)

            success_rate = (float(processed) / float(total) * 100.0) if total > 0 else 100.0

            return IntegrationMetrics(
                total_events_received=total,
                processed_count=processed,
                duplicate_count=dupes,
                dead_letter_count=dlq_count,
                cbs_events_count=cbs,
                gateway_events_count=gw,
                webhook_events_count=webhooks,
                success_rate_percent=round(success_rate, 2),
            )


# Global singleton store
integration_store = IntegrationStore()
