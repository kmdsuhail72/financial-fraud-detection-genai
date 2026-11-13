"""
FinGuard AI — Phase 26: Identity Document Verification & Field Consistency
"""
from document_verification.models import (
    DocumentFormat,
    DocumentCategory,
    VerificationStatus,
    ConsistencyVerdict,
    IdentityDocumentMetadata,
    FieldConsistencyReport,
    VerificationAssessment,
    DocumentIntakeRequest,
    DocumentVerificationRecord,
)
from document_verification.service import DocumentVerificationService, get_verification_service

__all__ = [
    "DocumentFormat",
    "DocumentCategory",
    "VerificationStatus",
    "ConsistencyVerdict",
    "IdentityDocumentMetadata",
    "FieldConsistencyReport",
    "VerificationAssessment",
    "DocumentIntakeRequest",
    "DocumentVerificationRecord",
    "DocumentVerificationService",
    "get_verification_service",
]
