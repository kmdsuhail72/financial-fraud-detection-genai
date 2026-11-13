"""
FinGuard AI — Phase 21 Enterprise Operations Queue, Alert Ingestion & SLA Management REST API Router.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, ConfigDict

from operations.models import (
    AlertIngestRequest,
    AlertIngestResponse,
    AlertPriority,
    AnalystNoteRequest,
    CaseAssignRequest,
    CaseResolveRequest,
    CaseStatus,
    CaseStatusUpdateRequest,
    OperationalCase,
    OperationsMetricsResponse,
)
from operations.service import OperationsService, get_operations_service
from security.audit import audit_logger
from security.roles import Permission, has_permission

logger = logging.getLogger("finguard-operations-api")

operations_router = APIRouter(tags=["Enterprise Operations Queue & Alert Ingestion"])


def check_permission_flexible(
    request: Request, required_permission: Optional[Permission] = None
) -> Dict[str, Any]:
    """
    Validates Bearer token if provided, enforcing RBAC permissions.
    If no authorization header is supplied, defaults to local analyst context for development.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        from security.dependencies import jwt_verifier
        token = auth_header[7:].strip()
        try:
            user = jwt_verifier.verify_token(token)
            if required_permission and not has_permission(user.roles, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Missing required permission '{required_permission.value}'",
                )
            role_list = [r.value if hasattr(r, "value") else str(r) for r in user.roles]
            return {"sub": user.sub, "email": user.email, "roles": role_list}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authorization token: {e}",
            )
    return {
        "sub": "usr-ops-analyst",
        "email": "analyst@finguard.internal",
        "roles": ["Admin", "Investigator", "Analyst"],
    }


# ==========================================
# Health Endpoints
# ==========================================
@operations_router.get("/operations/health")
@operations_router.get("/alerts/health")
def get_operations_health():
    """Health check endpoint for Operations Queue and Alert Ingestion."""
    return {
        "status": "HEALTHY",
        "phase": "Phase 21 — Enterprise Operations Queue, SLA Management & Alert Ingestion",
        "service": "operations_queue_engine",
    }


