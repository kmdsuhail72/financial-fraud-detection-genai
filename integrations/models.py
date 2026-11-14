"""
FinGuard AI — Phase 31: Enterprise Data Integration Models.
Defines schemas for Core Banking, Payment Gateway adapters, Canonical Events, DLQ, and Webhooks.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EventSource(str, Enum):
    CORE_BANKING = "CORE_BANKING"
    PAYMENT_GATEWAY = "PAYMENT_GATEWAY"
    EXTERNAL_KYC = "EXTERNAL_KYC"
    EXTERNAL_AML = "EXTERNAL_AML"
    WEBHOOK = "WEBHOOK"
    GENERIC = "GENERIC"


class EventType(str, Enum):
    TRANSACTION_POSTED = "TRANSACTION_POSTED"
    ACCOUNT_UPDATED = "ACCOUNT_UPDATED"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"
    KYC_VERIFIED = "KYC_VERIFIED"
    SANCTION_MATCH = "SANCTION_MATCH"
    GENERIC_EVENT = "GENERIC_EVENT"


class EventStatus(str, Enum):
    PROCESSED = "PROCESSED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class CanonicalEvent(BaseModel):
    event_id: str = Field(..., description="Unique canonical event reference")
    idempotency_key: str = Field(..., description="Idempotent deduplication key")
    source: EventSource
    event_type: EventType
    customer_id: Optional[str] = None
    account_id: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "INR"
    status: EventStatus = EventStatus.PROCESSED
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    normalized_payload: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0

    model_config = ConfigDict(extra="allow")


class GenericEventRequest(BaseModel):
    event_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    source: EventSource = EventSource.GENERIC
    event_type: EventType = EventType.GENERIC_EVENT
    customer_id: Optional[str] = None
    account_id: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "INR"
    payload: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class CoreBankingEventRequest(BaseModel):
    cbs_txn_id: str = Field(..., description="Core Banking System Transaction ID")
    account_number: str
    customer_cif: str
    posting_date: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    txn_type: str = Field(..., description="DEBIT or CREDIT")
    channel: str = Field(default="CBS_ONLINE", description="BRANCH, ATM, NETBANKING, UPI")
    beneficiary_account: Optional[str] = None
    narration: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class PaymentGatewayEventRequest(BaseModel):
    gateway_payment_id: str = Field(..., description="Payment Gateway reference (e.g. pay_9812401)")
    order_id: str
    gateway_provider: str = Field(default="RAZORPAY", description="RAZORPAY, STRIPE, ADYEN")
    event_name: str = Field(default="payment.captured")
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_method: str = Field(default="upi", description="upi, card, netbanking")
    status: str = Field(default="captured")
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class DeadLetterEvent(BaseModel):
    dlq_id: str
    original_event_id: Optional[str] = None
    source: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    failure_reason: str
    retry_attempts: int
    failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="allow")


class IntegrationAuditEntry(BaseModel):
    audit_id: str
    event_id: Optional[str] = None
    action: str
    source: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="allow")


class IntegrationMetrics(BaseModel):
    total_events_received: int
    processed_count: int
    duplicate_count: int
    dead_letter_count: int
    cbs_events_count: int
    gateway_events_count: int
    webhook_events_count: int
    success_rate_percent: float

    model_config = ConfigDict(extra="allow")
