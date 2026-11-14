"""
FinGuard AI — Phase 30: Enterprise Regulatory Reporting (SAR/STR) REST API Router.
Provides endpoints for creating, validating, reviewing, and recording SAR/STR submissions.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from regulatory_reporting.models import (
    RegulatoryReport,
    ReportAuditEvent,
    ReportCreateRequest,
    ReportingMetrics,
    ReportStatus,
    ReportType,
    ReportValidationResult,
    ReviewReportRequest,
    SubmitReportRequest,
)
from regulatory_reporting.service import regulatory_service

logger = logging.getLogger("finguard-regulatory-api")

regulatory_router = APIRouter(tags=["Enterprise AML Regulatory Reporting (SAR/STR)"])


@regulatory_router.get("/regulatory/health", summary="Regulatory Reporting Health Check")
def regulatory_health():
    """Returns the operational status of the regulatory reporting system."""
    return {
        "status": "ok",
        "service": "regulatory_reporting",
        "phase": "Phase-30",
        "templates": ["SAR", "STR"],
        "jurisdictions": ["FIU_IND", "FINCEN", "FCA", "GLOBAL"],
        "advisory_standard": True,
    }


@regulatory_router.post(
    "/reports",
    response_model=RegulatoryReport,
    status_code=status.HTTP_201_CREATED,
    summary="Create SAR/STR Regulatory Draft",
)
def create_report(req: ReportCreateRequest) -> RegulatoryReport:
    """Creates a new SAR/STR draft linked to customer, transactions, and evidence."""
    try:
        report = regulatory_service.create_report(req)
        logger.info("Created %s report %s for customer %s", report.report_type.value, report.report_id, report.customer_id)
        return report
    except Exception as exc:
        logger.error("Failed to create report: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@regulatory_router.get(
    "/reports",
    response_model=List[RegulatoryReport],
    summary="List Regulatory Reports",
)
def list_reports(
    report_type: Optional[ReportType] = Query(None, description="Filter by SAR or STR"),
    status: Optional[ReportStatus] = Query(None, description="Filter by report status"),
    limit: int = Query(50, ge=1, le=200),
) -> List[RegulatoryReport]:
    """Retrieves all regulatory filings matching criteria."""
    return regulatory_service.list_reports(report_type=report_type, status=status, limit=limit)


@regulatory_router.get(
    "/reports/metrics",
    response_model=ReportingMetrics,
    summary="Regulatory Reporting Metrics & Overdue Deadlines",
)
def get_reporting_metrics() -> ReportingMetrics:
    """Aggregates SAR/STR operational KPIs and statutory deadline metrics."""
    return regulatory_service.get_metrics()


# Also alias /metrics on this router
@regulatory_router.get(
    "/metrics",
    include_in_schema=False,
)
def get_metrics_alias(request: Request):
    accept = request.headers.get("accept", "")
    if "text/plain" in accept or "openmetrics" in accept or request.query_params.get("format") == "prometheus":
        from observability.service import observability_service
        return Response(content=observability_service.get_prometheus_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")
    return regulatory_service.get_metrics()


@regulatory_router.get(
    "/reports/{report_id}",
    response_model=RegulatoryReport,
    summary="Retrieve Regulatory Report",
)
def get_report(report_id: str) -> RegulatoryReport:
    """Retrieves an existing regulatory report by reference ID."""
    report = regulatory_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulatory report '{report_id}' not found.",
        )
    return report


@regulatory_router.post(
    "/reports/{report_id}/validate",
    response_model=ReportValidationResult,
    summary="Validate Report for Submission Readiness",
)
def validate_report(report_id: str) -> ReportValidationResult:
    """Runs structural, reference, and deadline consistency checks on a report."""
    try:
        return regulatory_service.validate_report(report_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulatory report '{report_id}' not found.",
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@regulatory_router.post(
    "/reports/{report_id}/send-for-review",
    response_model=RegulatoryReport,
    summary="Submit Report for Compliance Review",
)
def send_for_review(report_id: str, sender: str = Query("compliance_analyst")) -> RegulatoryReport:
    """Transitions a draft report to UNDER_REVIEW status after validating required fields."""
    try:
        return regulatory_service.send_for_review(report_id, sender=sender)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulatory report '{report_id}' not found.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@regulatory_router.post(
    "/reports/{report_id}/review",
    response_model=RegulatoryReport,
    summary="Review Report (Approve / Reject / Return)",
)
def review_report(report_id: str, req: ReviewReportRequest) -> RegulatoryReport:
    """Compliance officer decision: APPROVE, REJECT, or RETURN_TO_DRAFT with written rationale."""
    try:
        return regulatory_service.review_report(report_id, req)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulatory report '{report_id}' not found.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@regulatory_router.post(
    "/reports/{report_id}/submit",
    response_model=RegulatoryReport,
    summary="Record External Regulatory Submission",
)
def submit_report(report_id: str, req: SubmitReportRequest) -> RegulatoryReport:
    """Attaches external regulator acknowledgment reference and records SUBMITTED status."""
    try:
        return regulatory_service.submit_report(report_id, req)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulatory report '{report_id}' not found.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@regulatory_router.get(
    "/reports/{report_id}/audit",
    response_model=List[ReportAuditEvent],
    summary="Retrieve Report Audit Trail",
)
def get_report_audit(report_id: str) -> List[ReportAuditEvent]:
    """Retrieves immutable chronological audit events for a report."""
    report = regulatory_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Regulatory report '{report_id}' not found.",
        )
    return regulatory_service.get_audit_trail(report_id)
