"""
FinGuard AI — Phase 22 Evidence Management & Digital Forensics Package.
"""
from evidence.hashing import compute_sha256, serialize_canonical_payload, verify_sha256
from evidence.copilot import EvidenceGroundedCopilot
from evidence.models import (
    AnalystInvestigationReport,
    CaseTimeline,
    CopilotInvestigationDraft,
    EvidenceAuditEntry,
    EvidenceCitation,
    EvidenceCollectRequest,
    EvidenceItem,
    EvidenceType,
    IntegrityVerificationResult,
    ReportGenerateRequest,
    TimelineEvent,
)
from evidence.store import EvidenceStore
from evidence.service import EvidenceService, get_evidence_service

__all__ = [
    "AnalystInvestigationReport",
    "CaseTimeline",
    "CopilotInvestigationDraft",
    "EvidenceAuditEntry",
    "EvidenceCitation",
    "EvidenceCollectRequest",
    "EvidenceGroundedCopilot",
    "EvidenceItem",
    "EvidenceService",
    "EvidenceStore",
    "EvidenceType",
    "IntegrityVerificationResult",
    "ReportGenerateRequest",
    "TimelineEvent",
    "compute_sha256",
    "get_evidence_service",
    "serialize_canonical_payload",
    "verify_sha256",
]

