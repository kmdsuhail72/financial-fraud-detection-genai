"""FastAPI Router for Enterprise Threat Intelligence, IOC Enrichment & MITRE ATT&CK (Phase 13)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from security.auth import AuthenticatedUser
from security.audit import audit_logger
from security.dependencies import require_permission, require_roles
from security.roles import Permission, Role
from threat_intel.mitre_mapper import MITREMapper
from threat_intel.models import (
    AnalystFeedback,
    AnalystVerdict,
    IOCEnrichmentRequest,
    IOCEnrichmentResponse,
    IOCRecord,
    MITRETechnique,
    ThreatHuntingRule,
    ThreatHuntResult,
)
from threat_intel.store import threat_intel_store

threat_intel_router = APIRouter(prefix="/threat-intel", tags=["Threat Intelligence & MITRE ATT&CK Mapping"])


class SubmitFeedbackRequest(BaseModel):
    ioc_id: str = Field(..., json_schema_extra={"example": "ioc-ipv4-1985110042"})
    verdict: AnalystVerdict = Field(..., json_schema_extra={"example": "TRUE_POSITIVE"})
    notes: Optional[str] = Field(None, json_schema_extra={"example": "Confirmed malicious proxy traffic from botnet node."})
    confidence_adjustment: Optional[float] = Field(None, ge=-1.0, le=1.0)


class ThreatHuntExecutionRequest(BaseModel):
    events: List[Dict[str, Any]] = Field(..., min_length=1, description="Security events to analyze")
    rule_ids: Optional[List[str]] = Field(None, description="Optional filter for specific hunting rules")


@threat_intel_router.get("/iocs", response_model=List[IOCRecord])
def list_iocs(
    ioc_type: Optional[str] = Query(None, description="Filter: ipv4, domain, url, md5, sha1, sha256"),
    severity: Optional[str] = Query(None, description="Filter: CRITICAL, HIGH, MEDIUM, LOW, INFO"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter: ACTIVE, EXPIRED, REVOKED, UNDER_REVIEW"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum reputation score"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Lists cached and managed threat indicators. Requires 'cases:view'."""
    iocs = threat_intel_store.cache.list_iocs(
        ioc_type=ioc_type,
        severity=severity,
        status=status_filter,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
    return iocs


@threat_intel_router.get("/iocs/{ioc_id}", response_model=IOCRecord)
def get_ioc(
    ioc_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves intelligence details on a specific indicator."""
    ioc = threat_intel_store.cache.get_ioc_by_id(ioc_id)
    if not ioc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Indicator '{ioc_id}' not found.")
    return ioc


@threat_intel_router.post("/enrich", response_model=IOCEnrichmentResponse)
def enrich_indicators(
    payload: IOCEnrichmentRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Enriches raw indicators against threat providers and local reputation cache."""
    response = threat_intel_store.enrich_indicators(
        indicators=payload.indicators,
        force_refresh=payload.force_refresh,
    )
    return response


@threat_intel_router.get("/rules", response_model=List[ThreatHuntingRule])
def list_hunting_rules(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Returns active threat hunting rules mapped to MITRE ATT&CK techniques."""
    return threat_intel_store.list_hunting_rules()


@threat_intel_router.post("/hunt", response_model=List[ThreatHuntResult])
def run_threat_hunt(
    payload: ThreatHuntExecutionRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR, Role.ANALYST])),
):
    """Executes hypothesis-driven threat hunting over provided security events."""
    results = threat_intel_store.execute_hunt(events=payload.events, rule_ids=payload.rule_ids)

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="threat_intel:execute_hunt",
        resource_type="HUNT_CAMPAIGN",
        resource_id=f"hunt-batch-{len(payload.events)}events",
        status="SUCCESS",
        details={"events_evaluated": len(payload.events), "matches_found": len(results)},
    )
    return results


@threat_intel_router.post("/feedback", response_model=IOCRecord)
def submit_analyst_feedback(
    payload: SubmitFeedbackRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR])),
):
    """Submits human analyst review feedback, updating confidence and risk score. Requires Investigator or Admin."""
    feedback = AnalystFeedback(
        feedback_id=f"fb-{uuid.uuid4().hex[:8]}",
        ioc_id=payload.ioc_id,
        analyst_id=current_user.email or current_user.username,
        verdict=payload.verdict,
        notes=payload.notes,
        confidence_adjustment=payload.confidence_adjustment,
    )

    try:
        updated_ioc = threat_intel_store.cache.add_analyst_feedback(feedback)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="threat_intel:submit_feedback",
        resource_type="IOC",
        resource_id=payload.ioc_id,
        status="SUCCESS",
        details={
            "verdict": payload.verdict.value,
            "new_reputation_score": updated_ioc.reputation_score,
            "new_status": updated_ioc.status.value,
        },
    )
    return updated_ioc


@threat_intel_router.get("/mitre", response_model=List[MITRETechnique])
def list_mitre_techniques(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Returns the MITRE ATT&CK taxonomy and technique reference catalog."""
    return MITREMapper.list_all_techniques()
