"""
FinGuard AI — Phase 29: Payment Fraud Intelligence REST API Router.
Provides endpoints for payment assessment, transaction retrieval, and metrics.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from payment_fraud.models import (
    PaymentAssessmentResponse,
    PaymentEvent,
    PaymentMetrics,
)
from payment_fraud.service import payment_service

logger = logging.getLogger("finguard-payment-api")

payment_router = APIRouter(tags=["Payment Fraud Intelligence"])


@payment_router.get("/payments/health", summary="Payment Fraud Service Health Check")
def payment_health():
    """Returns the operational status of the payment fraud intelligence engine."""
    return {
        "status": "ok",
        "service": "payment_fraud_intelligence",
        "phase": "Phase-29",
        "rails": ["UPI", "IMPS", "NEFT", "RTGS", "CARD"],
        "advisory_mode": True,
    }


@payment_router.post(
    "/payments/assess",
    response_model=PaymentAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assess Payment Event Risk",
)
def assess_payment(payment: PaymentEvent) -> PaymentAssessmentResponse:
    """
    Evaluates real-time payment risk across velocity, high-value, city mismatch,
    new beneficiaries, cross-border flows, and device context.
    """
    try:
        assessment = payment_service.assess_payment(payment)
        logger.info(
            "Assessed payment %s (₹%s via %s): score %d (%s) -> action %s",
            payment.transaction_id,
            payment.amount,
            payment.payment_rail.value,
            assessment.risk_score,
            assessment.risk_level.value,
            assessment.action.value,
        )
        return assessment
    except Exception as exc:
        logger.error("Failed to assess payment %s: %s", payment.transaction_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment risk assessment error: {str(exc)}",
        )


@payment_router.get(
    "/payments/assessments/{transaction_id}",
    response_model=PaymentAssessmentResponse,
    summary="Retrieve Payment Risk Assessment",
)
def get_payment_assessment(transaction_id: str) -> PaymentAssessmentResponse:
    """Retrieves an existing payment risk assessment by transaction ID."""
    assessment = payment_service.get_assessment(transaction_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment assessment for transaction '{transaction_id}' not found.",
        )
    return assessment


@payment_router.get(
    "/payments/assessments",
    response_model=List[PaymentAssessmentResponse],
    summary="List Recent Payment Assessments",
)
def list_payment_assessments(limit: int = Query(50, ge=1, le=200)) -> List[PaymentAssessmentResponse]:
    """Lists recent payment risk assessments for operational consoles and dashboards."""
    return payment_service.list_assessments(limit=limit)


@payment_router.get(
    "/payments/metrics",
    response_model=PaymentMetrics,
    summary="Payment Risk Aggregations & KPIs",
)
def get_payment_metrics() -> PaymentMetrics:
    """Calculates operational metrics across payments, actions, and detected anomalies."""
    return payment_service.get_metrics()

