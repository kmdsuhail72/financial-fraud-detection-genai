"""
FinGuard AI — Phase 25: KYC, CDD/EDD & Screening Data Models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CustomerType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    CORPORATE = "CORPORATE"


class OnboardingStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDD_REQUIRED = "EDD_REQUIRED"


class DocumentType(str, Enum):
    PASSPORT = "PASSPORT"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    TAX_ID = "TAX_ID"
    PROOF_OF_ADDRESS = "PROOF_OF_ADDRESS"
    CERTIFICATE_OF_INCORPORATION = "CERTIFICATE_OF_INCORPORATION"


class DocumentStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class ScreeningMatchCategory(str, Enum):
    PEP = "PEP"
    SANCTIONS = "SANCTIONS"
    ADVERSE_MEDIA = "ADVERSE_MEDIA"


class MatchConfidence(str, Enum):
    EXACT = "EXACT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CDDTier(str, Enum):
    SIMPLIFIED_SDD = "SIMPLIFIED_SDD"
    STANDARD_CDD = "STANDARD_CDD"
    ENHANCED_EDD = "ENHANCED_EDD"


class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED_EDD = "ESCALATED_EDD"
    REQUEST_INFO = "REQUEST_INFO"


class KYCDocument(BaseModel):
    document_id: str = Field(..., description="Unique document ID")
    document_type: DocumentType = Field(..., description="Type of verification document")
    issuing_country: str = Field(..., description="ISO 2 or 3 letter country code")
    document_number_masked: str = Field(..., description="Masked identification number")
    sha256_hash: str = Field(..., description="Cryptographic SHA-256 integrity hash of document content")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: DocumentStatus = Field(default=DocumentStatus.VERIFIED)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScreeningMatch(BaseModel):
    match_id: str
    category: ScreeningMatchCategory
    matched_entity_name: str
    entity_country: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    match_confidence: MatchConfidence
    source_reference: str
    snippet_or_reason: str


class CustomerRiskAssessment(BaseModel):
    risk_level: RiskLevel
    score: float = Field(..., ge=0.0, le=100.0)
    risk_factors: List[str] = Field(default_factory=list)
    cdd_tier: CDDTier
    explanation: str
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CustomerAuditEvent(BaseModel):
    event_id: str
    customer_id: str
    event_type: str
    actor: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


class CustomerProfile(BaseModel):
    customer_id: str
    customer_type: CustomerType
    full_name: str
    date_of_birth_or_inc: str
    nationality_or_country: str
    email: str
    phone: str
    tax_id_masked: str
    risk_assessment: CustomerRiskAssessment
    documents: List[KYCDocument] = Field(default_factory=list)
    screening_matches: List[ScreeningMatch] = Field(default_factory=list)
    onboarding_status: OnboardingStatus = Field(default=OnboardingStatus.PENDING_REVIEW)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None


class CustomerOnboardingRequest(BaseModel):
    customer_id: Optional[str] = None
    customer_type: CustomerType = CustomerType.INDIVIDUAL
    full_name: str
    date_of_birth_or_inc: str
    nationality_or_country: str
    email: str
    phone: str
    tax_id_masked: str
    initial_documents: Optional[List[KYCDocument]] = None


class DocumentUploadRequest(BaseModel):
    document_type: DocumentType
    issuing_country: str
    document_number_masked: str
    content_raw: Optional[str] = None
    provided_sha256: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ComplianceReviewRequest(BaseModel):
    decision: ReviewDecision
    analyst_id: str
    rationale: str
    edd_notes: Optional[str] = None

