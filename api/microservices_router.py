"""
FinGuard AI — Phase 33: Enterprise Microservices & Event-Driven Architecture Router.
Exposes APIs for transaction initiation, Saga orchestration, transactional outbox,
dead-letter queue forensics, and distributed tracing telemetry.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, status

from events.event_bus import event_bus
from events.models import (
    DeadLetterRecord,
    EventContract,
    InitiateTransactionRequest,
    MicroserviceMetrics,
    OutboxRecord,
    OutboxStatus,
    SagaInstance,
)
from events.outbox import transactional_outbox
from events.saga import saga_orchestrator
from events.service import microservices_coordinator

logger = logging.getLogger("finguard-microservices-api")

microservices_router = APIRouter(prefix="/microservices", tags=["Microservices & Event-Driven Architecture"])


@microservices_router.get("/health", summary="Microservices Architecture Health Check")
def microservices_health():
    """Returns the operational status of the event-driven microservices architecture."""
    return {
        "status": "healthy",
        "service": "event_driven_microservices",
        "phase": "Phase-33",
        "architecture": {
            "services": [
                "transaction-service",
                "fraud-scoring-service",
                "ledger-service",
                "notification-service",
            ],
            "event_bus": "EventBridge-compatible in-memory bus",
            "patterns": [
                "transactional_outbox",
                "saga_orchestration_forward_and_compensate",
                "dead_letter_queue_redrive",
                "idempotency_deduplication",
                "distributed_tracing_correlation_causation",
            ],
        },
    }


@microservices_router.post(
    "/transactions",
    summary="Initiate Transaction via Event-Driven Outbox & Saga",
)
def initiate_transaction(
    req: InitiateTransactionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Initiates transaction workflow:
    1. Checks Idempotency-Key
    2. Persists outbox record atomically
    3. Emits transaction.initiated.v1 event
    4. Orchestrates forward Saga steps with reverse compensation on failure
    """
    result = microservices_coordinator.process_transaction(req, idempotency_key=idempotency_key)
    return result


@microservices_router.post(
    "/saga/execute",
    summary="Execute Distributed Transaction Saga Directly",
)
def execute_saga(
    transaction_id: str = Query(..., description="Unique transaction ID"),
    customer_id: str = Query(..., description="Customer ID"),
    amount: float = Query(..., description="Transaction amount in INR"),
    force_failure_at_step: Optional[str] = Query(None, description="Step to force failure for testing compensation"),
):
    """Executes a Saga with forward actions or reverse-order compensation."""
    saga = saga_orchestrator.execute_transaction_saga(
        transaction_id=transaction_id,
        customer_id=customer_id,
        amount=amount,
        force_failure_at_step=force_failure_at_step,
    )
    return saga


@microservices_router.get(
    "/saga/{saga_id}",
    response_model=SagaInstance,
    summary="Retrieve Saga Execution State",
)
def get_saga_state(saga_id: str) -> SagaInstance:
    """Returns detailed state, executed steps, and compensation logs for a Saga."""
    saga = saga_orchestrator.get_saga(saga_id)
    if not saga:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saga with ID '{saga_id}' not found.",
        )
    return saga


@microservices_router.get(
    "/sagas",
    response_model=List[SagaInstance],
    summary="List All Saga Workflows",
)
def list_sagas() -> List[SagaInstance]:
    """Returns all recorded Saga instances."""
    return saga_orchestrator.list_sagas()


@microservices_router.get(
    "/outbox",
    response_model=List[OutboxRecord],
    summary="Inspect Transactional Outbox",
)
def list_outbox_records(
    status_filter: Optional[OutboxStatus] = Query(None, alias="status"),
) -> List[OutboxRecord]:
    """Returns outbox records filtered by PENDING, PUBLISHED, or FAILED status."""
    return transactional_outbox.list_records(status_filter)


@microservices_router.post(
    "/outbox/flush",
    summary="Flush Pending Outbox Events to Event Bus",
)
def flush_outbox():
    """Manually flushes pending outbox records to the event bus."""
    published = transactional_outbox.flush(event_bus)
    return {
        "status": "flushed",
        "events_published": published,
        "pending_remaining": transactional_outbox.get_pending_count(),
    }


@microservices_router.get(
    "/dlq",
    response_model=List[DeadLetterRecord],
    summary="List Dead-Letter Queue Failed Events",
)
def list_dlq_records() -> List[DeadLetterRecord]:
    """Inspects failed events that exhausted bounded retries."""
    return event_bus.get_dlq_records()


@microservices_router.post(
    "/dlq/replay/{dlq_id}",
    summary="Replay Dead-Letter Queue Message",
)
def replay_dlq_message(dlq_id: str):
    """Replays a DLQ message through the Event Bus."""
    replayed = event_bus.replay_dlq(dlq_id)
    if not replayed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to replay DLQ message '{dlq_id}' or already replayed.",
        )
    return {"status": "replayed", "dlq_id": dlq_id}


@microservices_router.get(
    "/events",
    response_model=List[EventContract],
    summary="Query Event Bus Log for Distributed Tracing",
)
def list_events(
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
) -> List[EventContract]:
    """Retrieves chronological event log with correlation and causation tracking."""
    return event_bus.get_event_log(correlation_id=correlation_id)


@microservices_router.get(
    "/metrics",
    response_model=MicroserviceMetrics,
    summary="Microservices Operational Metrics & Telemetry",
)
def get_metrics() -> MicroserviceMetrics:
    """Aggregates throughput, saga completions/compensations, outbox backlog, and DLQ depth."""
    return microservices_coordinator.get_metrics()
