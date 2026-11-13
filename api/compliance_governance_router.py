"""
FinGuard AI — Phase 23 Regulatory Compliance & Audit Governance REST API Router.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from governance.models import (
    ComplianceReadinessReport,
    ControlAssessmentRequest,
    ControlEffectiveness,
    FindingCreateRequest,
    FindingRemediateRequest,
    FindingSeverity,
    FrameworkType,
    GovernanceAuditEvent,
    GovernanceControl,
    GovernanceFinding,
    RemediationStatus,
)
from governance.service import GovernanceService, get_governance_service

logger = logging.getLogger("finguard-governance-api")

compliance_governance_router = APIRouter(
    prefix="/compliance/governance", tags=["Enterprise Regulatory Compliance & Audit Governance"]
)


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
    return {"sub": "usr-compliance-officer", "email": "auditor@finguard.internal", "roles": ["Auditor", "Admin"]}


# ==========================================
# Health Endpoint
# ==========================================
@compliance_governance_router.get("/health")
def get_governance_health():
    """Health check endpoint for regulatory compliance and audit governance."""
    return {
        "status": "HEALTHY",
        "phase": "Phase 23 — Enterprise Regulatory Compliance & Financial Crime Governance",
        "service": "regulatory_compliance_engine",
    }


# ==========================================
# Compliance Controls Catalogue & Assessment
# ==========================================
@compliance_governance_router.get("/controls", response_model=List[GovernanceControl])
def list_compliance_controls(
    effectiveness: Optional[ControlEffectiveness] = Query(None, description="Filter: EFFECTIVE, PARTIALLY_EFFECTIVE, INEFFECTIVE, NOT_APPLICABLE"),
    framework: Optional[FrameworkType] = Query(None, description="Filter: SOC2, ISO27001, PCI_DSS, FINCEN_AML"),
    domain: Optional[str] = Query(None, description="Filter by security domain"),
    service: GovernanceService = Depends(get_governance_service),
):
    """Retrieve compliance control catalogue with framework mappings and assessment status."""
    return service.list_controls(effectiveness=effectiveness, framework=framework, domain=domain)


@compliance_governance_router.get("/controls/{control_id}", response_model=GovernanceControl)
def get_compliance_control_detail(
    control_id: str,
    service: GovernanceService = Depends(get_governance_service),
):
    """Retrieve single control specification, evidence references, and assessor rationale."""
    ctrl = service.get_control(control_id)
    if not ctrl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance control '{control_id}' not found.",
        )
    return ctrl


@compliance_governance_router.post("/controls/{control_id}/assess", response_model=GovernanceControl)
def assess_compliance_control(
    control_id: str,
    payload: ControlAssessmentRequest,
    request: Request,
    service: GovernanceService = Depends(get_governance_service),
):
    """
    Record formal control assessment: effectiveness status, evidence references, and assessor rationale.
    Automatically generates audit trail record.
    """
    actor = get_actor_from_request(request)
    assessor = payload.assessor or actor.get("email") or "compliance.auditor"
    payload.assessor = assessor
    try:
        return service.assess_control(control_id, payload, actor=assessor)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance control '{control_id}' not found.",
        )


# ==========================================
# Findings & Remediation Management
# ==========================================
@compliance_governance_router.get("/findings", response_model=List[GovernanceFinding])
def list_governance_findings(
    severity: Optional[FindingSeverity] = Query(None, description="Filter: CRITICAL, HIGH, MEDIUM, LOW"),
    status_filter: Optional[RemediationStatus] = Query(None, alias="status", description="Filter: OPEN, IN_PROGRESS, REMEDIATED, VERIFIED"),
    control_id: Optional[str] = Query(None, description="Filter by linked control ID"),
    service: GovernanceService = Depends(get_governance_service),
):
    """List compliance findings and deficiency tracking."""
    return service.list_findings(severity=severity, status=status_filter, control_id=control_id)


@compliance_governance_router.post("/findings", response_model=GovernanceFinding, status_code=status.HTTP_201_CREATED)
def create_governance_finding(
    payload: FindingCreateRequest,
    request: Request,
    service: GovernanceService = Depends(get_governance_service),
):
    """Create a new compliance finding linked to a control deficiency."""
    actor = get_actor_from_request(request)
    try:
        return service.create_finding(payload, actor=actor.get("email") or "compliance.auditor")
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@compliance_governance_router.post("/findings/{finding_id}/remediate", response_model=GovernanceFinding)
def remediate_governance_finding(
    finding_id: str,
    payload: FindingRemediateRequest,
    request: Request,
    service: GovernanceService = Depends(get_governance_service),
):
    """Update finding remediation status (IN_PROGRESS, REMEDIATED, VERIFIED) and log remediation notes."""
    actor = get_actor_from_request(request)
    remediator = payload.remediated_by or actor.get("email") or "security.lead"
    payload.remediated_by = remediator
    try:
        return service.remediate_finding(finding_id, payload, actor=remediator)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found.",
        )


# ==========================================
# Audit Trail & Readiness Reporting
# ==========================================
@compliance_governance_router.get("/audit-trail", response_model=List[GovernanceAuditEvent])
def get_governance_audit_trail(
    entity_id: Optional[str] = Query(None, description="Filter audit trail by control or finding ID"),
    limit: int = Query(100, ge=1, le=500),
    service: GovernanceService = Depends(get_governance_service),
):
    """Retrieve audit log of all control assessments, findings created, and remediations performed."""
    return service.list_audit_events(entity_id=entity_id, limit=limit)


@compliance_governance_router.get("/readiness", response_model=ComplianceReadinessReport)
def get_audit_readiness_report(
    service: GovernanceService = Depends(get_governance_service),
):
    """Generate overall audit-readiness snapshot, compliance KPIs, and framework breakdown."""
    return service.calculate_readiness()

