"""
FinGuard AI — Phase 23 Enterprise Regulatory Compliance & Financial Crime Governance Models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class FrameworkType(str, Enum):
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI_DSS"
    FINCEN_AML = "FINCEN_AML"


class ControlEffectiveness(str, Enum):
    EFFECTIVE = "EFFECTIVE"
    PARTIALLY_EFFECTIVE = "PARTIALLY_EFFECTIVE"
    INEFFECTIVE = "INEFFECTIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RemediationStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    REMEDIATED = "REMEDIATED"
    VERIFIED = "VERIFIED"


class FrameworkMapping(BaseModel):
    model_config = ConfigDict(extra="ignore")
    framework: FrameworkType
    clause_or_requirement: str
    description: str


class GovernanceControl(BaseModel):
    model_config = ConfigDict(extra="ignore")
    control_id: str
    name: str
    domain: str
    description: str
    framework_mappings: List[FrameworkMapping] = Field(default_factory=list)
    effectiveness: ControlEffectiveness = ControlEffectiveness.PARTIALLY_EFFECTIVE
    evidence_references: List[str] = Field(default_factory=list)
    assessor_rationale: Optional[str] = None
    last_assessed_at: Optional[datetime] = None
    assessed_by: Optional[str] = None


class ControlAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    effectiveness: ControlEffectiveness
    assessor_rationale: str
    evidence_references: List[str] = Field(default_factory=list)
    assessor: Optional[str] = "compliance.auditor"


class GovernanceFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    finding_id: str = Field(default_factory=lambda: f"FND-{uuid.uuid4().hex[:8].upper()}")
    control_id: str
    title: str
    description: str
    severity: FindingSeverity
    status: RemediationStatus = RemediationStatus.OPEN
    owner: str
    due_date: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    remediation_notes: Optional[str] = None
    verified_by: Optional[str] = None


class FindingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    control_id: str
    title: str
    description: str
    severity: FindingSeverity = FindingSeverity.MEDIUM
    owner: str
    due_date: str


class FindingRemediateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: RemediationStatus
    remediation_notes: str
    remediated_by: Optional[str] = "security.lead"


class GovernanceAuditEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_id: str = Field(default_factory=lambda: f"GOV-AUD-{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str  # e.g., "CONTROL_ASSESSED", "FINDING_CREATED", "FINDING_REMEDIATED"
    actor: str
    entity_type: str  # "CONTROL", "FINDING", "REPORT"
    entity_id: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ComplianceReadinessReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    generated_at: datetime
    overall_readiness_pct: float
    effective_controls_count: int
    partially_effective_count: int
    ineffective_count: int
    not_applicable_count: int
    total_controls: int
    framework_breakdown: Dict[str, float]
    open_findings_count: int
    critical_findings_count: int
    controls: List[GovernanceControl]
    findings: List[GovernanceFinding]

