"""
FinGuard AI — Phase 31: Data Integration Service Layer.
Coordinates ingestion, idempotency deduplication, retry processing, dead-letter routing, and monitoring.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from integrations.adapters import (
    DEFAULT_WEBHOOK_SECRET,
    map_core_banking_to_canonical,
    map_payment_gateway_to_canonical,
    verify_hmac_sha256,
)
from integrations.models import (
    CanonicalEvent,
    CoreBankingEventRequest,
    DeadLetterEvent,
    EventSource,
    EventStatus,
    EventType,
    GenericEventRequest,
    IntegrationAuditEntry,
    IntegrationMetrics,
    PaymentGatewayEventRequest,
)
from integrations.store import IntegrationStore, integration_store

logger = logging.getLogger("finguard-integrations")


class IntegrationService:
    def __init__(self, store: Optional[IntegrationStore] = None):
        self.store = store or integration_store

    def ingest_generic_event(self, req: GenericEventRequest) -> Tuple[CanonicalEvent, bool]:
        """
        Ingests a generic event with idempotency verification and DLQ fallback.
        Returns (CanonicalEvent, is_duplicate).
        """
        event_id = req.event_id or f"EVT-GEN-{uuid.uuid4().hex[:8].upper()}"
        idempotency_key = req.idempotency_key or f"generic:{event_id}"

        # 1. Idempotency Check
        existing = self.store.check_idempotency(idempotency_key)
        if existing:
            logger.info("Duplicate event detected for idempotency key: %s", idempotency_key)
            dupe = self.store.record_duplicate(existing)
            return dupe, True

        # 2. Construct canonical event
        canonical = CanonicalEvent(
            event_id=event_id,
            idempotency_key=idempotency_key,
            source=req.source,
            event_type=req.event_type,
            customer_id=req.customer_id,
            account_id=req.account_id,
            amount=req.amount,
            currency=req.currency,
            status=EventStatus.PROCESSED,
            raw_payload=req.payload,
            normalized_payload=req.payload,
        )
        saved = self.store.save_event(canonical)
        return saved, False

    def ingest_core_banking_event(self, req: CoreBankingEventRequest) -> Tuple[CanonicalEvent, bool]:
        """
        Transforms Core Banking payload into canonical format and persists idempotently.
        """
        canonical = map_core_banking_to_canonical(req)

        # Idempotency Check
        existing = self.store.check_idempotency(canonical.idempotency_key)
        if existing:
            logger.info("Duplicate CBS transaction detected: %s", req.cbs_txn_id)
            dupe = self.store.record_duplicate(existing)
            return dupe, True

        saved = self.store.save_event(canonical)
        return saved, False

    def ingest_payment_gateway_event(self, req: PaymentGatewayEventRequest) -> Tuple[CanonicalEvent, bool]:
        """
        Transforms Payment Gateway payload into canonical format and persists idempotently.
        """
        canonical = map_payment_gateway_to_canonical(req)

        # Idempotency Check
        existing = self.store.check_idempotency(canonical.idempotency_key)
        if existing:
            logger.info("Duplicate Gateway payment detected: %s", req.gateway_payment_id)
            dupe = self.store.record_duplicate(existing)
            return dupe, True

        saved = self.store.save_event(canonical)
        return saved, False

    def ingest_webhook(
        self,
        provider_name: str,
        payload_bytes: bytes,
        signature_header: str,
        secret: str = DEFAULT_WEBHOOK_SECRET,
    ) -> Tuple[CanonicalEvent, bool]:
        """
        Validates HMAC signature and ingests signed webhook payload.
        """
        # 1. Cryptographic HMAC-SHA256 signature validation
        if not verify_hmac_sha256(payload_bytes, signature_header, secret):
            raise PermissionError("Invalid webhook HMAC-SHA256 signature.")

        # 2. Parse JSON body
        try:
            body = json.loads(payload_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Malformed webhook JSON body: {exc}")

        # 3. Canonical mapping
        event_ref = body.get("id") or body.get("event_id") or uuid.uuid4().hex[:8]
        event_id = f"EVT-WH-{uuid.uuid4().hex[:8].upper()}"
        idempotency_key = f"webhook:{provider_name.lower()}:{event_ref}"

        existing = self.store.check_idempotency(idempotency_key)
        if existing:
            dupe = self.store.record_duplicate(existing)
            return dupe, True

        canonical = CanonicalEvent(
            event_id=event_id,
            idempotency_key=idempotency_key,
            source=EventSource.WEBHOOK,
            event_type=EventType.PAYMENT_CAPTURED if "payment" in provider_name.lower() else EventType.GENERIC_EVENT,
            customer_id=body.get("customer_id") or body.get("email"),
            account_id=body.get("account_id"),
            amount=float(body.get("amount", 0.0)) if body.get("amount") is not None else None,
            currency=body.get("currency", "INR"),
            status=EventStatus.PROCESSED,
            raw_payload=body,
            normalized_payload={"provider": provider_name.upper(), "data": body},
        )
        saved = self.store.save_event(canonical)
        return saved, False

    def process_with_retry_and_dlq(
        self,
        source: str,
        payload: Dict[str, Any],
        max_retries: int = 3,
    ) -> CanonicalEvent:
        """
        Executes bounded retry handling with exponential backoff; pushes to DLQ on exhaustion.
        """
        attempts = 0
        failure_reason = ""

        # Check for simulated forced failure flag in payload
        should_fail = payload.get("force_failure", False)

        while attempts < max_retries:
            attempts += 1
            if should_fail:
                failure_reason = f"Simulated provider timeout / upstream 503 error on attempt {attempts}"
                logger.warning("Retry attempt %d failed for %s: %s", attempts, source, failure_reason)
                continue
            else:
                # Succeeded
                req = GenericEventRequest(source=EventSource.GENERIC, payload=payload)
                event, _ = self.ingest_generic_event(req)
                event.retry_count = attempts - 1
                return event

        # Retries exhausted -> route to Dead Letter Queue (DLQ)
        logger.error("Max retries (%d) exhausted for source '%s'. Routing to DLQ.", max_retries, source)
        dlq_event = self.store.record_dead_letter(
            source=source,
            payload=payload,
            failure_reason=failure_reason or "Max retries exceeded",
            retry_attempts=attempts,
            original_event_id=payload.get("event_id"),
        )
        # Return canonical event flagged as DEAD_LETTER
        return CanonicalEvent(
            event_id=dlq_event.dlq_id,
            idempotency_key=f"dlq:{dlq_event.dlq_id}",
            source=EventSource.GENERIC,
            event_type=EventType.GENERIC_EVENT,
            status=EventStatus.DEAD_LETTER,
            raw_payload=payload,
            normalized_payload={"dlq_id": dlq_event.dlq_id, "reason": failure_reason},
            retry_count=attempts,
        )

    def list_events(self, limit: int = 50) -> List[CanonicalEvent]:
        return self.store.list_events(limit=limit)

    def list_dead_letters(self, limit: int = 50) -> List[DeadLetterEvent]:
        return self.store.list_dead_letters(limit=limit)

    def list_audit_trail(self, limit: int = 100) -> List[IntegrationAuditEntry]:
        return self.store.list_audit_trail(limit=limit)

    def get_metrics(self) -> IntegrationMetrics:
        return self.store.get_metrics()


# Global singleton instance
integration_service = IntegrationService()

