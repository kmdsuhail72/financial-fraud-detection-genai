"""
FinGuard AI — Phase 21 Enterprise Operations Queue, Alert Ingestion & SLA Management.
Domain models, schemas, and SLA definitions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AlertPriority(str, Enum):
    P0 = "P0"  # Critical (SLA: 30 mins)
    P1 = "P1"  # High (SLA: 2 hours)
    P2 = "P2"  # Medium (SLA: 8 hours)
    P3 = "P3"  # Low (SLA: 24 hours)


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ResolutionType(str, Enum):
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    SUSPICIOUS_CLEARED = "SUSPICIOUS_CLEARED"
    ACCOUNT_RESTRICTED = "ACCOUNT_RESTRICTED"
    DISMISSED = "DISMISSED"


# Priority SLA windows in minutes
SLA_MINUTES_BY_PRIORITY: Dict[AlertPriority, int] = {
    AlertPriority.P0: 30,
    AlertPriority.P1: 120,
    AlertPriority.P2: 480,
    AlertPriority.P3: 1440,
}


def calculate_priority_from_risk(risk_score: float) -> AlertPriority:
    """Map normalized risk score [0, 1] to AlertPriority tier."""
    if risk_score >= 0.90:
        return AlertPriority.P0
    elif risk_score >= 0.70:
        return AlertPriority.P1
    elif risk_score >= 0.35:
        return AlertPriority.P2
    return AlertPriority.P3


class ActivityLogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    activity_id: str = Field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str
    actor: str
    details: Dict[str, Any] = Field(default_factory=dict)


class AnalystNote(BaseModel):
    model_config = ConfigDict(extra="ignore")
    note_id: str = Field(default_factory=lambda: f"NOTE-{uuid.uuid4().hex[:8]}")
    author: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: str


class AlertIngestRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    alert_id: Optional[str] = None
    tenant_id: str = Field(default="default-tenant", description="Tenant identifier for multi-tenant isolation")
    idempotency_key: Optional[str] = Field(default=None, description="Optional tenant-scoped deduplication key")
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    account_id: Optional[str] = None
    amount: float = 0.0
    currency: str = "USD"
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Normalized risk score [0.0 - 1.0]")
    priority: Optional[AlertPriority] = Field(default=None, description="Explicit priority; auto-assigned if omitted")
    source: str = Field(default="DECISION_ENGINE", description="Originating detection pipeline")
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertIngestResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    alert_id: str
    case_id: str
    tenant_id: str
    idempotency_key: str
    priority: AlertPriority
    status: CaseStatus
    risk_score: float
    created_at: datetime
    sla_deadline: datetime
    is_duplicate: bool = False
    message: str


class CaseAssignRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    analyst_id: str
    assigned_by: Optional[str] = "supervisor"


class CaseStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: CaseStatus
    updated_by: str = "analyst"
    reason: Optional[str] = None


class CaseResolveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    resolution: str = Field(..., description="e.g. CONFIRMED_FRAUD, FALSE_POSITIVE")
    resolved_by: str = "analyst"
    notes: Optional[str] = None


class AnalystNoteRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    author: str = "analyst"
    content: Optional[str] = None
    note: Optional[str] = None

    def get_content(self) -> str:
        return (self.content or self.note or "").strip()


class OperationalCase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    case_id: str
    alert_id: str
    tenant_id: str
    idempotency_key: str
    transaction_id: Optional[str] = None
    customer_id: Optional[str] = None
    account_id: Optional[str] = None
    amount: float = 0.0
    currency: str = "USD"
    risk_score: float
    priority: AlertPriority
    status: CaseStatus = CaseStatus.OPEN
    assigned_to: Optional[str] = None
    source: str = "DECISION_ENGINE"
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
    sla_deadline: datetime
    sla_breached: bool = False
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    notes: List[AnalystNote] = Field(default_factory=list)
    history: List[ActivityLogEntry] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OperationsMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total_alerts: int
    total_cases: int
    open_cases: int
    in_review_cases: int
    escalated_cases: int
    resolved_cases: int
    closed_cases: int
    priority_breakdown: Dict[str, int]
    sla_breaches: int
    sla_breach_rate_pct: float
    sla_impending_breaches: int
    analyst_workload: Dict[str, int]
    avg_resolution_time_minutes: float