# ==========================================
# Alert Ingestion & Deduplication
# ==========================================
@operations_router.post("/alerts", response_model=AlertIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_alert(
    payload: AlertIngestRequest,
    request: Request,
    service: OperationsService = Depends(get_operations_service),
):
    """
    Ingest a real-time fraud alert with tenant-scoped idempotency.
    Automatically assigns priority (P0-P3) and computes SLA deadlines.
    """
    actor = check_permission_flexible(request)
    response = service.ingest_alert(payload)

    audit_logger.log(
        actor_sub=actor.get("sub", "system"),
        actor_email=actor.get("email"),
        actor_roles=actor.get("roles", []),
        action="alert:ingest",
        resource_type="ALERT",
        resource_id=response.alert_id,
        status="SUCCESS",
        details={
            "case_id": response.case_id,
            "tenant_id": response.tenant_id,
            "priority": response.priority.value,
            "is_duplicate": response.is_duplicate,
            "risk_score": response.risk_score,
        },
    )
    return response


@operations_router.get("/alerts", response_model=List[OperationalCase])
def list_alerts(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant identifier"),
    status_filter: Optional[CaseStatus] = Query(None, alias="status", description="Filter by status"),
    priority: Optional[AlertPriority] = Query(None, description="Filter by priority: P0, P1, P2, P3"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned analyst"),
    limit: int = Query(50, ge=1, le=200),
    service: OperationsService = Depends(get_operations_service),
):
    """List operational alerts/cases with SLA monitoring."""
    return service.list_cases(
        tenant_id=tenant_id,
        status=status_filter,
        priority=priority,
        assigned_to=assigned_to,
        limit=limit,
    )


# ==========================================
# Operations Queue & Metrics
# ==========================================
@operations_router.get("/operations/queue", response_model=List[OperationalCase])
def get_operations_queue(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    limit: int = Query(50, ge=1, le=200),
    service: OperationsService = Depends(get_operations_service),
):
    """Retrieve operational queue sorted by SLA deadline and priority tier."""
    return service.list_cases(
        tenant_id=tenant_id,
        status=None,
        limit=limit,
    )


@operations_router.get("/operations/metrics", response_model=OperationsMetricsResponse)
def get_operations_metrics(
    tenant_id: Optional[str] = Query(None, description="Optional tenant scoping"),
    service: OperationsService = Depends(get_operations_service),
):
    """Retrieve comprehensive queue, priority, SLA breach, and analyst workload metrics."""
    return service.get_metrics(tenant_id=tenant_id)


# ==========================================
# Operational Case Detail & Lifecycle
# ==========================================
@operations_router.get("/operations/cases/{case_id}", response_model=OperationalCase)
def get_operational_case_detail(
    case_id: str,
    service: OperationsService = Depends(get_operations_service),
):
    """Retrieve full details of an operational case."""
    case = service.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operational case '{case_id}' not found.",
        )
    return case


class FlexibleAssignRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    analyst_id: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_by: Optional[str] = "supervisor"


@operations_router.post("/cases/{case_id}/assign")
@operations_router.post("/operations/cases/{case_id}/assign", include_in_schema=False)
def assign_operational_case(
    case_id: str,
    payload: FlexibleAssignRequest,
    request: Request,
    service: OperationsService = Depends(get_operations_service),
):
    """Assign a case to an analyst (supports both Operational and Legacy CaseStore cases)."""
    actor = check_permission_flexible(request, Permission.ASSIGN_CASES)
    analyst = payload.analyst_id or payload.assigned_to
    if not analyst:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'analyst_id' or 'assigned_to' must be provided.",
        )

    # 1. Try OperationsService
    op_case = service.get_case(case_id)
    if op_case:
        assign_req = CaseAssignRequest(
            analyst_id=analyst,
            assigned_by=payload.assigned_by or actor.get("email") or "supervisor",
        )
        updated = service.assign_case(case_id, assign_req)
        audit_logger.log(
            actor_sub=actor.get("sub", "system"),
            actor_email=actor.get("email"),
            actor_roles=actor.get("roles", []),
            action="case:assign",
            resource_type="CASE",
            resource_id=case_id,
            status="SUCCESS",
            details={"assigned_to": analyst},
        )
        return updated

    # 2. Fallback to Legacy CaseStore (e.g. CASE-123)
    try:
        from api.app import CASE_STORE
        from investigation.models import CaseUpdateRequest
        legacy_update = CaseUpdateRequest(assigned_to=analyst)
        updated_legacy = CASE_STORE.update_case(
            case_id, legacy_update, performed_by=actor.get("email") or "system"
        )
        if updated_legacy:
            audit_logger.log(
                actor_sub=actor.get("sub", "system"),
                actor_email=actor.get("email"),
                actor_roles=actor.get("roles", []),
                action="cases:assign",
                resource_type="CASE",
                resource_id=case_id,
                status="SUCCESS",
                details={"assigned_to": analyst},
            )
            return updated_legacy
    except Exception as e:
        logger.warning(f"Fallback CASE_STORE assign failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Case '{case_id}' not found.",
    )


@operations_router.post("/cases/{case_id}/status")
@operations_router.put("/cases/{case_id}/status", include_in_schema=False)
@operations_router.post("/operations/cases/{case_id}/status", include_in_schema=False)
def update_operational_case_status(
    case_id: str,
    payload: CaseStatusUpdateRequest,
    request: Request,
    service: OperationsService = Depends(get_operations_service),
):
    """Transition case status (e.g., OPEN -> IN_REVIEW, ESCALATED)."""
    actor = check_permission_flexible(request)
    if not payload.updated_by or payload.updated_by == "analyst":
        payload.updated_by = actor.get("email") or "analyst"

    # 1. Try OperationsService
    op_case = service.get_case(case_id)
    if op_case:
        updated = service.update_case_status(case_id, payload)
        audit_logger.log(
            actor_sub=actor.get("sub", "system"),
            actor_email=actor.get("email"),
            actor_roles=actor.get("roles", []),
            action="case:status_update",
            resource_type="CASE",
            resource_id=case_id,
            status="SUCCESS",
            details={"new_status": payload.status.value, "reason": payload.reason},
        )
        return updated

    # 2. Fallback to Legacy CaseStore
    try:
        from api.app import CASE_STORE
        from investigation.models import CaseStatus as LegacyCaseStatus, CaseUpdateRequest
        legacy_status = getattr(LegacyCaseStatus, payload.status.value, None)
        if legacy_status:
            legacy_update = CaseUpdateRequest(status=legacy_status)
            updated_legacy = CASE_STORE.update_case(
                case_id, legacy_update, performed_by=actor.get("email") or "system"
            )
            if updated_legacy:
                return updated_legacy
    except Exception as e:
        logger.warning(f"Fallback CASE_STORE status update failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Case '{case_id}' not found.",
    )


class FlexibleNoteRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    author: Optional[str] = "analyst"
    content: Optional[str] = None
    note: Optional[str] = None


@operations_router.post("/cases/{case_id}/notes")
@operations_router.post("/operations/cases/{case_id}/notes", include_in_schema=False)
def add_operational_case_note(
    case_id: str,
    payload: FlexibleNoteRequest,
    request: Request,
    service: OperationsService = Depends(get_operations_service),
):
    """Add an investigation note to case timeline."""
    actor = check_permission_flexible(request, Permission.ADD_NOTES)
    author = payload.author or actor.get("email") or "analyst"
    content = payload.content or payload.note
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Note content cannot be empty (provide 'content' or 'note').",
        )

    # 1. Try OperationsService
    op_case = service.get_case(case_id)
    if op_case:
        note_req = AnalystNoteRequest(author=author, content=content)
        updated = service.add_note(case_id, note_req)
        audit_logger.log(
            actor_sub=actor.get("sub", "system"),
            actor_email=actor.get("email"),
            actor_roles=actor.get("roles", []),
            action="case:add_note",
            resource_type="CASE",
            resource_id=case_id,
            status="SUCCESS",
            details={"note_preview": content[:60]},
        )
        return updated

    # 2. Fallback to Legacy CaseStore
    try:
        from api.app import CASE_STORE
        from investigation.models import CaseUpdateRequest
        legacy_update = CaseUpdateRequest(note=content)
        updated_legacy = CASE_STORE.update_case(
            case_id, legacy_update, performed_by=actor.get("email") or "system"
        )
        if updated_legacy:
            audit_logger.log(
                actor_sub=actor.get("sub", "system"),
                actor_email=actor.get("email"),
                actor_roles=actor.get("roles", []),
                action="cases:notes:add",
                resource_type="CASE",
                resource_id=case_id,
                status="SUCCESS",
                details={"note_preview": content[:60]},
            )
            return updated_legacy
    except Exception as e:
        logger.warning(f"Fallback CASE_STORE add note failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Case '{case_id}' not found.",
    )


class FlexibleResolveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    resolution: Optional[str] = None
    resolution_action: Optional[str] = None
    resolved_by: Optional[str] = "analyst"
    notes: Optional[str] = None
    resolution_notes: Optional[str] = None


@operations_router.post("/cases/{case_id}/resolve")
@operations_router.post("/operations/cases/{case_id}/resolve", include_in_schema=False)
def resolve_operational_case(
    case_id: str,
    payload: FlexibleResolveRequest,
    request: Request,
    service: OperationsService = Depends(get_operations_service),
):
    """Mark a case as RESOLVED with resolution classification."""
    actor = check_permission_flexible(request, Permission.RESOLVE_CASES)
    resolution = payload.resolution or payload.resolution_action
    if not resolution:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resolution classification is required.",
        )
    resolved_by = payload.resolved_by or actor.get("email") or "analyst"
    notes = payload.notes or payload.resolution_notes

    # 1. Try OperationsService
    op_case = service.get_case(case_id)
    if op_case:
        resolve_req = CaseResolveRequest(
            resolution=resolution,
            resolved_by=resolved_by,
            notes=notes,
        )
        updated = service.resolve_case(case_id, resolve_req)
        audit_logger.log(
            actor_sub=actor.get("sub", "system"),
            actor_email=actor.get("email"),
            actor_roles=actor.get("roles", []),
            action="case:resolve",
            resource_type="CASE",
            resource_id=case_id,
            status="SUCCESS",
            details={"resolution": resolution},
        )
        return updated

    # 2. Fallback to Legacy CaseStore
    try:
        from api.app import CASE_STORE
        from investigation.models import CaseStatus as LegacyCaseStatus, CaseUpdateRequest, ResolutionAction
        res_action = getattr(ResolutionAction, resolution, ResolutionAction.CONFIRMED_FRAUD)
        legacy_update = CaseUpdateRequest(
            status=LegacyCaseStatus.RESOLVED,
            resolution_action=res_action,
            resolution_notes=notes,
        )
        updated_legacy = CASE_STORE.update_case(
            case_id, legacy_update, performed_by=actor.get("email") or "system"
        )
        if updated_legacy:
            audit_logger.log(
                actor_sub=actor.get("sub", "system"),
                actor_email=actor.get("email"),
                actor_roles=actor.get("roles", []),
                action="cases:resolve",
                resource_type="CASE",
                resource_id=case_id,
                status="SUCCESS",
                details={"resolution_action": resolution},
            )
            return updated_legacy
    except Exception as e:
        logger.warning(f"Fallback CASE_STORE resolve failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Case '{case_id}' not found.",
    )


class FlexibleEscalateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    reason: Optional[str] = "Escalated for senior investigator review"
    escalated_by: Optional[str] = "analyst"


@operations_router.post("/cases/{case_id}/escalate")
@operations_router.post("/operations/cases/{case_id}/escalate", include_in_schema=False)
def escalate_operational_case(
    case_id: str,
    payload: FlexibleEscalateRequest,
    request: Request,
    service: OperationsService = Depends(get_operations_service),
):
    """Escalate a case to senior fraud investigators."""
    actor = check_permission_flexible(request, Permission.ESCALATE_CASES)
    escalated_by = payload.escalated_by or actor.get("email") or "analyst"

    # 1. Try OperationsService
    op_case = service.get_case(case_id)
    if op_case:
        update_req = CaseStatusUpdateRequest(
            status=CaseStatus.ESCALATED,
            updated_by=escalated_by,
            reason=payload.reason,
        )
        updated = service.update_case_status(case_id, update_req)
        audit_logger.log(
            actor_sub=actor.get("sub", "system"),
            actor_email=actor.get("email"),
            actor_roles=actor.get("roles", []),
            action="case:escalate",
            resource_type="CASE",
            resource_id=case_id,
            status="SUCCESS",
            details={"reason": payload.reason},
        )
        return updated

    # 2. Fallback to Legacy CaseStore
    try:
        from api.app import CASE_STORE
        from investigation.models import CaseStatus as LegacyCaseStatus, CaseUpdateRequest
        legacy_update = CaseUpdateRequest(
            status=LegacyCaseStatus.ESCALATED,
            note=f"ESCALATED: {payload.reason}" if payload.reason else "Case escalated",
        )
        updated_legacy = CASE_STORE.update_case(
            case_id, legacy_update, performed_by=actor.get("email") or "system"
        )
        if updated_legacy:
            audit_logger.log(
                actor_sub=actor.get("sub", "system"),
                actor_email=actor.get("email"),
                actor_roles=actor.get("roles", []),
                action="cases:escalate",
                resource_type="CASE",
                resource_id=case_id,
                status="SUCCESS",
                details={"reason": payload.reason},
            )
            return updated_legacy
    except Exception as e:
        logger.warning(f"Fallback CASE_STORE escalate failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Case '{case_id}' not found.",
    )


@operations_router.get("/cases/{case_id}")
def get_any_case_detail(
    case_id: str,
    request: Request,
    service: OperationsService = Depends(get_operations_service),
):
    """Retrieve case detail from either OperationsService or CaseStore."""
    # 1. Try OperationsService
    op_case = service.get_case(case_id)
    if op_case:
        return op_case

    # 2. Try CaseStore (requires auth if present or token)
    try:
        from api.app import CASE_STORE
        legacy_case = CASE_STORE.get_case(case_id)
        if legacy_case:
            return legacy_case
    except Exception as e:
        logger.warning(f"Fallback CASE_STORE get failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Case '{case_id}' not found.",
    )
