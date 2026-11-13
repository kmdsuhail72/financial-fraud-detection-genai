"""
FinGuard AI — Phase 26: Document Verification Store & Identity Timeline
"""
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from document_verification.models import (
    DocumentVerificationRecord,
    IdentityDocumentMetadata,
    FieldConsistencyReport,
    FieldConsistencyCheck,
    ConsistencyVerdict,
    VerificationStatus,
    DocumentCategory,
    DocumentFormat,
    DocumentAuditEvent,
    BiometricIntegrationPlaceholder,
)


class DocumentVerificationStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._records: Dict[str, DocumentVerificationRecord] = {}  # verification_id -> record
        self._doc_id_to_ver_id: Dict[str, str] = {}
        self._customer_timelines: Dict[str, List[str]] = {}  # customer_id -> list of ver_ids
        self._audit_events: Dict[str, List[DocumentAuditEvent]] = {}  # customer_id -> events
        self._seed_initial_data()

    def _seed_initial_data(self):
        """Seed realistic identity documents with timeline and audit trail."""
        # 1. Verified US Passport for Sarah Connor
        c1_id = "CUST-US-9011"
        v1_id = "VER-9011-PASS"
        meta1 = IdentityDocumentMetadata(
            document_id="DOC-9011-PASS",
            customer_id=c1_id,
            document_category=DocumentCategory.PASSPORT,
            file_format=DocumentFormat.PDF,
            file_name="passport_scan_s_connor.pdf",
            file_size_bytes=1048576,
            mime_type="application/pdf",
            issuing_country="US",
            extracted_fields={
                "full_name": "Sarah Connor",
                "date_of_birth": "1984-05-12",
                "issuing_country": "US",
                "document_number": "P884920442"
            },
            expiration_date="2032-05-12",
            uploaded_at=datetime.now(timezone.utc)
        )
        report1 = FieldConsistencyReport(
            checks=[
                FieldConsistencyCheck(
                    field_name="full_name",
                    customer_value="Sarah Connor",
                    document_value="Sarah Connor",
                    similarity_score=1.0,
                    verdict=ConsistencyVerdict.MATCH,
                    explanation="Exact match on full name."
                ),
                FieldConsistencyCheck(
                    field_name="date_of_birth",
                    customer_value="1984-05-12",
                    document_value="1984-05-12",
                    similarity_score=1.0,
                    verdict=ConsistencyVerdict.MATCH,
                    explanation="Exact match on date of birth."
                )
            ],
            overall_consistency_score=1.0,
            is_consistent=True,
            mismatch_count=0,
            notes="All extracted identity fields are perfectly consistent with customer record."
        )
        rec1 = DocumentVerificationRecord(
            verification_id=v1_id,
            document_metadata=meta1,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            verification_status=VerificationStatus.VERIFIED_AUTHENTIC_BYTES,
            consistency_report=report1,
            biometric_integration=BiometricIntegrationPlaceholder(
                face_match_confidence=0.98,
                face_match_status="INTEGRATION_POINT_READY",
                liveness_score=0.96,
                liveness_status="INTEGRATION_POINT_READY"
            ),
            analyst_notes="Primary passport verified authentic against customer KYC declaration."
        )
        self._records[v1_id] = rec1
        self._doc_id_to_ver_id[meta1.document_id] = v1_id
        self._customer_timelines[c1_id] = [v1_id]
        self._log_audit_internal(
            customer_id=c1_id,
            document_id=meta1.document_id,
            event_type="DOCUMENT_INGESTED",
            actor="system",
            details={"file_name": meta1.file_name, "sha256": rec1.sha256_hash}
        )

        # 2. National ID with Partial Match for Arthur Pendelton
        c2_id = "CUST-GB-8840"
        v2_id = "VER-8840-ID"
        meta2 = IdentityDocumentMetadata(
            document_id="DOC-8840-ID",
            customer_id=c2_id,
            document_category=DocumentCategory.NATIONAL_ID,
            file_format=DocumentFormat.JPEG,
            file_name="uk_national_id_card.jpeg",
            file_size_bytes=524288,
            mime_type="image/jpeg",
            issuing_country="GB",
            extracted_fields={
                "full_name": "Arthur J. Pendelton",
                "date_of_birth": "1968-11-20",
                "issuing_country": "GB",
                "document_number": "UK901928491"
            },
            expiration_date="2028-11-20",
            uploaded_at=datetime.now(timezone.utc)
        )
        report2 = FieldConsistencyReport(
            checks=[
                FieldConsistencyCheck(
                    field_name="full_name",
                    customer_value="Arthur Pendelton",
                    document_value="Arthur J. Pendelton",
                    similarity_score=0.88,
                    verdict=ConsistencyVerdict.PARTIAL_MATCH,
                    explanation="Partial match due to middle initial 'J.' present on ID."
                ),
                FieldConsistencyCheck(
                    field_name="date_of_birth",
                    customer_value="1968-11-20",
                    document_value="1968-11-20",
                    similarity_score=1.0,
                    verdict=ConsistencyVerdict.MATCH,
                    explanation="Exact match on date of birth."
                )
            ],
            overall_consistency_score=0.94,
            is_consistent=True,
            mismatch_count=0,
            notes="Document exhibits minor name formatting variance; acceptable for EDD."
        )
        rec2 = DocumentVerificationRecord(
            verification_id=v2_id,
            document_metadata=meta2,
            sha256_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            verification_status=VerificationStatus.VERIFIED_AUTHENTIC_BYTES,
            consistency_report=report2,
            analyst_notes="UK National ID accepted with middle initial variance noted."
        )
        self._records[v2_id] = rec2
        self._doc_id_to_ver_id[meta2.document_id] = v2_id
        self._customer_timelines[c2_id] = [v2_id]
        self._log_audit_internal(
            customer_id=c2_id,
            document_id=meta2.document_id,
            event_type="DOCUMENT_INGESTED",
            actor="system",
            details={"file_name": meta2.file_name}
        )

    def _log_audit_internal(self, customer_id: str, document_id: str, event_type: str, actor: str, details: Dict):
        event = DocumentAuditEvent(
            event_id=f"DOC-AUD-{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            document_id=document_id,
            event_type=event_type,
            actor=actor,
            timestamp=datetime.now(timezone.utc),
            details=details
        )
        if customer_id not in self._audit_events:
            self._audit_events[customer_id] = []
        self._audit_events[customer_id].append(event)

    def save_record(self, record: DocumentVerificationRecord) -> DocumentVerificationRecord:
        with self._lock:
            self._records[record.verification_id] = record
            self._doc_id_to_ver_id[record.document_metadata.document_id] = record.verification_id
            cid = record.document_metadata.customer_id
            if cid not in self._customer_timelines:
                self._customer_timelines[cid] = []
            if record.verification_id not in self._customer_timelines[cid]:
                self._customer_timelines[cid].append(record.verification_id)
            return record

    def get_record(self, verification_id: str) -> Optional[DocumentVerificationRecord]:
        with self._lock:
            return self._records.get(verification_id)

    def get_record_by_doc_id(self, document_id: str) -> Optional[DocumentVerificationRecord]:
        with self._lock:
            vid = self._doc_id_to_ver_id.get(document_id)
            return self._records.get(vid) if vid else None

    def list_records(self, customer_id: Optional[str] = None) -> List[DocumentVerificationRecord]:
        with self._lock:
            if customer_id:
                vids = self._customer_timelines.get(customer_id, [])
                return [self._records[vid] for vid in vids if vid in self._records]
            return sorted(list(self._records.values()), key=lambda r: r.verified_at, reverse=True)

    def log_audit(self, customer_id: str, document_id: str, event_type: str, actor: str, details: Dict) -> DocumentAuditEvent:
        with self._lock:
            event = DocumentAuditEvent(
                event_id=f"DOC-AUD-{uuid.uuid4().hex[:8].upper()}",
                customer_id=customer_id,
                document_id=document_id,
                event_type=event_type,
                actor=actor,
                timestamp=datetime.now(timezone.utc),
                details=details
            )
            if customer_id not in self._audit_events:
                self._audit_events[customer_id] = []
            self._audit_events[customer_id].append(event)
            return event

    def get_audit_trail(self, customer_id: str) -> List[DocumentAuditEvent]:
        with self._lock:
            return sorted(
                self._audit_events.get(customer_id, []),
                key=lambda e: e.timestamp,
                reverse=True
            )


# Global singleton instance
_verification_store = DocumentVerificationStore()


def get_verification_store() -> DocumentVerificationStore:
    return _verification_store

