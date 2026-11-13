"""FastAPI Router for Enterprise Security Analytics & UEBA (Phase 14)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from security.auth import AuthenticatedUser
from security.audit import audit_logger
from security.dependencies import require_permission, require_roles
from security.roles import Permission, Role
from ueba.entity_analytics import UEBAEntityAnalytics
from ueba.models import (
    BehavioralAnomalyResult,
    CorrelateRiskRequest,
    EntityRiskLevel,
    FraudThreatCorrelation,
    PeerGroup,
    ScoreEventRequest,
    UserEntityProfile,
)

ueba_router = APIRouter(prefix="/ueba", tags=["User & Entity Behavior Analytics (UEBA)"])

analytics_engine = UEBAEntityAnalytics()


@ueba_router.get("/metrics")
def get_ueba_metrics(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
) -> Dict[str, Any]:
    """Retrieves high-level behavioral risk metrics across the entity population. Requires 'cases:view'."""
    return analytics_engine.get_overview_metrics()


@ueba_router.get("/entities", response_model=List[UserEntityProfile])
def list_entities(
    peer_group: Optional[PeerGroup] = Query(None, description="Filter by cohort/peer group"),
    risk_level: Optional[EntityRiskLevel] = Query(None, description="Filter by risk classification"),
    min_risk: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Lists behavioral profiles for users and entities. Requires 'cases:view'."""
    return analytics_engine.profile_store.list_profiles(
        peer_group=peer_group,
        risk_level=risk_level,
        min_risk=min_risk,
        limit=limit,
        offset=offset,
    )


@ueba_router.get("/entities/{entity_id}", response_model=UserEntityProfile)
def get_entity_profile(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves detailed behavioral baseline and current risk posture for a single entity."""
    profile = analytics_engine.profile_store.get_profile(entity_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Behavioral profile for entity '{entity_id}' not found.",
        )
    return profile


@ueba_router.post("/score", response_model=BehavioralAnomalyResult)
def score_event(
    request: ScoreEventRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR, Role.ANALYST])),
):
    """Evaluates an entity event against its baseline using feature engineering, rules, and Isolation Forest."""
    result = analytics_engine.score_event(request)

    if result.is_anomaly:
        audit_logger.log(
            actor_sub=current_user.sub,
            actor_email=current_user.email,
            actor_roles=current_user.roles,
            action="ueba:anomaly_detected",
            resource_type="ENTITY",
            resource_id=request.entity_id,
            status="WARNING",
            details={
                "anomaly_id": result.anomaly_id,
                "score": result.anomaly_score,
                "rule_flags": result.rule_flags,
            },
        )
    return result


@ueba_router.post("/correlate", response_model=FraudThreatCorrelation)
def correlate_risk(
    request: CorrelateRiskRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR, Role.ANALYST])),
):
    """Fuses UEBA anomaly scores with ML fraud probability, IOC threat scores, and cloud findings."""
    correlation = analytics_engine.correlate_event(request)

    if correlation.risk_level in (EntityRiskLevel.HIGH, EntityRiskLevel.CRITICAL):
        audit_logger.log(
            actor_sub=current_user.sub,
            actor_email=current_user.email,
            actor_roles=current_user.roles,
            action="ueba:high_risk_correlation",
            resource_type="ENTITY",
            resource_id=request.entity_id,
            status="ALERT",
            details={
                "blended_risk_score": correlation.blended_risk_score,
                "signals": correlation.correlated_signals,
            },
        )
    return correlation
