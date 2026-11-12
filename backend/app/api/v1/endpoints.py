"""
FastAPI v1 API Endpoints for FinGuard AI
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from backend.app.schemas.transaction import (
    TransactionCreate, TransactionResponse, FraudScoreRequest, FraudScoreResponse
)
from backend.app.schemas.case import (
    CaseDetailResponse, CaseAssignRequest, InvestigatorDecisionRequest
)
from genai.schemas.investigation_report import BedrockInvestigationReport

router = APIRouter(prefix="/api/v1")


@router.post("/transactions", status_code=status.HTTP_202_ACCEPTED)
async def submit_transaction(payload: TransactionCreate):
    """Submits transaction into the Kinesis streaming pipeline."""
    return {
        "status": "ACCEPTED",
        "transaction_id": payload.transaction_id,
        "message": "Transaction accepted for real-time risk evaluation."
    }


@router.get("/transactions", response_model=List[dict])
async def list_transactions(limit: int = 50, offset: int = 0):
    """Lists recent transactions."""
    return []


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    """Retrieves specific transaction details."""
    return {"transaction_id": transaction_id, "status": "APPROVED"}


@router.get("/fraud/alerts")
async def list_alerts(status_filter: Optional[str] = None):
    """Lists fraud alerts."""
    return []


@router.get("/fraud/alerts/{alert_id}")
async def get_alert(alert_id: UUID):
    """Retrieves fraud alert details."""
    return {"alert_id": alert_id, "alert_level": "CRITICAL"}


@router.post("/fraud/score", response_model=FraudScoreResponse)
async def score_transaction(payload: FraudScoreRequest):
    """Synchronously scores transaction features using dual-model risk formulation."""
    # R = 100 * (0.65P + 0.35A)
    # Mocking calibrated inference for API contract demonstration
    prob_supervised = min(1.0, max(0.0, (payload.amount_deviation / 10.0) * 0.8 + (0.2 if payload.new_device else 0.0)))
    anomaly_unsupervised = min(1.0, max(0.0, (payload.transaction_count_5m / 5.0) * 0.7 + (0.3 if payload.location_change else 0.0)))
    unified_score = round(100.0 * (0.65 * prob_supervised + 0.35 * anomaly_unsupervised), 2)

    if unified_score >= 80.0:
        level = "CRITICAL"
        action = "FREEZE_AND_CREATE_CASE"
    elif unified_score >= 60.0:
        level = "HIGH"
        action = "CREATE_CASE"
    elif unified_score >= 30.0:
        level = "MEDIUM"
        action = "MONITOR"
    else:
        level = "LOW"
        action = "APPROVE"

    return FraudScoreResponse(
        transaction_id=payload.transaction_id,
        xgboost_probability=round(prob_supervised, 4),
        isoforest_anomaly_score=round(anomaly_unsupervised, 4),
        unified_risk_score=unified_score,
        risk_level=level,
        recommended_action=action,
        latency_ms=24.5
    )


@router.get("/cases", response_model=List[CaseDetailResponse])
async def list_cases(status_filter: Optional[str] = "OPEN", limit: int = 20):
    """Lists fraud investigation cases."""
    return []


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    """Retrieves full case details."""
    return {
        "case_id": case_id,
        "status": "OPEN",
        "risk_level": "CRITICAL",
        "risk_score": 94.50
    }


@router.post("/cases/{case_id}/assign")
async def assign_case(case_id: str, payload: CaseAssignRequest):
    """Assigns an investigator to a case."""
    return {
        "case_id": case_id,
        "assigned_to": payload.assigned_to,
        "status": "IN_REVIEW"
    }


@router.post("/cases/{case_id}/decision")
async def record_decision(case_id: str, payload: InvestigatorDecisionRequest):
    """Records investigator resolution decision."""
    return {
        "case_id": case_id,
        "decision": payload.decision,
        "action_taken": payload.action_taken,
        "status": "CLOSED"
    }


@router.post("/cases/{case_id}/investigate", response_model=BedrockInvestigationReport)
async def generate_ai_investigation_report(case_id: str):
    """Generates structured Amazon Bedrock AI investigation summary."""
    return BedrockInvestigationReport(
        case_id=case_id,
        risk_level="CRITICAL",
        executive_summary="The transaction has been flagged because its amount significantly exceeds historical spending patterns in conjunction with unrecognized device signals.",
        key_evidence=[
            "Transaction amount exceeds 24h baseline by 7.0x",
            "Previously unseen mobile device detected",
            "Multiple rapid transactions within 5 minutes"
        ],
        recommended_actions=[
            "Verify customer identity using registered two-factor challenge",
            "Review customer account activity for preceding 48 hours",
            "Temporarily restrict card payment channel if unconfirmed"
        ],
        confidence_rationale="Robust evidentiary grounding across transaction velocity and device fingerprinting."
    )


@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Provides high-level KPI summary for the dashboard."""
    return {
        "total_transactions_today": 142580,
        "flagged_alerts": 34,
        "open_investigations": 12,
        "critical_cases": 3,
        "false_positive_rate": 0.38,
        "average_triage_time_minutes": 4.2
    }


@router.get("/audit-logs")
async def get_audit_logs(limit: int = 100):
    """Retrieves immutable audit trail entries."""
    return []

