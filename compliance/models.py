"""Pydantic Models for FinGuard AI Compliance and Risk Management."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ComplianceFramework(str, Enum):
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI_DSS"
    RBI_CYBER = "RBI_CYBER"


class ControlStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    IN_PROGRESS = "IN_PROGRESS"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    REMEDIATED = "REMEDIATED"
    SUPPRESSED = "SUPPRESSED"


class EvidenceArtifact(BaseModel):
    """Raw evidence collected from AWS services or local security scans."""
    evidence_id: str
    name: str
    source: str  # CloudTrail, AWSConfig, KMS, Cognito, S3, etc.
    collected_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: Dict[str, Any] = Field(default_factory=dict)
    s3_uri: Optional[str] = None


class ControlMapping(BaseModel):
    """Reference control mapping for SOC 2 or ISO 27001."""
    control_id: str
    framework: ComplianceFramework
    title: str
    description: str
    status: ControlStatus = ControlStatus.IN_PROGRESS
    mapped_services: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    remediation_guidance: Optional[str] = None


class SecurityFinding(BaseModel):
    """Actionable security risk or non-compliance finding."""
    finding_id: str
    title: str
    description: str
    severity: FindingSeverity
    status: FindingStatus = FindingStatus.OPEN
    source: str  # GuardDuty, SecurityHub, AWSConfig, IAM, InternalScanner
    resource_id: str
    resource_type: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    remediation_steps: List[str] = Field(default_factory=list)


class CompliancePostureSummary(BaseModel):
    """Executive security posture metrics across all frameworks."""
    framework_scores: Dict[str, float] = Field(default_factory=dict)
    total_controls: int = 0
    compliant_controls: int = 0
    non_compliant_controls: int = 0
    compliance_percentage: float = 0.0
    critical_findings_count: int = 0
    high_findings_count: int = 0
    open_findings_count: int = 0
    evaluated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ComplianceReport(BaseModel):
    """Comprehensive compliance and audit evidence package."""
    report_id: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    environment: str = "production"
    posture: CompliancePostureSummary
    controls: List[ControlMapping] = Field(default_factory=list)
    findings: List[SecurityFinding] = Field(default_factory=list)
    evidence_artifacts: List[EvidenceArtifact] = Field(default_factory=list)

