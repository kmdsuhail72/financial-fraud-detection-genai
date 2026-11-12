"""FastAPI Router for SOC Incident Management, Playbooks, and Remediation (Phase 12)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from security.auth import AuthenticatedUser
from security.audit import audit_logger
from security.dependencies import get_current_user, require_permission, require_roles
from security.roles import Permission, Role
from soc.event_normalizer import EventNormalizer
from soc.incident_store import soc_incident_store
from soc.models import (
    ApprovalStatus,
    IncidentSeverity,
    IncidentStatus,
    RemediationApproval,
    RemediationReceipt,
    SOCIncident,
    SOCMetrics,
)

soc_router = APIRouter(prefix="/soc", tags=["SOC Incident Response & Threat Containment"])


class IngestEventRequest(BaseModel):
    event: Dict[str, Any]


class AssignIncidentRequest(BaseModel):
    assigned_to: str = Field(..., json_schema_extra={"example": "soc.analyst@finguard.internal"})


class RequestApprovalRequest(BaseModel):
    action_id: str = Field(..., json_schema_extra={"example": "ACT-REVOKE-STS"})


class DecisionApprovalRequest(BaseModel):
    decision: ApprovalStatus = Field(..., json_schema_extra={"example": "APPROVED"})
    notes: Optional[str] = Field(None, json_schema_extra={"example": "Verified anomalous IP outside office range."})


class UpdateStatusRequest(BaseModel):
    status: IncidentStatus = Field(..., json_schema_extra={"example": "CONTAINED"})


@soc_router.get("/incidents", response_model=List[SOCIncident])
def list_incidents(
    severity: Optional[str] = Query(None, description="Filter: CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="Filter: NEW, ASSIGNED, INVESTIGATING, CONTAINED, RESOLVED, CLOSED"),
    limit: int = Query(50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Lists SOC incident cases. Requires 'cases:view'."""
    incidents = soc_incident_store.list_incidents(severity=severity, status=status, limit=limit)
    return incidents


@soc_router.get("/incidents/{incident_id}", response_model=SOCIncident)
def get_incident(
    incident_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves full incident case dossier including AI brief, timeline, playbooks, approvals, and receipts."""
    incident = soc_incident_store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found.")
    return incident


@soc_router.post("/events", response_model=SOCIncident, status_code=status.HTTP_201_CREATED)
def ingest_security_event(
    payload: IngestEventRequest,
    current_user: AuthenticatedUser = Depends(require_roles([Role.ADMIN, Role.INVESTIGATOR, Role.ANALYST])),
):
    """Ingests raw security finding event, normalizes, correlates, and returns active SOC incident."""
    normalized = EventNormalizer.normalize(payload.event)
    incident = soc_incident_store.ingest_event(normalized)

    audit_logger.log(
        actor_sub=current_user.sub,
        actor_email=current_user.email,
        actor_roles=current_user.roles,
        action="soc:event:ingest",
        resource_type="SOC_INCIDENT",
        resource_id=incident.incident_id,
        status="SUCCESS",
        details={"source": normalized.source, "severity": normalized.severity.value},
    )
    return incident


@soc_router.post("/incidents/{incident_id}/assign", response_model=SOCIncident)
def assign_incident(
    incident_id: str,
    payload: AssignIncidentRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.ASSIGN_CASES)),
):
    """Assigns an incident to an analyst. Requires 'cases:assign' (Admin, Investigator)."""
    try:
        incident = soc_incident_store.assign_incident(
            incident_id, payload.assigned_to, performed_by=current_user.email or current_user.username
        )
        return incident
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@soc_router.post("/incidents/{incident_id}/approvals", response_model=RemediationApproval)
def request_remediation_approval(
    incident_id: str,
    payload: RequestApprovalRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.ADD_NOTES)),
):
    """Requests human approval for a sensitive playbook action."""
    try:
        approval = soc_incident_store.request_approval(
            incident_id, payload.action_id, requested_by=current_user.email or current_user.username
        )
        return approval
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@soc_router.post("/incidents/{incident_id}/approvals/{approval_id}", response_model=RemediationApproval)
def approve_or_reject_action(
    incident_id: str,
    approval_id: str,
    payload: DecisionApprovalRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.RESOLVE_CASES)),
):
    """Records approval or rejection for a containment action. Requires 'cases:resolve' (Admin, Investigator)."""
    try:
        approval = soc_incident_store.approve_action(
            incident_id,
            approval_id,
            approver=current_user.email or current_user.username,
            decision=payload.decision,
            notes=payload.notes,
        )
        return approval
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@soc_router.post("/incidents/{incident_id}/remediate/{action_id}", response_model=RemediationReceipt)
def execute_remediation(
    incident_id: str,
    action_id: str,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.RESOLVE_CASES)),
):
    """Executes approved containment action in allowlisted simulation sandbox. Requires 'cases:resolve'."""
    try:
        receipt = soc_incident_store.execute_remediation(
            incident_id, action_id, executed_by=current_user.email or current_user.username
        )
        return receipt
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@soc_router.patch("/incidents/{incident_id}/status", response_model=SOCIncident)
def update_incident_status(
    incident_id: str,
    payload: UpdateStatusRequest,
    current_user: AuthenticatedUser = Depends(require_permission(Permission.ADD_NOTES)),
):
    """Updates incident status. Requires 'cases:notes:add'."""
    try:
        incident = soc_incident_store.update_status(
            incident_id, payload.status, performed_by=current_user.email or current_user.username
        )
        return incident
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@soc_router.get("/metrics", response_model=SOCMetrics)
def get_soc_metrics(
    current_user: AuthenticatedUser = Depends(require_permission(Permission.VIEW_CASES)),
):
    """Retrieves SOC operational metrics, open incidents by severity, and SLA compliance percentage."""
    return soc_incident_store.get_metrics()

