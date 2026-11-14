"""
FinGuard AI — Phase 31: Data Integrations REST API Router.
Provides endpoints for Core Banking, Payment Gateway adapters, signed webhooks, DLQ, and audit history.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from integrations.models import (
    CanonicalEvent,
    CoreBankingEventRequest,
    DeadLetterEvent,
    GenericEventRequest,
    IntegrationAuditEntry,
    IntegrationMetrics,
    PaymentGatewayEventRequest,
)
from integrations.service import integration_service

logger = logging.getLogger("finguard-integrations-api")

integrations_router = APIRouter(tags=["Enterprise Data Integration & Banking APIs"])


@integrations_router.get("/integrations/health", summary="Data Integration Service Health Check")
def integrations_health():
    """Returns operational status of the Enterprise Data Integration layer."""
    return {
        "status": "ok",
        "service": "data_integration",
        "phase": "Phase-31",
        "connectors": ["core_banking", "payment_gateway", "signed_webhooks"],
        "idempotency_enabled": True,
        "dlq_enabled": True,
    }


@integrations_router.post(
    "/integrations/events",
    response_model=CanonicalEvent,
    status_code=status.HTTP_201_CREATED,
    summary="Generic Event Ingestion",
)
def ingest_generic_event(req: GenericEventRequest) -> CanonicalEvent:
    """Ingests a generic event into the canonical ingestion pipeline with idempotency checking."""
    try:
        event, is_dupe = integration_service.ingest_generic_event(req)
        return event
    except Exception as exc:
        logger.error("Failed to ingest event: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@integrations_router.post(
    "/integrations/core-banking/events",
    response_model=CanonicalEvent,
    status_code=status.HTTP_201_CREATED,
    summary="Core Banking System (CBS) Adapter Ingestion",
)
def ingest_core_banking(req: CoreBankingEventRequest) -> CanonicalEvent:
    """Transforms and ingests CBS account and transaction events."""
    try:
        event, is_dupe = integration_service.ingest_core_banking_event(req)
        return event
    except Exception as exc:
        logger.error("Failed to ingest CBS event: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@integrations_router.post(
    "/integrations/payment-gateway/events",
    response_model=CanonicalEvent,
    status_code=status.HTTP_201_CREATED,
    summary="Payment Gateway Adapter Ingestion",
)
def ingest_payment_gateway(req: PaymentGatewayEventRequest) -> CanonicalEvent:
    """Transforms and ingests payment lifecycle events from Razorpay, Stripe, Adyen, etc."""
    try:
        event, is_dupe = integration_service.ingest_payment_gateway_event(req)
        return event
    except Exception as exc:
        logger.error("Failed to ingest Payment Gateway event: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@integrations_router.post(
    "/integrations/webhooks/{provider_name}",
    response_model=CanonicalEvent,
    status_code=status.HTTP_200_OK,
    summary="Signed Webhook Intake with HMAC-SHA256 Verification",
)
async def ingest_webhook(
    provider_name: str,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
) -> CanonicalEvent:
    """
    Ingests signed webhook payload from external providers with HMAC-SHA256 signature verification.
    Accepts X-Signature or X-Hub-Signature-256 headers.
    """
    signature = x_signature or x_hub_signature_256
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required HMAC signature header (X-Signature or X-Hub-Signature-256).",
        )

    raw_body = await request.body()
    try:
        event, is_dupe = integration_service.ingest_webhook(
            provider_name=provider_name,
            payload_bytes=raw_body,
            signature_header=signature,
        )
        return event
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Webhook processing error for %s: %s", provider_name, exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@integrations_router.get(
    "/integrations/events",
    response_model=List[CanonicalEvent],
    summary="List Ingested Canonical Events",
)
def list_canonical_events(limit: int = Query(50, ge=1, le=200)) -> List[CanonicalEvent]:
    """Retrieves list of canonical events recently ingested across connectors."""
    return integration_service.list_events(limit=limit)


@integrations_router.get(
    "/integrations/dead-letters",
    response_model=List[DeadLetterEvent],
    summary="List Dead-Letter Queue (DLQ) Failed Events",
)
def list_dead_letters(limit: int = Query(50, ge=1, le=200)) -> List[DeadLetterEvent]:
    """Retrieves failed events routed to DLQ after retry exhaustion."""
    return integration_service.list_dead_letters(limit=limit)


@integrations_router.get(
    "/integrations/audit",
    response_model=List[IntegrationAuditEntry],
    summary="List Integration Audit Trail",
)
def list_integration_audit(limit: int = Query(100, ge=1, le=500)) -> List[IntegrationAuditEntry]:
    """Retrieves chronological audit events across data connectors."""
    return integration_service.list_audit_trail(limit=limit)


@integrations_router.get(
    "/integrations/metrics",
    response_model=IntegrationMetrics,
    summary="Data Integration Metrics & Gateway KPIs",
)
def get_integration_metrics() -> IntegrationMetrics:
    """Aggregates ingestion volumes, duplicate rates, DLQ counts, and success ratios."""
    return integration_service.get_metrics()

