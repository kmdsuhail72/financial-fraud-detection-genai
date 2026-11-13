"""
FinGuard AI — Phase 26: Identity Document Verification Models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    PDF = "PDF"
    JPEG = "JPEG"
    PNG = "PNG"


class DocumentCategory(str, Enum):
    PASSPORT = "PASSPORT"
    PAN = "PAN"
    AADHAAR = "AADHAAR"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    NATIONAL_ID = "NATIONAL_ID"
    VOTER_ID = "VOTER_ID"


class VerificationStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED_AUTHENTIC_BYTES = "VERIFIED_AUTHENTIC_BYTES"
    TAMPER_DETECTED = "TAMPER_DETECTED"
    INCONSISTENT_FIELDS = "INCONSISTENT_FIELDS"
    REJECTED = "REJECTED"


class ConsistencyVerdict(str, Enum):
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FieldConsistencyCheck(BaseModel):
    field_name: str
    customer_value: str
    document_value: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    verdict: ConsistencyVerdict
    explanation: str


class FieldConsistencyReport(BaseModel):
    checks: List[FieldConsistencyCheck]
    overall_consistency_score: float = Field(..., ge=0.0, le=1.0)
    is_consistent: bool
    mismatch_count: int
    notes: str


class BiometricIntegrationPlaceholder(BaseModel):
    face_match_confidence: Optional[float] = None
    face_match_status: str = "INTEGRATION_POINT_READY"
    liveness_score: Optional[float] = None
    liveness_status: str = "INTEGRATION_POINT_READY"
    notes: str = "Biometric and face-liveness APIs are integration points for downstream production models."


class IdentityDocumentMetadata(BaseModel):
    document_id: str
    customer_id: str
    document_category: DocumentCategory
    file_format: DocumentFormat
    file_name: str
    file_size_bytes: int
    mime_type: str
    issuing_country: str
    extracted_fields: Dict[str, str] = Field(default_factory=dict)
    expiration_date: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentVerificationRecord(BaseModel):
    verification_id: str
    document_metadata: IdentityDocumentMetadata
    sha256_hash: str
    verification_status: VerificationStatus
    consistency_report: FieldConsistencyReport
    biometric_integration: BiometricIntegrationPlaceholder = Field(default_factory=BiometricIntegrationPlaceholder)
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    analyst_notes: Optional[str] = None


class DocumentIntakeRequest(BaseModel):
    customer_id: str
    document_category: DocumentCategory
    file_format: DocumentFormat
    file_name: str
    content_raw: str = Field(..., description="Raw text, base64 or file payload bytes")
    issuing_country: str
    extracted_fields: Dict[str, str] = Field(default_factory=dict)
    customer_profile_expected: Dict[str, str] = Field(default_factory=dict)
    expiration_date: Optional[str] = None


class VerificationAssessmentRequest(BaseModel):
    analyst_id: str
    decision: str = Field(..., description="VERIFY, FLAG_TAMPER, REJECT_INCONSISTENT")
    notes: str


VerificationAssessment = VerificationAssessmentRequest


class TamperCheckRequest(BaseModel):
    modified_content_raw: str


class DocumentAuditEvent(BaseModel):
    event_id: str
    customer_id: str
    document_id: str
    event_type: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
