"""
FinGuard AI — Phase 22 Evidence Store.
Thread-safe evidence metadata registry, SHA-256 verification, timeline management, and audit logging.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from evidence.hashing import compute_sha256, serialize_canonical_payload, verify_sha256
from evidence.copilot import EvidenceGroundedCopilot
from evidence.models import (
    AnalystInvestigationReport,
    CaseTimeline,
    CopilotInvestigationDraft,
    EvidenceAuditEntry,
    EvidenceCollectRequest,
    EvidenceItem,
    EvidenceType,
    IntegrityVerificationResult,
    ReportGenerateRequest,
    TimelineEvent,
)


class EvidenceStore:
    """Thread-safe evidence locker, SHA-256 integrity validator, and digital forensics registry."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._evidence: Dict[str, EvidenceItem] = {}
        self._case_index: Dict[str, List[str]] = {}
        self._timeline_events: Dict[str, List[TimelineEvent]] = {}
        self._drafts: Dict[str, CopilotInvestigationDraft] = {}
        self._reports: Dict[str, AnalystInvestigationReport] = {}
        self._audit_log: List[EvidenceAuditEntry] = []
        self._copilot = EvidenceGroundedCopilot()

    def log_audit(
        self,
        actor: str,
        action: str,
        evidence_id: Optional[str] = None,
        case_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> EvidenceAuditEntry:
        entry = EvidenceAuditEntry(
            actor=actor,
            action=action,
            evidence_id=evidence_id,
            case_id=case_id,
            ip_address=ip_address or "127.0.0.1",
            details=details or {},
        )
        with self._lock:
            self._audit_log.append(entry)
        return entry

    def collect_evidence(
        self,
        request: EvidenceCollectRequest,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> EvidenceItem:
        with self._lock:
            evidence_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now(timezone.utc)

            # Compute canonical SHA-256 digest
            sha256_hash = compute_sha256(request.payload)
            size_bytes = len(serialize_canonical_payload(request.payload))

            item = EvidenceItem(
                evidence_id=evidence_id,
                case_id=request.case_id,
                evidence_type=request.evidence_type,
                title=request.title,
                description=request.description or "",
                source_system=request.source_system,
                collected_at=now,
                collector=request.collector or actor,
                raw_payload=request.payload,
                sha256_hash=sha256_hash,
                size_bytes=size_bytes,
                metadata=request.metadata,
            )

            self._evidence[evidence_id] = item
            if request.case_id not in self._case_index:
                self._case_index[request.case_id] = []
            self._case_index[request.case_id].append(evidence_id)

            # Automatically inject timeline event for this evidence
            entity_id = (
                request.payload.get("transaction_id")
                or request.payload.get("device_id")
                or request.payload.get("ip_address")
                or request.case_id
            )
            evt = TimelineEvent(
                case_id=request.case_id,
                timestamp=now,
                event_type=f"EVIDENCE_{request.evidence_type.value}",
                entity_id=str(entity_id),
                summary=f"Collected {request.evidence_type.value}: {request.title}",
                evidence_id=evidence_id,
                details={"sha256": sha256_hash, "size_bytes": size_bytes},
            )
            self._add_timeline_event_internal(evt)

            # Audit log
            self.log_audit(
                actor=actor,
                action="COLLECT",
                evidence_id=evidence_id,
                case_id=request.case_id,
                ip_address=ip_address,
                details={"evidence_type": request.evidence_type.value, "sha256": sha256_hash},
            )

            return item

    def get_evidence(
        self,
        evidence_id: str,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> Optional[EvidenceItem]:
        with self._lock:
            item = self._evidence.get(evidence_id)
            if item:
                self.log_audit(
                    actor=actor,
                    action="VIEW",
                    evidence_id=evidence_id,
                    case_id=item.case_id,
                    ip_address=ip_address,
                )
            return item

    def list_case_evidence(
        self,
        case_id: str,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> List[EvidenceItem]:
        with self._lock:
            evidence_ids = self._case_index.get(case_id, [])
            items = [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]
            self.log_audit(
                actor=actor,
                action="LIST_CASE_EVIDENCE",
                case_id=case_id,
                ip_address=ip_address,
                details={"count": len(items)},
            )
            return items

    def verify_integrity(
        self,
        evidence_id: str,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> IntegrityVerificationResult:
        with self._lock:
            item = self._evidence.get(evidence_id)
            now = datetime.now(timezone.utc)
            if not item:
                raise KeyError(f"Evidence '{evidence_id}' not found.")

            computed_hash = compute_sha256(item.raw_payload)
            is_valid = computed_hash.lower() == item.sha256_hash.lower()
            status_text = "VERIFIED_AUTHENTIC" if is_valid else "TAMPER_DETECTED"

            result = IntegrityVerificationResult(
                evidence_id=evidence_id,
                case_id=item.case_id,
                verified=is_valid,
                stored_hash=item.sha256_hash,
                computed_hash=computed_hash,
                verified_at=now,
                status=status_text,
                details="SHA-256 cryptographic digest matches canonical stored hash."
                if is_valid
                else "CRITICAL ALERT: Evidence payload has been modified or corrupted! (TAMPER DETECTED)",
            )

            self.log_audit(
                actor=actor,
                action="VERIFY_INTEGRITY",
                evidence_id=evidence_id,
                case_id=item.case_id,
                ip_address=ip_address,
                details={"verified": is_valid, "computed_hash": computed_hash},
            )
            return result

    def verify_all_case_evidence(
        self,
        case_id: str,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> List[IntegrityVerificationResult]:
        with self._lock:
            evidence_ids = self._case_index.get(case_id, [])
            results = [
                self.verify_integrity(eid, actor=actor, ip_address=ip_address)
                for eid in evidence_ids
                if eid in self._evidence
            ]
            return results

    def _add_timeline_event_internal(self, event: TimelineEvent) -> None:
        if event.case_id not in self._timeline_events:
            self._timeline_events[event.case_id] = []
        self._timeline_events[event.case_id].append(event)
        self._timeline_events[event.case_id].sort(key=lambda e: e.timestamp)

    def add_timeline_event(
        self,
        event: TimelineEvent,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> TimelineEvent:
        with self._lock:
            self._add_timeline_event_internal(event)
            self.log_audit(
                actor=actor,
                action="TIMELINE_EVENT_ADDED",
                case_id=event.case_id,
                evidence_id=event.evidence_id,
                ip_address=ip_address,
                details={"event_type": event.event_type, "summary": event.summary},
            )
            return event

    def get_case_timeline(
        self,
        case_id: str,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> CaseTimeline:
        with self._lock:
            events = self._timeline_events.get(case_id, [])
            events_sorted = sorted(events, key=lambda e: e.timestamp)
            self.log_audit(
                actor=actor,
                action="TIMELINE_QUERY",
                case_id=case_id,
                ip_address=ip_address,
                details={"total_events": len(events_sorted)},
            )
            return CaseTimeline(
                case_id=case_id,
                total_events=len(events_sorted),
                events=events_sorted,
            )

    def generate_copilot_draft(
        self,
        case_id: str,
        actor: str = "analyst",
        custom_instructions: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> CopilotInvestigationDraft:
        with self._lock:
            evidence_items = self.list_case_evidence(case_id, actor=actor)
            timeline = self._timeline_events.get(case_id, [])

            draft = self._copilot.generate_draft(
                case_id=case_id,
                evidence_items=evidence_items,
                timeline_events=timeline,
                custom_instructions=custom_instructions,
            )
            self._drafts[draft.draft_id] = draft

            self.log_audit(
                actor=actor,
                action="COPILOT_DRAFT_GENERATE",
                case_id=case_id,
                ip_address=ip_address,
                details={
                    "draft_id": draft.draft_id,
                    "citations_count": len(draft.evidence_citations),
                    "confidence_score": draft.confidence_score,
                },
            )
            return draft

    def generate_report(
        self,
        case_id: str,
        request: ReportGenerateRequest,
        actor: str = "analyst",
        ip_address: Optional[str] = None,
    ) -> AnalystInvestigationReport:
        with self._lock:
            evidence_items = self.list_case_evidence(case_id, actor=actor)
            timeline = self._timeline_events.get(case_id, [])
            draft: Optional[CopilotInvestigationDraft] = None

            if request.include_copilot_draft:
                draft = self.generate_copilot_draft(case_id, actor=actor)

            now = datetime.now(timezone.utc)
            report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"

            # Format comprehensive Markdown report
            exec_summary = (
                draft.executive_summary
                if draft
                else f"Comprehensive fraud investigation report for Case {case_id} concluded with disposition {request.disposition}."
            )
            findings_summary = (
                "\n".join(f"- {f}" for f in draft.key_findings)
                if draft
                else f"- Primary finding: {request.analyst_notes or 'Investigation closed.'}"
            )

            # Build markdown document
            lines = [
                f"# FinGuard AI — Formal Fraud Investigation Report",
                f"**Report ID:** `{report_id}` | **Case ID:** `{case_id}` | **Generated:** `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
                f"**Lead Investigator:** `{request.author}` | **Final Disposition:** `{request.disposition}`",
                "",
                "---",
                "",
                "## 1. Executive Summary",
                exec_summary,
                "",
                "## 2. Key Evidence & Cryptographic Verification",
                "| Evidence ID | Type | Source System | SHA-256 Digest | Status |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]

            for item in evidence_items:
                is_valid = verify_sha256(item.raw_payload, item.sha256_hash)
                status_icon = "Verified Authentic" if is_valid else "TAMPER DETECTED"
                lines.append(
                    f"| `{item.evidence_id}` | {item.evidence_type.value} | {item.source_system} | `{item.sha256_hash[:16]}...` | {status_icon} |"
                )

            lines.extend([
                "",
                "## 3. Chronological Forensic Timeline",
            ])
            for evt in timeline:
                lines.append(
                    f"- **{evt.timestamp.strftime('%H:%M:%S UTC')}** — [{evt.event_type}] ({evt.entity_id}): {evt.summary}"
                )

            if draft:
                lines.extend([
                    "",
                    "## 4. AI Investigation Copilot Synthesis",
                    f"**Copilot Confidence:** `{draft.confidence_score * 100:.1f}%` ({draft.confidence_rationale})",
                    "",
                    "### Threat Hypotheses:",
                ])
                for hyp in draft.threat_hypotheses:
                    lines.append(f"- {hyp}")
                lines.extend([
                    "",
                    "### Key Findings:",
                ])
                for f in draft.key_findings:
                    lines.append(f"- {f}")
                lines.extend([
                    "",
                    "### Recommended Remediation:",
                ])
                for rec in draft.recommended_actions:
                    lines.append(f"- {rec}")

            lines.extend([
                "",
                "## 5. Analyst Findings & Sign-Off",
                request.analyst_notes or "Evidence bundle reviewed and validated against compliance controls.",
                "",
                "**Cryptographic Sign-off:**",
                f"- **Investigator Signature:** `{request.author}`",
                f"- **Timestamp:** `{now.isoformat()}`",
                f"- **Compliance Audit Token:** `TOKEN-SHA256-{uuid.uuid4().hex[:12].upper()}`",
            ])

            report_md = "\n".join(lines)

            report = AnalystInvestigationReport(
                report_id=report_id,
                case_id=case_id,
                created_at=now,
                author=request.author,
                disposition=request.disposition,
                verified_evidence_count=len(evidence_items),
                timeline_event_count=len(timeline),
                copilot_draft_id=draft.draft_id if draft else None,
                executive_summary=exec_summary,
                findings_summary=findings_summary,
                report_markdown=report_md,
                sign_off={
                    "author": request.author,
                    "signed_at": now.isoformat(),
                    "disposition": request.disposition,
                },
            )

            self._reports[report_id] = report

            self.log_audit(
                actor=actor,
                action="REPORT_GENERATE",
                case_id=case_id,
                ip_address=ip_address,
                details={
                    "report_id": report_id,
                    "disposition": request.disposition,
                    "evidence_count": len(evidence_items),
                },
            )
            return report

    def get_report(self, report_id: str, actor: str = "analyst") -> Optional[AnalystInvestigationReport]:
        with self._lock:
            report = self._reports.get(report_id)
            if report:
                self.log_audit(
                    actor=actor,
                    action="REPORT_VIEW",
                    case_id=report.case_id,
                    details={"report_id": report_id},
                )
            return report

    def list_reports(self, case_id: Optional[str] = None) -> List[AnalystInvestigationReport]:
        with self._lock:
            if case_id:
                return [r for r in self._reports.values() if r.case_id == case_id]
            return list(self._reports.values())

    def get_audit_log(
        self,
        case_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[EvidenceAuditEntry]:
        with self._lock:
            logs = self._audit_log
            if case_id:
                logs = [e for e in logs if e.case_id == case_id]
            if evidence_id:
                logs = [e for e in logs if e.evidence_id == evidence_id]
            return list(reversed(logs))[:limit]

    def clear(self) -> None:
        with self._lock:
            self._evidence.clear()
            self._case_index.clear()
            self._timeline_events.clear()
            self._drafts.clear()
            self._reports.clear()
            self._audit_log.clear()

