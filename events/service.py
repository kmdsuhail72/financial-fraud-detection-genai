"""
FinGuard AI — Phase 33: Enterprise Microservices Coordination Service.
Coordinates the Transaction Service, Fraud-Scoring Service, Outbox, Event Bus, and Saga.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from events.event_bus import EventBus, event_bus
from events.idempotency import IdempotencyEngine, idempotency_engine
from events.models import (
    EventContract,
    EventType,
    InitiateTransactionRequest,
    MicroserviceMetrics,
    OutboxRecord,
    SagaInstance,
    SagaStatus,
)
from events.outbox import TransactionalOutbox, transactional_outbox
from events.saga import SagaOrchestrator, saga_orchestrator

logger = logging.getLogger("finguard-microservices")


class MicroservicesCoordinator:
    def __init__(
        self,
        bus: EventBus = event_bus,
        outbox: TransactionalOutbox = transactional_outbox,
        saga: SagaOrchestrator = saga_orchestrator,
        idempotency: IdempotencyEngine = idempotency_engine,
    ):
        self.bus = bus
        self.outbox = outbox
        self.saga = saga
        self.idempotency = idempotency
        self._consumed_count: int = 0
        self._init_subscribers()

    def _init_subscribers(self):
        """Wires in-memory microservice listeners to the event bus."""
        def on_any_event(evt: EventContract):
            self._consumed_count += 1
            logger.info("Microservice boundary received event: %s (%s)", evt.event_type, evt.event_id)

        self.bus.subscribe("*", on_any_event)

    def process_transaction(
        self,
        req: InitiateTransactionRequest,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Coordinates full microservice event-driven transaction processing:
        1. Idempotency deduplication check
        2. Transactional Outbox persistence (dual-write prevention)
        3. Event Bus asynchronous dispatch
        4. Distributed Saga orchestration (forward execution or reverse compensation)
        """
        dedup_key = idempotency_key or f"txn-idem:{req.transaction_id}"
        is_dup, cached = self.idempotency.check_and_set(dedup_key)
        if is_dup and cached is not None:
            logger.info("Idempotent duplicate detected for key %s. Returning cached state.", dedup_key)
            return {
                "status": "cached",
                "idempotent_replay": True,
                "data": cached,
            }

        # 1. Create TransactionInitiated Event Contract
        init_event = EventContract(
            event_type=EventType.TRANSACTION_INITIATED.value,
            source="transaction-service",
            tenant_id="tenant-alpha",
            payload={
                "transaction_id": req.transaction_id,
                "customer_id": req.customer_id,
                "amount": req.amount,
                "currency": req.currency,
                "rail": req.rail,
            },
        )

        # 2. Persist in Transactional Outbox
        outbox_entry = self.outbox.record_event(
            aggregate_type="Transaction",
            aggregate_id=req.transaction_id,
            event=init_event,
        )

        # 3. Flush Outbox to EventBus
        self.outbox.flush(self.bus)

        # 4. Trigger Distributed Saga
        saga_result = self.saga.execute_transaction_saga(
            transaction_id=req.transaction_id,
            customer_id=req.customer_id,
            amount=req.amount,
            correlation_id=init_event.correlation_id,
            force_failure_at_step=req.force_failure_at_step,
        )

        response_payload = {
            "transaction_id": req.transaction_id,
            "status": "COMPLETED" if saga_result.status == SagaStatus.COMPLETED else "COMPENSATED",
            "saga_id": saga_result.saga_id,
            "correlation_id": init_event.correlation_id,
            "outbox_id": outbox_entry.outbox_id,
            "saga_status": saga_result.status.value,
            "steps_executed": len([s for s in saga_result.steps if s.status == "EXECUTED"]),
            "compensation_log": saga_result.compensation_log,
            "error": saga_result.error,
        }

        # Store in idempotency cache
        self.idempotency.store_result(dedup_key, response_payload)

        return {
            "status": "success" if saga_result.status == SagaStatus.COMPLETED else "compensated",
            "idempotent_replay": False,
            "data": response_payload,
        }

    def get_metrics(self) -> MicroserviceMetrics:
        sagas = self.saga.list_sagas()
        completed = sum(1 for s in sagas if s.status == SagaStatus.COMPLETED)
        compensated = sum(1 for s in sagas if s.status == SagaStatus.COMPENSATED)

        return MicroserviceMetrics(
            total_events_published=len(self.bus.get_event_log()),
            total_events_consumed=self._consumed_count,
            pending_outbox_count=self.outbox.get_pending_count(),
            dead_letter_queue_count=len(self.bus.get_dlq_records()),
            sagas_completed=completed,
            sagas_compensated=compensated,
            idempotent_deduplications=self.idempotency.deduplication_count,
            service_health={
                "transaction_service": "healthy",
                "fraud_scoring_service": "healthy",
                "ledger_service": "healthy",
                "notification_service": "healthy",
                "event_bus": "active",
                "transactional_outbox": "active",
            },
        )

    def reset(self):
        """Resets in-memory state for clean test isolation."""
        self.bus.clear()
        self.outbox.clear()
        self.saga.clear()
        self.idempotency.clear()
        self._consumed_count = 0


# Global singleton coordinator
microservices_coordinator = MicroservicesCoordinator()
