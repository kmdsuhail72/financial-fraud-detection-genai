"""
FinGuard AI — Phase 30: In-Memory Regulatory Report Store & Audit Trail.
Thread-safe store for SAR/STR reports, audit logging, and reporting KPIs.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from regulatory_reporting.engine import validate_regulatory_report
from regulatory_reporting.models import (
    RegulatoryJurisdiction,
    RegulatoryReport,
    ReportAuditEvent,
    ReportingMetrics,
    ReportStatus,
    ReportType,
)


class RegulatoryReportStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._reports: Dict[str, RegulatoryReport] = {}
        self._audit_events: Dict[str, List[ReportAuditEvent]] = {}
        self._seed_default_reports()

    def _seed_default_reports(self):
        """Seeds representative SAR/STR reports across submission lifecycle."""
        now = datetime.now(timezone.utc)

        # 1. Submitted SAR (FIU-IND)
        sar_001 = RegulatoryReport(
            report_id="SAR-2026-IND-001",
            report_type=ReportType.SAR,
            jurisdiction=RegulatoryJurisdiction.FIU_IND,
            status=ReportStatus.SUBMITTED,
            case_id="CASE-AML-9901",
            customer_id="CUST-IND-77102",
            customer_name="Vikram Malhotra",
            customer_pan_or_id="ABCDE1234F",
            suspicion_narrative="Repeated cash deposits just below the ₹10,00,000 threshold followed by immediate NEFT transfers overseas, indicative of structuring and layering.",
            primary_offense_category="Structuring",
            transaction_ids=["TXN-2026-001", "TXN-2026-002", "TXN-2026-003"],
            evidence_ids=["EV-SHA256-BANK-01", "EV-SHA256-KYC-02"],
            total_suspicious_amount=3250000.0,
            currency="INR",
            created_by="compliance_analyst@finguard.internal",
            created_at=now - timedelta(days=12),
            updated_at=now - timedelta(days=2),
            filing_deadline=now + timedelta(days=18),
            is_overdue=False,
            reviewed_by="mlro_officer@finguard.internal",
            reviewed_at=now - timedelta(days=4),
            review_notes="Approved for official filing. Clear structuring pattern confirmed.",
            external_filing_reference="FIU-IND-ACK-202604-9912",
            submitted_at=now - timedelta(days=2),
            submitted_by="mlro_officer@finguard.internal",
        )
        sar_001.validation_result = validate_regulatory_report(sar_001)
        self._reports[sar_001.report_id] = sar_001
        self._record_audit_event(
            sar_001.report_id,
            action="REPORT_CREATED",
            performed_by=sar_001.created_by,
            details={"type": "SAR", "jurisdiction": "FIU_IND"},
            timestamp=sar_001.created_at,
        )
        self._record_audit_event(
            sar_001.report_id,
            action="REPORT_APPROVED",
            performed_by="mlro_officer@finguard.internal",
            details={"decision": "APPROVE"},
            timestamp=sar_001.reviewed_at,
        )
        self._record_audit_event(
            sar_001.report_id,
            action="REPORT_SUBMITTED",
            performed_by="mlro_officer@finguard.internal",
            details={"filing_ref": "FIU-IND-ACK-202604-9912"},
            timestamp=sar_001.submitted_at,
        )

        # 2. STR Under Compliance Review
        str_002 = RegulatoryReport(
            report_id="STR-2026-IND-002",
            report_type=ReportType.STR,
            jurisdiction=RegulatoryJurisdiction.FIU_IND,
            status=ReportStatus.UNDER_REVIEW,
            case_id="CASE-AML-4412",
            customer_id="CUST-BLR-40291",
            customer_name="Jordan Cross",
            customer_pan_or_id="BNMPL9021K",
            suspicion_narrative="High-velocity payment funneling through newly added beneficiaries within 10-minute intervals without underlying economic rationale.",
            primary_offense_category="Payment Funneling / Layering",
            transaction_ids=["TXN-UPI-285000", "TXN-UPI-285001"],
            evidence_ids=["EV-PAYMENT-GATEWAY-TRACE-01"],
            total_suspicious_amount=1450000.0,
            currency="INR",
            created_by="analyst_rajesh@finguard.internal",
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=1),
            filing_deadline=now + timedelta(days=27),
            is_overdue=False,
        )
        str_002.validation_result = validate_regulatory_report(str_002)
        self._reports[str_002.report_id] = str_002
        self._record_audit_event(
            str_002.report_id,
            action="REPORT_CREATED",
            performed_by=str_002.created_by,
            details={"type": "STR"},
            timestamp=str_002.created_at,
        )
        self._record_audit_event(
            str_002.report_id,
            action="SENT_FOR_REVIEW",
            performed_by=str_002.created_by,
            details={"stage": "UNDER_REVIEW"},
            timestamp=str_002.updated_at,
        )

    def _record_audit_event(
        self,
        report_id: str,
        action: str,
        performed_by: str,
        details: Dict,
        timestamp: Optional[datetime] = None,
    ):
        with self._lock:
            if report_id not in self._audit_events:
                self._audit_events[report_id] = []
            event = ReportAuditEvent(
                event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
                report_id=report_id,
                action=action,
                performed_by=performed_by,
                details=details,
                timestamp=timestamp or datetime.now(timezone.utc),
            )
            self._audit_events[report_id].append(event)

    def save_report(self, report: RegulatoryReport) -> RegulatoryReport:
        with self._lock:
            # Check deadline status
            now = datetime.now(timezone.utc)
            if report.filing_deadline and now > report.filing_deadline:
                report.is_overdue = True
            else:
                report.is_overdue = False

            report.validation_result = validate_regulatory_report(report)
            report.updated_at = now
            self._reports[report.report_id] = report
            return report

    def get_report(self, report_id: str) -> Optional[RegulatoryReport]:
        with self._lock:
            report = self._reports.get(report_id)
            if report:
                now = datetime.now(timezone.utc)
                if report.filing_deadline and now > report.filing_deadline:
                    report.is_overdue = True
            return report

    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        status: Optional[ReportStatus] = None,
        limit: int = 50,
    ) -> List[RegulatoryReport]:
        with self._lock:
            items = list(self._reports.values())
            now = datetime.now(timezone.utc)
            for r in items:
                if r.filing_deadline and now > r.filing_deadline:
                    r.is_overdue = True

            if report_type:
                items = [r for r in items if r.report_type == report_type]
            if status:
                items = [r for r in items if r.status == status]

            items.sort(key=lambda x: x.created_at, reverse=True)
            return items[:limit]

    def get_audit_trail(self, report_id: str) -> List[ReportAuditEvent]:
        with self._lock:
            return list(self._audit_events.get(report_id, []))

    def add_audit_event(
        self,
        report_id: str,
        action: str,
        performed_by: str,
        details: Dict,
    ):
        self._record_audit_event(report_id, action, performed_by, details)

    def get_metrics(self) -> ReportingMetrics:
        with self._lock:
            reports = list(self._reports.values())
            now = datetime.now(timezone.utc)

            total = len(reports)
            drafts = sum(1 for r in reports if r.status == ReportStatus.DRAFT)
            under_rev = sum(1 for r in reports if r.status == ReportStatus.UNDER_REVIEW)
            approved = sum(1 for r in reports if r.status == ReportStatus.APPROVED)
            submitted = sum(1 for r in reports if r.status == ReportStatus.SUBMITTED)
            rejected = sum(1 for r in reports if r.status == ReportStatus.REJECTED)
            returned = sum(1 for r in reports if r.status == ReportStatus.RETURNED_TO_DRAFT)
            overdue = sum(1 for r in reports if r.filing_deadline and now > r.filing_deadline and r.status != ReportStatus.SUBMITTED)
            total_amt = sum(r.total_suspicious_amount for r in reports)

            return ReportingMetrics(
                total_reports=total,
                draft_count=drafts,
                under_review_count=under_rev,
                approved_count=approved,
                submitted_count=submitted,
                rejected_count=rejected,
                returned_to_draft_count=returned,
                overdue_count=overdue,
                total_suspicious_amount_reported=round(total_amt, 2),
            )


# Global singleton store
report_store = RegulatoryReportStore()
