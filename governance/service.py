"""
FinGuard AI — Phase 23 Governance Service.
Singleton coordinator for regulatory compliance, control assessments, findings tracking, and audit readiness reports.
"""
from __future__ import annotations

import logging
from typing import List, Optional

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
from governance.store import GovernanceStore

logger = logging.getLogger("finguard-governance-service")


class GovernanceService:
    """Service layer managing enterprise regulatory compliance framework and audit automation."""

    def __init__(self, store: Optional[GovernanceStore] = None) -> None:
        self.store = store or GovernanceStore()

    def list_controls(
        self,
        effectiveness: Optional[ControlEffectiveness] = None,
        framework: Optional[FrameworkType] = None,
        domain: Optional[str] = None,
    ) -> List[GovernanceControl]:
        return self.store.list_controls(effectiveness=effectiveness, framework=framework, domain=domain)

    def get_control(self, control_id: str) -> Optional[GovernanceControl]:
        return self.store.get_control(control_id)

    def assess_control(
        self, control_id: str, request: ControlAssessmentRequest, actor: str = "compliance.auditor"
    ) -> GovernanceControl:
        return self.store.assess_control(control_id, request, actor=actor)

    def list_findings(
        self,
        severity: Optional[FindingSeverity] = None,
        status: Optional[RemediationStatus] = None,
        control_id: Optional[str] = None,
    ) -> List[GovernanceFinding]:
        return self.store.list_findings(severity=severity, status=status, control_id=control_id)

    def get_finding(self, finding_id: str) -> Optional[GovernanceFinding]:
        return self.store.get_finding(finding_id)

    def create_finding(
        self, request: FindingCreateRequest, actor: str = "compliance.auditor"
    ) -> GovernanceFinding:
        return self.store.create_finding(request, actor=actor)

    def remediate_finding(
        self, finding_id: str, request: FindingRemediateRequest, actor: str = "security.lead"
    ) -> GovernanceFinding:
        return self.store.remediate_finding(finding_id, request, actor=actor)

    def list_audit_events(
        self, entity_id: Optional[str] = None, limit: int = 100
    ) -> List[GovernanceAuditEvent]:
        return self.store.list_audit_events(entity_id=entity_id, limit=limit)

    def calculate_readiness(self) -> ComplianceReadinessReport:
        return self.store.calculate_readiness()

    def seed_initial_findings(self) -> None:
        """Seed representative findings for partially effective starter controls."""
        if not self.store._findings:
            self.create_finding(
                FindingCreateRequest(
                    control_id="CTRL-VULN-04",
                    title="Automated ECR Container Image Vulnerability Scan Missing",
                    description="Container images deployed to ECS/EKS must have automated Amazon Inspector CVE scanning enabled prior to promotion.",
                    severity=FindingSeverity.HIGH,
                    owner="devops.lead@finguard.internal",
                    due_date="2026-12-15",
                ),
                actor="system.seed",
            )
            self.create_finding(
                FindingCreateRequest(
                    control_id="CTRL-GOV-10",
                    title="Annual Third-Party External Penetration Test Scheduling",
                    description="PCI DSS 11.3 requires annual external network and web application penetration tests conducted by an independent certified QSA.",
                    severity=FindingSeverity.MEDIUM,
                    owner="ciso@finguard.internal",
                    due_date="2027-01-31",
                ),
                actor="system.seed",
            )


# Global singleton instance
_GLOBAL_GOVERNANCE_SERVICE: Optional[GovernanceService] = None


def get_governance_service() -> GovernanceService:
    global _GLOBAL_GOVERNANCE_SERVICE
    if _GLOBAL_GOVERNANCE_SERVICE is None:
        _GLOBAL_GOVERNANCE_SERVICE = GovernanceService()
        _GLOBAL_GOVERNANCE_SERVICE.seed_initial_findings()
    return _GLOBAL_GOVERNANCE_SERVICE

