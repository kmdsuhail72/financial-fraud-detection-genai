"""
FinGuard AI — Phase 26: Identity Document Verification Test Suite.
Validates:
1. Health check endpoint (/documents/verification/health)
2. Document intake supporting PDF, JPEG, and PNG formats
3. SHA-256 digest computation & tamper detection
4. Field consistency matching on exact values
5. Fuzzy field consistency on partial/reordered tokens
6. Field mismatch detection flagging INCONSISTENT_FIELDS
7. Customer identity document timeline retrieval
8. Analyst verification assessment & audit trail tracking
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from document_verification.integrity import compute_sha256
from document_verification.models import DocumentFormat, DocumentCategory, VerificationStatus


@pytest.fixture
def client():
    return TestClient(app)


def test_verification_health_endpoint(client):
    """1. Test health check on /documents/verification/health."""
    resp = client.get("/documents/verification/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "document_verification"


def test_document_intake_formats(client):
    """2. Test ingesting documents in PDF, JPEG, and PNG formats."""
    formats = [
        ("PDF", "doc_test.pdf", "application/pdf"),
        ("JPEG", "doc_test.jpeg", "image/jpeg"),
        ("PNG", "doc_test.png", "image/png"),
    ]

    for fmt, fname, expected_mime in formats:
        payload = {
            "customer_id": "CUST-FMT-TEST-01",
            "document_category": "PASSPORT",
            "file_format": fmt,
            "file_name": fname,
            "content_raw": f"SIMULATED_CONTENT_FOR_{fmt}",
            "issuing_country": "US",
            "extracted_fields": {"full_name": "Format Tester", "dob": "1990-01-01"},
            "customer_profile_expected": {"full_name": "Format Tester", "dob": "1990-01-01"}
        }
        resp = client.post("/documents/verification/intake", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_metadata"]["file_format"] == fmt
        assert data["document_metadata"]["mime_type"] == expected_mime
        assert data["document_metadata"]["file_size_bytes"] > 0
        assert len(data["sha256_hash"]) == 64


def test_sha256_digest_and_tamper_detection(client):
    """3. Test SHA-256 calculation and tamper detection on modified payload."""
    original_content = "AUTHENTIC_GOVERNMENT_ISSUED_PASSPORT_BYTE_STREAM_v1"
    expected_hash = compute_sha256(original_content)

    payload = {
        "customer_id": "CUST-TAMPER-TEST",
        "document_category": "PASSPORT",
        "file_format": "PDF",
        "file_name": "authentic_passport.pdf",
        "content_raw": original_content,
        "issuing_country": "US",
        "extracted_fields": {"full_name": "John Connor"},
        "customer_profile_expected": {"full_name": "John Connor"}
    }
    resp = client.post("/documents/verification/intake", json=payload)
    assert resp.status_code == 201
    ver_rec = resp.json()
    vid = ver_rec["verification_id"]
    assert ver_rec["sha256_hash"].lower() == expected_hash.lower()

    # 3a. Verify authentic check
    check_auth = client.post(
        f"/documents/verification/records/{vid}/tamper-check",
        json={"modified_content_raw": original_content}
    )
    assert check_auth.status_code == 200
    assert check_auth.json()["is_authentic"] is True

    # 3b. Verify altered/tampered check
    tampered_content = "TAMPERED_GOVERNMENT_ISSUED_PASSPORT_BYTE_STREAM_v1_MODIFIED"
    check_tamper = client.post(
        f"/documents/verification/records/{vid}/tamper-check",
        json={"modified_content_raw": tampered_content}
    )
    assert check_tamper.status_code == 200
    tamper_data = check_tamper.json()
    assert tamper_data["is_authentic"] is False
    assert tamper_data["current_status"] == "TAMPER_DETECTED"


def test_field_consistency_exact_match(client):
    """4. Test field consistency when document fields match customer profile."""
    payload = {
        "customer_id": "CUST-MATCH-01",
        "document_category": "NATIONAL_ID",
        "file_format": "JPEG",
        "file_name": "id_card.jpeg",
        "content_raw": "SAMPLE_ID_CARD_BYTES",
        "issuing_country": "GB",
        "extracted_fields": {
            "full_name": "Arthur Pendelton",
            "date_of_birth": "1968-11-20",
            "issuing_country": "GB"
        },
        "customer_profile_expected": {
            "full_name": "Arthur Pendelton",
            "date_of_birth": "1968-11-20",
            "issuing_country": "GB"
        }
    }
    resp = client.post("/documents/verification/intake", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    report = data["consistency_report"]
    assert report["is_consistent"] is True
    assert report["overall_consistency_score"] == 1.0
    assert report["mismatch_count"] == 0
    assert data["verification_status"] == "VERIFIED_AUTHENTIC_BYTES"


def test_field_consistency_partial_match_and_reorder(client):
    """5. Test fuzzy consistency when names have initials or reordered tokens."""
    payload = {
        "customer_id": "CUST-PARTIAL-01",
        "document_category": "PASSPORT",
        "file_format": "PDF",
        "file_name": "passport.pdf",
        "content_raw": "SAMPLE_PASSPORT_BYTES",
        "issuing_country": "US",
        "extracted_fields": {
            "full_name": "Connor, Sarah J.",
            "date_of_birth": "1984-05-12"
        },
        "customer_profile_expected": {
            "full_name": "Sarah Connor",
            "date_of_birth": "1984-05-12"
        }
    }
    resp = client.post("/documents/verification/intake", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    report = data["consistency_report"]
    assert report["is_consistent"] is True
    assert report["overall_consistency_score"] >= 0.85
    assert report["mismatch_count"] == 0


def test_field_consistency_mismatch_detection(client):
    """6. Test that conflicting field values trigger MISMATCH and flag INCONSISTENT_FIELDS."""
    payload = {
        "customer_id": "CUST-MISMATCH-01",
        "document_category": "PAN",
        "file_format": "PNG",
        "file_name": "pan_card.png",
        "content_raw": "SAMPLE_PAN_BYTES",
        "issuing_country": "IND",
        "extracted_fields": {
            "full_name": "Vikram Malhotra",
            "date_of_birth": "1975-08-14",
            "id_number": "ABCDE1234F"
        },
        "customer_profile_expected": {
            "full_name": "Rajesh Sharma",  # Critical Name Mismatch
            "date_of_birth": "1990-12-01",  # Critical DOB Mismatch
            "id_number": "ABCDE1234F"
        }
    }
    resp = client.post("/documents/verification/intake", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    report = data["consistency_report"]
    assert report["is_consistent"] is False
    assert report["mismatch_count"] >= 1
    assert data["verification_status"] == "INCONSISTENT_FIELDS"


def test_customer_identity_timeline(client):
    """7. Test retrieving chronological customer document history timeline."""
    cid = "CUST-TIMELINE-99"

    # Ingest document 1 (Passport)
    client.post("/documents/verification/intake", json={
        "customer_id": cid,
        "document_category": "PASSPORT",
        "file_format": "PDF",
        "file_name": "initial_passport.pdf",
        "content_raw": "PASSPORT_1_CONTENT",
        "issuing_country": "US",
        "extracted_fields": {"name": "Alice Timeline"}
    })

    # Ingest document 2 (Driving License)
    client.post("/documents/verification/intake", json={
        "customer_id": cid,
        "document_category": "DRIVING_LICENSE",
        "file_format": "JPEG",
        "file_name": "driver_license.jpeg",
        "content_raw": "DL_2_CONTENT",
        "issuing_country": "US",
        "extracted_fields": {"name": "Alice Timeline"}
    })

    # Fetch timeline
    resp = client.get(f"/documents/verification/customers/{cid}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert len(timeline) >= 2
    categories = [doc["document_metadata"]["document_category"] for doc in timeline]
    assert "PASSPORT" in categories
    assert "DRIVING_LICENSE" in categories


def test_analyst_assessment_and_audit_trail(client):
    """8. Test analyst assessment workflow and audit event tracking."""
    cid = "CUST-ASSESS-01"
    intake_resp = client.post("/documents/verification/intake", json={
        "customer_id": cid,
        "document_category": "PASSPORT",
        "file_format": "PDF",
        "file_name": "passport_for_review.pdf",
        "content_raw": "PASSPORT_RAW_FOR_ASSESSMENT",
        "issuing_country": "US",
        "extracted_fields": {"full_name": "Elena Rostova"},
        "customer_profile_expected": {"full_name": "Elena Rostova"}
    })
    vid = intake_resp.json()["verification_id"]

    # Analyst verifies document
    assess_payload = {
        "analyst_id": "senior-officer-chen",
        "decision": "VERIFY",
        "notes": "Hologram features and byte hashes inspected. Document verified authentic."
    }
    assess_resp = client.post(f"/documents/verification/records/{vid}/assess", json=assess_payload)
    assert assess_resp.status_code == 200
    assessed_data = assess_resp.json()
    assert assessed_data["verification_status"] == "VERIFIED_AUTHENTIC_BYTES"
    assert assessed_data["analyst_notes"] == assess_payload["notes"]

    # Verify audit trail
    audit_resp = client.get(f"/documents/verification/customers/{cid}/audit-trail")
    assert audit_resp.status_code == 200
    audit_events = audit_resp.json()
    assert len(audit_events) >= 2
    event_types = [e["event_type"] for e in audit_events]
    assert "DOCUMENT_INGESTED" in event_types
    assert "ANALYST_ASSESSMENT_COMPLETED" in event_types
