"""Data Models for SOC Incident Management, Playbooks, and Remediation."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class IncidentSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class IncidentStatus(str, Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RemediationActionType(str, Enum):
    ISOLATE_HOST = "ISOLATE_HOST"
    REVOKE_CREDENTIALS = "REVOKE_CREDENTIALS"
    BLOCK_IP = "BLOCK_IP"
    QUARANTINE_S3_OBJECT = "QUARANTINE_S3_OBJECT"
    RESTRICT_USER = "RESTRICT_USER"
    ENFORCE_MFA = "ENFORCE_MFA"


class NormalizedSecurityEvent(BaseModel):
    """Normalized security alert from GuardDuty, Security Hub, CloudTrail, or FinGuard Fraud alerts."""
    event_id: str
    source: str  # GuardDuty, SecurityHub, CloudTrail, FinGuardFraud
    event_type: str
    severity: IncidentSeverity
    resource_id: str
    resource_type: str
    actor: Optional[str] = None
    fingerprint: str  # Hash for deduplication and correlation
    details: Dict[str, Any] = Field(default_factory=dict)
    received_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IncidentTimelineEntry(BaseModel):
    """Chronological event in the incident investigation lifecycle."""
    entry_id: str = Field(default_factory=lambda: f"TIME-{uuid.uuid4().hex[:8]}")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    author: str
    entry_type: str  # CREATION, ASSIGNMENT, AI_INVESTIGATION, PLAYBOOK_PROPOSED, APPROVAL, REMEDIATION, STATUS_CHANGE
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlaybookAction(BaseModel):
    """Discrete containment or remediation action within a SOC playbook."""
    action_id: str
    name: str
    action_type: RemediationActionType
    target_resource: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dry_run_plan: str
    rollback_guidance: str
    requires_approval: bool = True


class RemediationApproval(BaseModel):
    """Formal human approval record enforcing separation of duties."""
    approval_id: str = Field(default_factory=lambda: f"APPR-{uuid.uuid4().hex[:8]}")
    action_id: str
    requested_by: str
    requested_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    approved_at: Optional[str] = None
    approval_notes: Optional[str] = None


class RemediationReceipt(BaseModel):
    """Verification receipt recorded upon action execution."""
    receipt_id: str = Field(default_factory=lambda: f"RCPT-{uuid.uuid4().hex[:8]}")
    action_id: str
    target_resource: str
    executed_by: str
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    execution_status: str = "SIMULATED_SUCCESS"
    verification_results: Dict[str, Any] = Field(default_factory=dict)
    audit_log_ref: str = ""


class Playbook(BaseModel):
    """Standard Operating Procedure playbook for incident triage and containment."""
    playbook_id: str
    title: str
    description: str
    incident_type: str
    actions: List[PlaybookAction] = Field(default_factory=list)


class AIInvestigationBrief(BaseModel):
    """GenAI generated evidence brief and recommended hypothesis checks."""
    incident_id: str
    executive_summary: str
    threat_context: str
    hypotheses: List[str] = Field(default_factory=list)
    recommended_checks: List[str] = Field(default_factory=list)
    confidence_score: float = 0.88
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SOCIncident(BaseModel):
    """First-class enterprise SOC incident case."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.NEW
    source: str
    primary_resource_id: str
    primary_resource_type: str
    assigned_to: Optional[str] = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sla_target_minutes: int = 60
    sla_breached: bool = False
    correlated_event_count: int = 1
    correlated_event_ids: List[str] = Field(default_factory=list)
    timeline: List[IncidentTimelineEntry] = Field(default_factory=list)
    playbooks: List[Playbook] = Field(default_factory=list)
    approvals: List[RemediationApproval] = Field(default_factory=list)
    receipts: List[RemediationReceipt] = Field(default_factory=list)
    ai_brief: Optional[AIInvestigationBrief] = None


class SOCMetrics(BaseModel):
    """SOC operational telemetry and SLA performance metrics."""
    total_incidents: int
    open_incidents: int
    critical_incidents: int
    high_incidents: int
    contained_incidents: int
    resolved_incidents: int
    sla_compliance_percentage: float
    avg_containment_time_minutes: float

