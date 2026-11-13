"""Phase 20 — Real-Time Fraud Decision Engine REST API Router."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from decision.models import (
    DecisionRequest,
    FraudClassification,
    FraudDecisionResponse,
    RiskPolicyConfig,
    RiskPriority,
)
from decision.service import DecisionService, get_decision_service
from security.audit import audit_logger

logger = logging.getLogger("finguard-decision-api")

decision_router = APIRouter(prefix="/decisions", tags=["Enterprise Fraud Decision Engine & Risk Orchestration"])


def get_actor_info(request: Request) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from security.auth import decode_and_validate_token
            token = auth_header.split(" ")[1]
            user = decode_and_validate_token(token)
            return {"sub": user.sub, "email": user.email, "roles": [r.value for r in user.roles]}
        except Exception:
            pass
    return {"sub": "usr-analyst-local", "email": "analyst@finguard.internal", "roles": ["Analyst"]}


@decision_router.get("/health")
def get_decision_engine_health():
    """Health check endpoint for real-time fraud decision orchestration."""
    return {
        "status": "HEALTHY",
        "phase": "Phase 20 — Real-Time Fraud Decision Engine",
        "service": "risk_fusion_orchestrator",
    }


@decision_router.post("", response_model=FraudDecisionResponse)
@decision_router.post("/", response_model=FraudDecisionResponse, include_in_schema=False)
def create_fraud_decision(
    payload: DecisionRequest,
    request: Request,
    service: DecisionService = Depends(get_decision_service),
):
    """
    Evaluates multi-signal telemetry (ML, UEBA, Graph, Temporal, Threat Intel) to reach an orchestrated fraud decision.
    Tested via: curl -X POST http://127.0.0.1:8010/decisions -H "Content-Type: application/json" --data @examples/decision_request.json
    """
    decision = service.evaluate_transaction(payload)

    actor = get_actor_info(request)
    audit_logger.log(
        actor_sub=actor["sub"],
        actor_email=actor["email"],
        actor_roles=actor["roles"],
        action="decision:evaluate_transaction",
        resource_type="TRANSACTION",
        resource_id=payload.transaction_id,
        status="SUCCESS",
        details={
            "decision_id": decision.decision_id,
            "composite_score": decision.composite_risk_score,
            "priority": decision.priority.value,
            "action": decision.recommended_action.value,
        },
    )
    return decision


@decision_router.get("", response_model=List[FraudDecisionResponse])
@decision_router.get("/", response_model=List[FraudDecisionResponse], include_in_schema=False)
def list_fraud_decisions(
    priority: Optional[RiskPriority] = Query(None, description="Filter by priority: P0, P1, P2, P3"),
    classification: Optional[FraudClassification] = Query(None, description="Filter by classification: LOW, MEDIUM, HIGH, CRITICAL"),
    limit: int = Query(50, ge=1, le=200),
    service: DecisionService = Depends(get_decision_service),
):
    """Lists past evaluated decisions with optional priority and risk tier filtering."""
    return service.list_decisions(priority=priority, classification=classification, limit=limit)


@decision_router.get("/policies/active", response_model=RiskPolicyConfig)
def get_active_risk_policy(
    service: DecisionService = Depends(get_decision_service),
):
    """Retrieves active risk policy thresholds and normalized signal weights."""
    return service.get_active_policy()


@decision_router.put("/policies/active", response_model=RiskPolicyConfig)
def update_active_risk_policy(
    payload: RiskPolicyConfig,
    request: Request,
    service: DecisionService = Depends(get_decision_service),
):
    """Dynamically updates active risk policy thresholds and signal weights."""
    updated = service.update_active_policy(payload)

    actor = get_actor_info(request)
    audit_logger.log(
        actor_sub=actor["sub"],
        actor_email=actor["email"],
        actor_roles=actor["roles"],
        action="decision:update_policy",
        resource_type="POLICY",
        resource_id=payload.policy_id,
        status="SUCCESS",
        details={"version": payload.policy_version, "weights": payload.weights},
    )
    return updated


@decision_router.get("/{decision_id}", response_model=FraudDecisionResponse)
def get_fraud_decision_by_id(
    decision_id: str,
    service: DecisionService = Depends(get_decision_service),
):
    """Retrieves an existing fraud decision by unique decision reference."""
    decision = service.get_decision(decision_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fraud decision '{decision_id}' not found.",
        )
    return decision

