"""
FinGuard AI — Phase 31: Data Integration Adapters & Webhook Verification.
Transforms disparate core banking and payment gateway payloads into canonical event structures
and performs cryptographic HMAC-SHA256 webhook verification.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import Tuple

from integrations.models import (
    CanonicalEvent,
    CoreBankingEventRequest,
    EventSource,
    EventStatus,
    EventType,
    PaymentGatewayEventRequest,
)

DEFAULT_WEBHOOK_SECRET = "finguard-secret-webhook-key-2026"


def verify_hmac_sha256(payload_bytes: bytes, signature_header: str, secret: str = DEFAULT_WEBHOOK_SECRET) -> bool:
    """
    Verifies that the incoming webhook payload matches the HMAC-SHA256 signature.
    Supports signatures formatted bare or with 'sha256=' prefix.
    """
    if not signature_header:
        return False

    clean_sig = signature_header.strip()
    if clean_sig.startswith("sha256="):
        clean_sig = clean_sig.split("=", 1)[1]

    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.lower(), clean_sig.lower())


def map_core_banking_to_canonical(req: CoreBankingEventRequest) -> CanonicalEvent:
    """
    Normalizes a Core Banking System (CBS) transaction into FinGuard AI's canonical event schema.
    """
    event_id = f"EVT-CBS-{uuid.uuid4().hex[:8].upper()}"
    idempotency_key = f"cbs:{req.cbs_txn_id}"

    normalized = {
        "cbs_transaction_id": req.cbs_txn_id,
        "account_id": req.account_number,
        "customer_id": req.customer_cif,
        "amount": req.amount,
        "currency": req.currency,
        "transaction_type": req.txn_type.upper(),
        "channel": req.channel.upper(),
        "beneficiary_account": req.beneficiary_account,
        "narration": req.narration,
        "posting_date": req.posting_date or datetime.now(timezone.utc).isoformat(),
        "raw_metadata": req.metadata,
    }

    return CanonicalEvent(
        event_id=event_id,
        idempotency_key=idempotency_key,
        source=EventSource.CORE_BANKING,
        event_type=EventType.TRANSACTION_POSTED,
        customer_id=req.customer_cif,
        account_id=req.account_number,
        amount=req.amount,
        currency=req.currency,
        status=EventStatus.PROCESSED,
        raw_payload=req.model_dump(),
        normalized_payload=normalized,
    )


def map_payment_gateway_to_canonical(req: PaymentGatewayEventRequest) -> CanonicalEvent:
    """
    Normalizes a payment gateway webhook / API payload into FinGuard AI's canonical event schema.
    """
    event_id = f"EVT-GW-{uuid.uuid4().hex[:8].upper()}"
    idempotency_key = f"gateway:{req.gateway_provider.lower()}:{req.gateway_payment_id}"

    # Map gateway event names to canonical event types
    name_lower = req.event_name.lower()
    if "captured" in name_lower or "success" in name_lower:
        canonical_type = EventType.PAYMENT_CAPTURED
    elif "authorized" in name_lower:
        canonical_type = EventType.PAYMENT_AUTHORIZED
    elif "failed" in name_lower:
        canonical_type = EventType.PAYMENT_FAILED
    elif "refund" in name_lower:
        canonical_type = EventType.PAYMENT_REFUNDED
    else:
        canonical_type = EventType.PAYMENT_CAPTURED

    normalized = {
        "gateway_payment_id": req.gateway_payment_id,
        "order_id": req.order_id,
        "provider": req.gateway_provider.upper(),
        "amount": req.amount,
        "currency": req.currency,
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "payment_method": req.payment_method.lower(),
        "gateway_status": req.status,
        "error_code": req.error_code,
        "raw_metadata": req.metadata,
    }

    return CanonicalEvent(
        event_id=event_id,
        idempotency_key=idempotency_key,
        source=EventSource.PAYMENT_GATEWAY,
        event_type=canonical_type,
        customer_id=req.customer_email or req.customer_phone,
        account_id=req.order_id,
        amount=req.amount,
        currency=req.currency,
        status=EventStatus.PROCESSED,
        raw_payload=req.model_dump(),
        normalized_payload=normalized,
    )
