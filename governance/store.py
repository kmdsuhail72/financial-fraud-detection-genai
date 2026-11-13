"""
FinGuard AI — Phase 23 Governance Store.
Thread-safe management of regulatory compliance controls, assessments, findings, remediations, and audit readiness KPIs.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from governance.catalogue import get_starter_controls
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


class GovernanceStore:
    """Thread-safe store for regulatory compliance catalogue, assessments, findings, and audit KPIs."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._controls: Dict[str, GovernanceControl] = {}
        self._findings: Dict[str, GovernanceFinding] = {}
        self._audit_log: List[GovernanceAuditEvent] = []
        self._reset_catalogue()

    def _reset_catalogue(self) -> None:
        self._controls.clear()
        for ctrl in get_starter_controls():
            self._controls[ctrl.control_id] = ctrl

    def log_audit(
        self,
        actor: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> GovernanceAuditEvent:
        entry = GovernanceAuditEvent(
            actor=actor,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
        with self._lock:
            self._audit_log.append(entry)
        return entry

    def list_controls(
        self,
        effectiveness: Optional[ControlEffectiveness] = None,
        framework: Optional[FrameworkType] = None,
        domain: Optional[str] = None,
    ) -> List[GovernanceControl]:
        with self._lock:
            results = []
            for ctrl in self._controls.values():
                if effectiveness and ctrl.effectiveness != effectiveness:
                    continue
                if domain and ctrl.domain.lower() != domain.lower():
                    continue
                if framework:
                    has_fw = any(m.framework == framework for m in ctrl.framework_mappings)
                    if not has_fw:
                        continue
                results.append(ctrl)
            return sorted(results, key=lambda c: c.control_id)

    def get_control(self, control_id: str) -> Optional[GovernanceControl]:
        with self._lock:
            return self._controls.get(control_id)

    def assess_control(
        self, control_id: str, request: ControlAssessmentRequest, actor: str = "compliance.auditor"
    ) -> GovernanceControl:
        with self._lock:
            ctrl = self._controls.get(control_id)
            if not ctrl:
                raise KeyError(f"Control '{control_id}' not found in catalogue.")

            now = datetime.now(timezone.utc)
            old_eff = ctrl.effectiveness
            ctrl.effectiveness = request.effectiveness
            ctrl.assessor_rationale = request.assessor_rationale
            ctrl.last_assessed_at = now
            ctrl.assessed_by = request.assessor or actor

            if request.evidence_references:
                for ref in request.evidence_references:
                    if ref not in ctrl.evidence_references:
                        ctrl.evidence_references.append(ref)

            self.log_audit(
                actor=actor,
                event_type="CONTROL_ASSESSED",
                entity_type="CONTROL",
                entity_id=control_id,
                details={
                    "old_effectiveness": old_eff.value,
                    "new_effectiveness": request.effectiveness.value,
                    "rationale": request.assessor_rationale,
                    "evidence_refs": request.evidence_references,
                },
            )
            return ctrl

    def list_findings(
        self,
        severity: Optional[FindingSeverity] = None,
        status: Optional[RemediationStatus] = None,
        control_id: Optional[str] = None,
    ) -> List[GovernanceFinding]:
        with self._lock:
            results = []
            for f in self._findings.values():
                if severity and f.severity != severity:
                    continue
                if status and f.status != status:
                    continue
                if control_id and f.control_id != control_id:
                    continue
                results.append(f)
            return sorted(results, key=lambda x: x.created_at, reverse=True)

    def get_finding(self, finding_id: str) -> Optional[GovernanceFinding]:
        with self._lock:
            return self._findings.get(finding_id)

    def create_finding(
        self, request: FindingCreateRequest, actor: str = "compliance.auditor"
    ) -> GovernanceFinding:
        with self._lock:
            if request.control_id not in self._controls:
                raise KeyError(f"Referenced control '{request.control_id}' does not exist.")

            now = datetime.now(timezone.utc)
            finding = GovernanceFinding(
                control_id=request.control_id,
                title=request.title,
                description=request.description,
                severity=request.severity,
                status=RemediationStatus.OPEN,
                owner=request.owner,
                due_date=request.due_date,
                created_at=now,
                updated_at=now,
            )
            self._findings[finding.finding_id] = finding

            self.log_audit(
                actor=actor,
                event_type="FINDING_CREATED",
                entity_type="FINDING",
                entity_id=finding.finding_id,
                details={
                    "control_id": request.control_id,
                    "severity": request.severity.value,
                    "owner": request.owner,
                },
            )
            return finding

    def remediate_finding(
        self, finding_id: str, request: FindingRemediateRequest, actor: str = "security.lead"
    ) -> GovernanceFinding:
        with self._lock:
            finding = self._findings.get(finding_id)
            if not finding:
                raise KeyError(f"Finding '{finding_id}' not found.")

            now = datetime.now(timezone.utc)
            old_status = finding.status
            finding.status = request.status
            finding.remediation_notes = request.remediation_notes
            finding.updated_at = now
            if request.status == RemediationStatus.VERIFIED:
                finding.verified_by = request.remediated_by or actor

            self.log_audit(
                actor=actor,
                event_type="FINDING_REMEDIATED",
                entity_type="FINDING",
                entity_id=finding_id,
                details={
                    "old_status": old_status.value,
                    "new_status": request.status.value,
                    "remediation_notes": request.remediation_notes,
                },
            )
            return finding

    def list_audit_events(
        self, entity_id: Optional[str] = None, limit: int = 100
    ) -> List[GovernanceAuditEvent]:
        with self._lock:
            events = self._audit_log
            if entity_id:
                events = [e for e in events if e.entity_id == entity_id]
            return list(reversed(events))[:limit]

    def calculate_readiness(self) -> ComplianceReadinessReport:
        with self._lock:
            controls = list(self._controls.values())
            findings = list(self._findings.values())
            now = datetime.now(timezone.utc)

            effective = sum(1 for c in controls if c.effectiveness == ControlEffectiveness.EFFECTIVE)
            partially = sum(1 for c in controls if c.effectiveness == ControlEffectiveness.PARTIALLY_EFFECTIVE)
            ineffective = sum(1 for c in controls if c.effectiveness == ControlEffectiveness.INEFFECTIVE)
            not_applicable = sum(1 for c in controls if c.effectiveness == ControlEffectiveness.NOT_APPLICABLE)

            applicable_count = len(controls) - not_applicable
            overall_pct = (
                ((effective * 1.0 + partially * 0.5) / applicable_count * 100.0)
                if applicable_count > 0
                else 100.0
            )

            # Framework breakdowns
            framework_breakdown: Dict[str, float] = {}
            for fw in [FrameworkType.SOC2, FrameworkType.ISO27001, FrameworkType.PCI_DSS]:
                fw_controls = [c for c in controls if any(m.framework == fw for m in c.framework_mappings)]
                fw_app = [c for c in fw_controls if c.effectiveness != ControlEffectiveness.NOT_APPLICABLE]
                if fw_app:
                    fw_eff = sum(1 for c in fw_app if c.effectiveness == ControlEffectiveness.EFFECTIVE)
                    fw_part = sum(1 for c in fw_app if c.effectiveness == ControlEffectiveness.PARTIALLY_EFFECTIVE)
                    fw_pct = ((fw_eff * 1.0 + fw_part * 0.5) / len(fw_app)) * 100.0
                    framework_breakdown[fw.value] = round(fw_pct, 1)
                else:
                    framework_breakdown[fw.value] = 100.0

            open_findings = sum(1 for f in findings if f.status in (RemediationStatus.OPEN, RemediationStatus.IN_PROGRESS))
            critical_findings = sum(
                1 for f in findings
                if f.severity == FindingSeverity.CRITICAL and f.status in (RemediationStatus.OPEN, RemediationStatus.IN_PROGRESS)
            )

            return ComplianceReadinessReport(
                generated_at=now,
                overall_readiness_pct=round(overall_pct, 1),
                effective_controls_count=effective,
                partially_effective_count=partially,
                ineffective_count=ineffective,
                not_applicable_count=not_applicable,
                total_controls=len(controls),
                framework_breakdown=framework_breakdown,
                open_findings_count=open_findings,
                critical_findings_count=critical_findings,
                controls=controls,
                findings=findings,
            )

    def clear(self) -> None:
        with self._lock:
            self._reset_catalogue()
            self._findings.clear()
            self._audit_log.clear()

