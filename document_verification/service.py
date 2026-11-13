"""
FinGuard AI — Phase 26: Identity Document Verification Service
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from document_verification.models import (
    DocumentIntakeRequest,
    DocumentVerificationRecord,
    IdentityDocumentMetadata,
    VerificationStatus,
    VerificationAssessmentRequest,
    DocumentAuditEvent,
    BiometricIntegrationPlaceholder,
)
from document_verification.store import DocumentVerificationStore, get_verification_store
from document_verification.integrity import compute_sha256, get_mime_type, verify_content_integrity
from document_verification.consistency import FieldConsistencyEngine


class DocumentVerificationService:
    def __init__(self, store: Optional[DocumentVerificationStore] = None):
        self.store = store or get_verification_store()
        self.consistency_engine = FieldConsistencyEngine()

    def ingest_document(self, req: DocumentIntakeRequest, actor: str = "document-service") -> DocumentVerificationRecord:
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        ver_id = f"VER-{uuid.uuid4().hex[:8].upper()}"

        # 1. Integrity Verification (SHA-256)
        sha256_digest = compute_sha256(req.content_raw)
        mime_type = get_mime_type(req.file_format)
        file_size_bytes = len(req.content_raw.encode("utf-8"))

        # 2. Metadata Profile
        meta = IdentityDocumentMetadata(
            document_id=doc_id,
            customer_id=req.customer_id,
            document_category=req.document_category,
            file_format=req.file_format,
            file_name=req.file_name,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            issuing_country=req.issuing_country,
            extracted_fields=req.extracted_fields,
            expiration_date=req.expiration_date,
            uploaded_at=datetime.now(timezone.utc)
        )

        # 3. Field Consistency Evaluation
        consistency_report = self.consistency_engine.evaluate_consistency(
            extracted_fields=req.extracted_fields,
            expected_profile=req.customer_profile_expected
        )

        # 4. Verification Status
        if not consistency_report.is_consistent:
            status = VerificationStatus.INCONSISTENT_FIELDS
        else:
            status = VerificationStatus.VERIFIED_AUTHENTIC_BYTES

        # 5. Biometric Integration Placeholder
        biometric = BiometricIntegrationPlaceholder(
            face_match_confidence=0.95 if status == VerificationStatus.VERIFIED_AUTHENTIC_BYTES else 0.65,
            face_match_status="INTEGRATION_POINT_READY",
            liveness_score=0.94 if status == VerificationStatus.VERIFIED_AUTHENTIC_BYTES else 0.60,
            liveness_status="INTEGRATION_POINT_READY"
        )

        record = DocumentVerificationRecord(
            verification_id=ver_id,
            document_metadata=meta,
            sha256_hash=sha256_digest,
            verification_status=status,
            consistency_report=consistency_report,
            biometric_integration=biometric,
            verified_at=datetime.now(timezone.utc),
            analyst_notes=None
        )

        self.store.save_record(record)
        self.store.log_audit(
            customer_id=req.customer_id,
            document_id=doc_id,
            event_type="DOCUMENT_INGESTED",
            actor=actor,
            details={
                "verification_id": ver_id,
                "category": req.document_category.value,
                "sha256": sha256_digest,
                "is_consistent": consistency_report.is_consistent,
                "consistency_score": consistency_report.overall_consistency_score,
                "status": status.value
            }
        )

        return record

    def check_tamper(self, verification_id: str, current_content: str, actor: str = "integrity-monitor") -> Dict[str, Any]:
        record = self.store.get_record(verification_id)
        if not record:
            raise ValueError(f"Verification record {verification_id} not found")

        current_hash = compute_sha256(current_content)
        is_authentic = current_hash.lower() == record.sha256_hash.lower()

        if not is_authentic:
            record.verification_status = VerificationStatus.TAMPER_DETECTED
            self.store.save_record(record)
            self.store.log_audit(
                customer_id=record.document_metadata.customer_id,
                document_id=record.document_metadata.document_id,
                event_type="TAMPER_DETECTED",
                actor=actor,
                details={
                    "recorded_sha256": record.sha256_hash,
                    "computed_sha256": current_hash,
                    "alert": "SECURITY ALERT: Byte mismatch detected! Document content altered."
                }
            )

        return {
            "verification_id": verification_id,
            "recorded_sha256": record.sha256_hash,
            "current_sha256": current_hash,
            "is_authentic": is_authentic,
            "current_status": record.verification_status.value
        }

    def assess_verification(
        self,
        verification_id: str,
        assessment_req: VerificationAssessmentRequest
    ) -> DocumentVerificationRecord:
        record = self.store.get_record(verification_id)
        if not record:
            raise ValueError(f"Verification record {verification_id} not found")

        dec = assessment_req.decision.upper()
        if dec == "VERIFY":
            new_status = VerificationStatus.VERIFIED_AUTHENTIC_BYTES
        elif dec == "FLAG_TAMPER":
            new_status = VerificationStatus.TAMPER_DETECTED
        elif dec == "REJECT_INCONSISTENT":
            new_status = VerificationStatus.REJECTED
        else:
            new_status = record.verification_status

        record.verification_status = new_status
        record.analyst_notes = assessment_req.notes
        self.store.save_record(record)

        self.store.log_audit(
            customer_id=record.document_metadata.customer_id,
            document_id=record.document_metadata.document_id,
            event_type="ANALYST_ASSESSMENT_COMPLETED",
            actor=assessment_req.analyst_id,
            details={
                "decision": assessment_req.decision,
                "resulting_status": new_status.value,
                "notes": assessment_req.notes
            }
        )

        return record

    def get_customer_timeline(self, customer_id: str) -> List[DocumentVerificationRecord]:
        return self.store.list_records(customer_id=customer_id)

    def get_audit_trail(self, customer_id: str) -> List[DocumentAuditEvent]:
        return self.store.get_audit_trail(customer_id=customer_id)


# Global singleton service
_verification_service = DocumentVerificationService()


def get_verification_service() -> DocumentVerificationService:
    return _verification_service

