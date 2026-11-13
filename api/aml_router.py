"""
FinGuard AI — Phase 24 Anti-Money Laundering (AML) REST API Router.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict

from aml.models import (
    AMLAlert,
    AMLCaseStatus,
    AMLInvestigationCase,
    AMLMetricsResponse,
    AMLTransaction,
    CustomerRiskProfile,
    CustomerRiskTier,
    SARInvestigationDraft,
)
from aml.service import AMLService, get_aml_service

logger = logging.getLogger("finguard-aml-api")

aml_router = APIRouter(prefix="/aml", tags=["Enterprise AML Transaction Monitoring & Customer Risk Profiling"])


def get_actor_from_request(request: Request) -> Dict[str, Any]:
    """Extract authenticated actor or provide safe operational fallback."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        try:
            from security.dependencies import jwt_verifier
            token = auth_header[7:].strip()
            user = jwt_verifier.verify_token(token)
            roles = [r.value if hasattr(r, "value") else str(r) for r in user.roles]
            return {"sub": user.sub, "email": user.email, "roles": roles}
        except Exception:
            pass
    return {"sub": "usr-aml-officer", "email": "aml.officer@finguard.internal", "roles": ["Analyst", "Investigator"]}


# ==========================================
# Health Endpoint
# ==========================================
@aml_router.get("/health")
def get_aml_health():
    """Health check endpoint for AML transaction monitoring engine."""
    return {
        "status": "HEALTHY",
        "phase": "Phase 24 — Enterprise AML Transaction Monitoring & Customer Risk Profiling",
        "service": "aml_transaction_monitor",
    }


# ==========================================
# AML Monitoring & Customer Profiling
# ==========================================
class TransactionMonitorResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    transaction_id: str
    customer_id: str
    alerts_triggered: List[AMLAlert]
    case_id: Optional[str] = None
    customer_risk_tier: CustomerRiskTier
    customer_risk_score: int
    message: str


@aml_router.post("/monitor/transaction", response_model=TransactionMonitorResponse)
def monitor_transaction(
    payload: AMLTransaction,
    request: Request,
    service: AMLService = Depends(get_aml_service),
):
    """
    Monitor incoming transaction against AML rules (Large Cash, Structuring, Rapid Inflow/Outflow, Velocity).
    Updates customer risk profile and auto-creates/escalates AML investigation case if suspicious.
    """
    alerts, case, profile = service.process_transaction(payload)
    msg = f"Flagged {len(alerts)} suspicious AML pattern(s)" if alerts else "Transaction cleared AML rules"

    return TransactionMonitorResponse(
        transaction_id=payload.transaction_id,
        customer_id=payload.customer_id,
        alerts_triggered=alerts,
        case_id=case.case_id if case else None,
        customer_risk_tier=profile.risk_tier,
        customer_risk_score=profile.risk_score,
        message=msg,
    )


@aml_router.get("/customers/{customer_id}", response_model=CustomerRiskProfile)
def get_customer_risk_profile(
    customer_id: str,
    service: AMLService = Depends(get_aml_service),
):
    """Retrieve explainable customer AML risk profile, score, and risk factors."""
    profile = service.get_customer_profile(customer_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer '{customer_id}' not found.",
        )
    return profile


# ==========================================
# AML Investigation Cases
# ==========================================
@aml_router.get("/cases", response_model=List[AMLInvestigationCase])
def list_aml_cases(
    status_filter: Optional[AMLCaseStatus] = Query(None, alias="status", description="Filter by case status"),
    risk_tier: Optional[CustomerRiskTier] = Query(None, description="Filter by customer risk tier"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    service: AMLService = Depends(get_aml_service),
):
    """List AML investigation cases with optional filtering."""
    return service.list_cases(status=status_filter, risk_tier=risk_tier, customer_id=customer_id)


@aml_router.get("/cases/{case_id}", response_model=AMLInvestigationCase)
def get_aml_case_detail(
    case_id: str,
    service: AMLService = Depends(get_aml_service),
):
    """Retrieve single AML case with alerts, investigation notes, and activity timeline."""
    case = service.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AML case '{case_id}' not found.",
        )
    return case


class CaseStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: AMLCaseStatus
    notes: Optional[str] = None
    updated_by: Optional[str] = "aml.analyst"


@aml_router.post("/cases/{case_id}/status", response_model=AMLInvestigationCase)
def update_case_status(
    case_id: str,
    payload: CaseStatusUpdateRequest,
    request: Request,
    service: AMLService = Depends(get_aml_service),
):
    """Transition AML case status (e.g. NEW -> UNDER_INVESTIGATION -> ESCALATED)."""
    actor = get_actor_from_request(request)
    updater = payload.updated_by or actor.get("email") or "aml.analyst"
    try:
        return service.update_case_status(case_id, payload.status, actor=updater, notes=payload.notes)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AML case '{case_id}' not found.",
        )


class AddCaseNoteRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    author: Optional[str] = "aml.analyst"
    content: str


@aml_router.post("/cases/{case_id}/notes", response_model=AMLInvestigationCase)
def add_case_note(
    case_id: str,
    payload: AddCaseNoteRequest,
    request: Request,
    service: AMLService = Depends(get_aml_service),
):
    """Add investigator note to AML case timeline."""
    actor = get_actor_from_request(request)
    author = payload.author or actor.get("email") or "aml.analyst"
    try:
        return service.add_case_note(case_id, author=author, content=payload.content)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AML case '{case_id}' not found.",
        )


class SARDraftRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prepared_by: Optional[str] = "aml.investigator"
    recommended_disposition: str = "RECOMMEND_SAR_FILING"


@aml_router.post("/cases/{case_id}/sar-draft", response_model=SARInvestigationDraft)
def generate_sar_investigation_draft(
    case_id: str,
    request: Request,
    payload: Optional[SARDraftRequest] = None,
    service: AMLService = Depends(get_aml_service),
):
    """Compile formal Suspicious Activity Report (SAR/STR) internal investigation draft."""
    actor = get_actor_from_request(request)
    author = (payload.prepared_by if payload else None) or actor.get("email") or "aml.investigator"
    disp = (payload.recommended_disposition if payload else None) or "RECOMMEND_SAR_FILING"
    try:
        return service.generate_sar_draft(case_id, prepared_by=author, disposition=disp)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AML case '{case_id}' not found.",
        )


# ==========================================
# Metrics Endpoint
# ==========================================
@aml_router.get("/metrics", response_model=AMLMetricsResponse)
def get_aml_metrics(
    service: AMLService = Depends(get_aml_service),
):
    """Retrieve operational AML monitoring metrics and customer risk tier distribution."""
    return service.get_metrics()

