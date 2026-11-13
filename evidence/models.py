"""
FinGuard AI — Phase 22 Enterprise Fraud Investigation Evidence Management & Digital Forensics.
Domain models, schemas, and verification definitions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EvidenceType(str, Enum):
    TRANSACTION_RECORD = "TRANSACTION_RECORD"
    DEVICE_FINGERPRINT = "DEVICE_FINGERPRINT"
    NETWORK_FLOW_IP = "NETWORK_FLOW_IP"
    GRAPH_COMMUNITY_SNAPSHOT = "GRAPH_COMMUNITY_SNAPSHOT"
    UEBA_BASELINE_DEVIATION = "UEBA_BASELINE_DEVIATION"
    AUTH_LOG = "AUTH_LOG"
    DECISION_RECORD = "DECISION_RECORD"
    CUSTOM_DOCUMENT = "CUSTOM_DOCUMENT"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    evidence_id: str
    case_id: str
    evidence_type: EvidenceType
    title: str
    description: str
    source_system: str
    collected_at: datetime
    collector: str
    raw_payload: Dict[str, Any]
    sha256_hash: str
    size_bytes: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceCollectRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    case_id: str
    evidence_type: EvidenceType
    title: str
    description: Optional[str] = ""
    source_system: str = "FIN_GUARD_CORE"
    payload: Dict[str, Any]
    collector: Optional[str] = "analyst"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntegrityVerificationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    evidence_id: str
    case_id: str
    verified: bool
    stored_hash: str
    computed_hash: str
    verified_at: datetime
    status: str
    details: Optional[str] = None


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    case_id: str
    timestamp: datetime
    event_type: str
    entity_id: str
    summary: str
    evidence_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class CaseTimeline(BaseModel):
    model_config = ConfigDict(extra="ignore")
    case_id: str
    total_events: int
    events: List[TimelineEvent]


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    evidence_id: str
    evidence_type: EvidenceType
    title: str
    relevance: str


class CopilotInvestigationDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    draft_id: str = Field(default_factory=lambda: f"DRAFT-{uuid.uuid4().hex[:8].upper()}")
    case_id: str
    generated_at: datetime
    model_provider: str = "FinGuard-Bedrock-Copilot (Local Grounded Template)"
    executive_summary: str
    threat_hypotheses: List[str]
    key_findings: List[str]
    recommended_actions: List[str]
    evidence_citations: List[EvidenceCitation]
    confidence_score: float
    confidence_rationale: str


class ReportGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    author: str = "analyst"
    disposition: str = "CONFIRMED_FRAUD"
    analyst_notes: Optional[str] = None
    include_copilot_draft: bool = True


class AnalystInvestigationReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    report_id: str = Field(default_factory=lambda: f"REP-{uuid.uuid4().hex[:8].upper()}")
    case_id: str
    created_at: datetime
    author: str
    disposition: str
    verified_evidence_count: int
    timeline_event_count: int
    copilot_draft_id: Optional[str] = None
    executive_summary: str
    findings_summary: str
    report_markdown: str
    sign_off: Dict[str, Any]


class EvidenceAuditEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    audit_id: str = Field(default_factory=lambda: f"AUD-{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    action: str  # e.g. "COLLECT", "VIEW", "VERIFY_INTEGRITY", "TIMELINE_QUERY", "REPORT_GENERATE"
    evidence_id: Optional[str] = None
    case_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

