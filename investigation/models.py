"""
FinGuard AI — Fraud Investigation Case Domain Models & Schemas (Phase 8).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CasePriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ResolutionAction(str, Enum):
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ACCOUNT_RESTRICTED = "ACCOUNT_RESTRICTED"
    STEP_UP_VERIFIED = "STEP_UP_VERIFIED"
    DISMISSED = "DISMISSED"


class AnalystNote(BaseModel):
    note_id: str = Field(default_factory=lambda: f"NOTE-{uuid.uuid4().hex[:8]}")
    author: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content: str


class AuditTrailEntry(BaseModel):
    action: str
    performed_by: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)


class BedrockAISummary(BaseModel):
    executive_summary: str
    key_evidence: List[str]
    recommended_actions: List[str]
    alternative_explanations: List[str] = Field(default_factory=list)
    confidence_rationale: Optional[str] = None
    evidence_limitations: Optional[str] = None
    model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InvestigationCase(BaseModel):
    case_id: str
    transaction_id: str
    account_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    risk_score: float
    risk_level: str
    status: CaseStatus = CaseStatus.OPEN
    priority: CasePriority = CasePriority.HIGH
    assigned_to: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolution_action: Optional[ResolutionAction] = None
    resolution_notes: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    ai_summary: Optional[BedrockAISummary] = None
    notes: List[AnalystNote] = Field(default_factory=list)
    audit_trail: List[AuditTrailEntry] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="allow")


class CaseUpdateRequest(BaseModel):
    status: Optional[CaseStatus] = None
    assigned_to: Optional[str] = None
    note: Optional[str] = None
    resolution_action: Optional[ResolutionAction] = None
    resolution_notes: Optional[str] = None
    priority: Optional[CasePriority] = None

    model_config = ConfigDict(extra="allow")


class CaseListResponse(BaseModel):
    total: int
    cases: List[InvestigationCase]

