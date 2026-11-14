"""
FinGuard AI — Phase 30: Regulatory Reporting Service Layer.
Coordinates SAR/STR lifecycle, transitions, validations, submission tracking, and immutable auditing.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from regulatory_reporting.engine import validate_regulatory_report
from regulatory_reporting.models import (
    RegulatoryReport,
    ReportAuditEvent,
    ReportCreateRequest,
    ReportingMetrics,
    ReportStatus,
    ReportType,
    ReportValidationResult,
    ReviewDecision,
    ReviewReportRequest,
    SubmitReportRequest,
)
from regulatory_reporting.store import RegulatoryReportStore, report_store


class RegulatoryReportingService:
    def __init__(self, store: Optional[RegulatoryReportStore] = None):
        self.store = store or report_store

    def create_report(self, req: ReportCreateRequest) -> RegulatoryReport:
        now = datetime.now(timezone.utc)
        prefix = "SAR" if req.report_type == ReportType.SAR else "STR"
        report_id = f"{prefix}-{now.year}-{uuid.uuid4().hex[:6].upper()}"

        deadline = now + timedelta(days=req.filing_deadline_days)

        report = RegulatoryReport(
            report_id=report_id,
            report_type=req.report_type,
            jurisdiction=req.jurisdiction,
            status=ReportStatus.DRAFT,
            case_id=req.case_id,
            customer_id=req.customer_id,
            customer_name=req.customer_name,
            customer_pan_or_id=req.customer_pan_or_id,
            suspicion_narrative=req.suspicion_narrative,
            primary_offense_category=req.primary_offense_category,
            transaction_ids=req.transaction_ids,
            evidence_ids=req.evidence_ids,
            total_suspicious_amount=req.total_suspicious_amount,
            currency=req.currency,
            created_by=req.created_by,
            created_at=now,
            updated_at=now,
            filing_deadline=deadline,
        )

        validation = validate_regulatory_report(report)
        report.validation_result = validation

        self.store.save_report(report)
        self.store.add_audit_event(
            report_id=report_id,
            action="REPORT_CREATED",
            performed_by=req.created_by,
            details={
                "report_type": req.report_type.value,
                "jurisdiction": req.jurisdiction.value,
                "customer_id": req.customer_id,
                "total_amount": req.total_suspicious_amount,
            },
        )
        return report

    def validate_report(self, report_id: str) -> ReportValidationResult:
        report = self.store.get_report(report_id)
        if not report:
            raise KeyError(f"Report '{report_id}' not found.")

        result = validate_regulatory_report(report)
        report.validation_result = result
        self.store.save_report(report)

        self.store.add_audit_event(
            report_id=report_id,
            action="REPORT_VALIDATED",
            performed_by="system",
            details={"is_valid": result.is_valid, "error_count": len(result.errors)},
        )
        return result

    def send_for_review(self, report_id: str, sender: str = "analyst") -> RegulatoryReport:
        report = self.store.get_report(report_id)
        if not report:
            raise KeyError(f"Report '{report_id}' not found.")

        if report.status not in (ReportStatus.DRAFT, ReportStatus.RETURNED_TO_DRAFT):
            raise ValueError(
                f"Cannot send report in status '{report.status.value}' for review. Must be DRAFT or RETURNED_TO_DRAFT."
            )

        # Validate before allowing review
        validation = validate_regulatory_report(report)
        report.validation_result = validation
        if not validation.is_valid:
            error_msgs = [e.message for e in validation.errors if e.severity == "ERROR"]
            raise ValueError(f"Report validation failed: {'; '.join(error_msgs)}")

        report.status = ReportStatus.UNDER_REVIEW
        report.updated_at = datetime.now(timezone.utc)
        self.store.save_report(report)

        self.store.add_audit_event(
            report_id=report_id,
            action="SENT_FOR_REVIEW",
            performed_by=sender,
            details={"previous_status": report.status.value, "new_status": "UNDER_REVIEW"},
        )
        return report

    def review_report(self, report_id: str, req: ReviewReportRequest) -> RegulatoryReport:
        report = self.store.get_report(report_id)
        if not report:
            raise KeyError(f"Report '{report_id}' not found.")

        if report.status != ReportStatus.UNDER_REVIEW:
            raise ValueError(f"Report must be in 'UNDER_REVIEW' status to review. Current: {report.status.value}")

        now = datetime.now(timezone.utc)
        report.reviewed_by = req.reviewer
        report.reviewed_at = now
        report.review_notes = req.rationale
        report.updated_at = now

        if req.decision == ReviewDecision.APPROVE:
            report.status = ReportStatus.APPROVED
            action = "REPORT_APPROVED"
        elif req.decision == ReviewDecision.REJECT:
            report.status = ReportStatus.REJECTED
            action = "REPORT_REJECTED"
        elif req.decision == ReviewDecision.RETURN_TO_DRAFT:
            report.status = ReportStatus.RETURNED_TO_DRAFT
            action = "REPORT_RETURNED_TO_DRAFT"
        else:
            raise ValueError(f"Unknown review decision: {req.decision}")

        self.store.save_report(report)
        self.store.add_audit_event(
            report_id=report_id,
            action=action,
            performed_by=req.reviewer,
            details={"decision": req.decision.value, "rationale": req.rationale},
        )
        return report

    def submit_report(self, report_id: str, req: SubmitReportRequest) -> RegulatoryReport:
        report = self.store.get_report(report_id)
        if not report:
            raise KeyError(f"Report '{report_id}' not found.")

        if report.status != ReportStatus.APPROVED:
            raise ValueError(
                f"Cannot submit report in status '{report.status.value}'. Only 'APPROVED' reports may be submitted."
            )

        now = datetime.now(timezone.utc)
        report.status = ReportStatus.SUBMITTED
        report.external_filing_reference = req.external_filing_reference
        report.submitted_at = now
        report.submitted_by = req.submitted_by
        report.updated_at = now

        self.store.save_report(report)
        self.store.add_audit_event(
            report_id=report_id,
            action="REPORT_SUBMITTED",
            performed_by=req.submitted_by,
            details={
                "external_filing_reference": req.external_filing_reference,
                "notes": req.submission_notes,
            },
        )
        return report

    def get_report(self, report_id: str) -> Optional[RegulatoryReport]:
        return self.store.get_report(report_id)

    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        status: Optional[ReportStatus] = None,
        limit: int = 50,
    ) -> List[RegulatoryReport]:
        return self.store.list_reports(report_type=report_type, status=status, limit=limit)

    def get_audit_trail(self, report_id: str) -> List[ReportAuditEvent]:
        return self.store.get_audit_trail(report_id)

    def get_metrics(self) -> ReportingMetrics:
        return self.store.get_metrics()


# Default singleton instance
regulatory_service = RegulatoryReportingService()
