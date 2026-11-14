"""
FinGuard AI — Phase 33: Enterprise Microservices & Event-Driven Architecture Models.
Defines versioned event contracts, transactional outbox entities, Saga states, and DLQ models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    TRANSACTION_INITIATED = "transaction.initiated.v1"
    TRANSACTION_SCORED = "fraud.scored.v1"
    TRANSACTION_APPROVED = "transaction.approved.v1"
    TRANSACTION_REJECTED = "transaction.rejected.v1"
    HOLD_PLACED = "account.hold.placed.v1"
    HOLD_RELEASED = "account.hold.released.v1"
    NOTIFICATION_SENT = "notification.sent.v1"
    SAGA_COMPENSATED = "saga.compensation.completed.v1"


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class SagaStatus(str, Enum):
    STARTED = "STARTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"


class EventContract(BaseModel):
    """
    Standard CloudEvents / EventBridge compliant event contract.
    Maintains distributed tracing context: trace_id, correlation_id, causation_id.
    """
    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    event_type: str = Field(..., description="Versioned event name e.g. transaction.initiated.v1")
    version: str = "1.0.0"
    source: str = Field(..., description="Service boundary emitting the event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str = Field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:8]}")
    causation_id: Optional[str] = None
    tenant_id: str = "tenant-alpha"
    payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class OutboxRecord(BaseModel):
    """
    Transactional Outbox entry stored alongside the business entity to ensure
    dual-write consistency without two-phase commit (2PC).
    """
    outbox_id: str = Field(default_factory=lambda: f"obx-{uuid.uuid4().hex[:8]}")
    aggregate_type: str = "Transaction"
    aggregate_id: str
    event: EventContract
    status: OutboxStatus = OutboxStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class DeadLetterRecord(BaseModel):
    """
    DLQ captured message after retry exhaustion for post-mortem forensics and replay.
    """
    dlq_id: str = Field(default_factory=lambda: f"dlq-{uuid.uuid4().hex[:8]}")
    original_event: EventContract
    failure_reason: str
    retry_attempts: int
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    replayed: bool = False
    replayed_at: Optional[datetime] = None

    model_config = ConfigDict(extra="allow")


class SagaStep(BaseModel):
    step_name: str
    service_name: str
    status: str = "PENDING"  # PENDING, EXECUTED, COMPENSATED, FAILED
    forward_action: str
    compensation_action: str
    executed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None
    error: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class SagaInstance(BaseModel):
    """
    State tracking for a distributed Saga workflow across microservices.
    """
    saga_id: str = Field(default_factory=lambda: f"saga-{uuid.uuid4().hex[:8]}")
    saga_type: str = "TransactionProcessingSaga"
    transaction_id: str
    correlation_id: str
    status: SagaStatus = SagaStatus.STARTED
    current_step: int = 0
    steps: List[SagaStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    compensation_log: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class MicroserviceMetrics(BaseModel):
    total_events_published: int
    total_events_consumed: int
    pending_outbox_count: int
    dead_letter_queue_count: int
    sagas_completed: int
    sagas_compensated: int
    idempotent_deduplications: int
    service_health: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class InitiateTransactionRequest(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    rail: str = "UPI"
    force_failure_at_step: Optional[str] = None  # Used for testing saga compensation

    model_config = ConfigDict(extra="allow")
