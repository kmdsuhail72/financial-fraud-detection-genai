"""
FinGuard AI — Phase 28: Unified Customer Risk Intelligence API Router
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from customer_risk.models import (
    CustomerRiskAssessment,
    CustomerAssessmentRequest,
    CustomerRiskLevel,
)
from customer_risk.service import get_customer_risk_service

customer_risk_router = APIRouter(tags=["Unified Customer Risk Intelligence"])


@customer_risk_router.get("/risk/health")
@customer_risk_router.get("/health")
def customer_risk_health():
    """Health check endpoint for customer risk intelligence service."""
    return {
        "status": "ok",
        "service": "customer_risk_intelligence",
        "phase": "Phase-28",
        "version": "1.0.0"
    }


@customer_risk_router.post("/risk/assessments", response_model=CustomerRiskAssessment, status_code=status.HTTP_201_CREATED)
def assess_customer_risk(req: CustomerAssessmentRequest):
    """
    Assesses customer risk across 7 domains (KYC, AML, Fraud, Identity, Sanctions, PEP, Behavioral),
    applying weighted domain aggregation, coverage renormalization, and previous score tracking.
    """
    try:
        service = get_customer_risk_service()
        return service.assess_customer(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@customer_risk_router.get("/risk/assessments", response_model=List[CustomerRiskAssessment])
def list_risk_assessments(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    risk_level: Optional[CustomerRiskLevel] = Query(None, description="Filter by classification tier")
):
    """Lists customer risk assessments with optional filtering by customer ID or risk classification."""
    service = get_customer_risk_service()
    return service.list_assessments(customer_id=customer_id, risk_level=risk_level)


@customer_risk_router.get("/risk/assessments/{assessment_id}", response_model=CustomerRiskAssessment)
def get_risk_assessment(assessment_id: str):
    """Retrieves full explainable customer risk assessment record by assessment ID."""
    service = get_customer_risk_service()
    assessment = service.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found")
    return assessment


@customer_risk_router.get("/risk/customers/{customer_id}/history", response_model=List[CustomerRiskAssessment])
def get_customer_risk_history(customer_id: str):
    """Retrieves continuous risk reassessment history and trendline for a customer."""
    service = get_customer_risk_service()
    return service.get_customer_history(customer_id)
