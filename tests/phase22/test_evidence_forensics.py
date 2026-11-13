"""
FinGuard AI — Phase 22 Digital Forensics & Evidence Management Test Suite.
Validates:
1. Health check endpoint (HTTP 200)
2. Evidence collection and canonical SHA-256 hash generation
3. SHA-256 cryptographic integrity verification (Authentic)
4. SHA-256 tamper detection (Tampered payload alert)
5. Case evidence chronological timeline
6. Evidence-grounded AI copilot draft with source citations
7. Analyst formal investigation report compilation with markdown export
8. Tamper-evident evidence access audit logging
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from evidence.service import get_evidence_service
from evidence.models import EvidenceType


@pytest.fixture(autouse=True)
def clean_evidence_store():
    """Clear evidence registry before each test run."""
    service = get_evidence_service()
    service.store.clear()
    yield
    service.store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_evidence_health_check(client):
    """1. Test health check on /evidence/health returns 200 OK."""
    resp = client.get("/evidence/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert "Phase 22" in data["phase"]


def test_evidence_collection_and_canonical_sha256(client):
    """2. Test evidence ingestion and canonical SHA-256 cryptographic digest computation."""
    payload = {
        "case_id": "CASE-TEST-001",
        "evidence_type": "TRANSACTION_RECORD",
        "title": "Wire Transfer High Velocity",
        "source_system": "CORE_LEDGER",
        "payload": {
            "transaction_id": "TXN-99881",
            "amount": 12500.0,
            "currency": "USD",
            "beneficiary": "BENE-4412",
        },
        "collector": "investigator.lead",
    }

    resp = client.post("/evidence/collect", json=payload)
    assert resp.status_code == 201
    item = resp.json()

    assert item["case_id"] == "CASE-TEST-001"
    assert item["evidence_id"].startswith("EVD-")
    assert len(item["sha256_hash"]) == 64  # Standard SHA-256 hex string length
    assert item["size_bytes"] > 0
    assert item["evidence_type"] == "TRANSACTION_RECORD"


def test_sha256_integrity_verification_authentic(client):
    """3. Test SHA-256 integrity verification passes for unmodified evidence."""
    # Collect evidence
    collect_resp = client.post(
        "/evidence/collect",
        json={
            "case_id": "CASE-VERIFY-001",
            "evidence_type": "DEVICE_FINGERPRINT",
            "title": "Android Device Telemetry",
            "payload": {"device_id": "DEV-5541", "rooted": True, "os": "Android 14"},
        },
    )
    evidence_id = collect_resp.json()["evidence_id"]
    original_hash = collect_resp.json()["sha256_hash"]

    # Verify integrity
    verify_resp = client.post(f"/evidence/{evidence_id}/verify")
    assert verify_resp.status_code == 200
    res = verify_resp.json()

    assert res["verified"] is True
    assert res["status"] == "VERIFIED_AUTHENTIC"
    assert res["stored_hash"] == original_hash
    assert res["computed_hash"] == original_hash


def test_sha256_tamper_detection(client):
    """4. Test SHA-256 detects tampering when evidence payload is modified in storage."""
    collect_resp = client.post(
        "/evidence/collect",
        json={
            "case_id": "CASE-TAMPER-001",
            "evidence_type": "NETWORK_FLOW_IP",
            "title": "Tor Exit Node Packet Log",
            "payload": {"ip_address": "198.51.100.12", "threat_score": 0.85},
        },
    )
    evidence_id = collect_resp.json()["evidence_id"]

    # Deliberately tamper with payload in store
    service = get_evidence_service()
    item = service.store._evidence[evidence_id]
    item.raw_payload["threat_score"] = 0.00  # Tampered!

    # Verify integrity detects tampering
    verify_resp = client.post(f"/evidence/{evidence_id}/verify")
    assert verify_resp.status_code == 200
    res = verify_resp.json()

    assert res["verified"] is False
    assert res["status"] == "TAMPER_DETECTED"
    assert res["stored_hash"] != res["computed_hash"]
    assert "TAMPER" in res["details"]


def test_case_evidence_timeline_chronological_ordering(client):
    """5. Test case evidence timeline gathers and orders events chronologically."""
    case_id = "CASE-TIME-001"

    # Ingest two evidence items
    client.post(
        "/evidence/collect",
        json={
            "case_id": case_id,
            "evidence_type": "AUTH_LOG",
            "title": "Initial Login Event",
            "payload": {"user_id": "usr-100", "status": "SUCCESS"},
        },
    )
    client.post(
        "/evidence/collect",
        json={
            "case_id": case_id,
            "evidence_type": "TRANSACTION_RECORD",
            "title": "Subsequent Transfer",
            "payload": {"amount": 7500.0, "currency": "USD"},
        },
    )

    # Fetch timeline
    timeline_resp = client.get(f"/cases/{case_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()

    assert timeline["case_id"] == case_id
    assert timeline["total_events"] >= 2
    assert len(timeline["events"]) >= 2
    # Check ordering
    timestamps = [e["timestamp"] for e in timeline["events"]]
    assert timestamps == sorted(timestamps)


def test_ai_investigation_copilot_draft_with_citations(client):
    """6. Test AI Investigation Copilot draft synthesizes evidence with explicit citations."""
    case_id = "CASE-COPILOT-001"

    # Ingest multiple disparate evidence types
    e1 = client.post(
        "/evidence/collect",
        json={
            "case_id": case_id,
            "evidence_type": "TRANSACTION_RECORD",
            "title": "Rapid Outbound Wire",
            "payload": {"amount": 9500.0, "currency": "USD", "channel": "MOBILE_APP"},
        },
    ).json()["evidence_id"]

    e2 = client.post(
        "/evidence/collect",
        json={
            "case_id": case_id,
            "evidence_type": "DEVICE_FINGERPRINT",
            "title": "New Emulated Device",
            "payload": {"device_id": "DEV-EMU-01", "is_new_device": True, "os": "Linux"},
        },
    ).json()["evidence_id"]

    e3 = client.post(
        "/evidence/collect",
        json={
            "case_id": case_id,
            "evidence_type": "NETWORK_FLOW_IP",
            "title": "Commercial Anonymizer IP",
            "payload": {"ip_address": "203.0.113.88", "is_proxy_or_vpn": True},
        },
    ).json()["evidence_id"]

    # Request AI copilot draft
    draft_resp = client.post(f"/cases/{case_id}/copilot/draft")
    assert draft_resp.status_code == 200
    draft = draft_resp.json()

    assert draft["case_id"] == case_id
    assert len(draft["threat_hypotheses"]) > 0
    assert len(draft["key_findings"]) >= 3
    assert len(draft["recommended_actions"]) > 0
    assert draft["confidence_score"] > 0.50

    # Ensure explicit evidence citations
    cited_ids = [c["evidence_id"] for c in draft["evidence_citations"]]
    assert e1 in cited_ids
    assert e2 in cited_ids
    assert e3 in cited_ids


def test_analyst_investigation_report_generation(client):
    """7. Test formal investigation report compilation and markdown output."""
    case_id = "CASE-REPORT-001"

    client.post(
        "/evidence/collect",
        json={
            "case_id": case_id,
            "evidence_type": "TRANSACTION_RECORD",
            "title": "Mule Smurfing Burst",
            "payload": {"amount": 4900.0, "currency": "USD"},
        },
    )

    # Generate Report
    report_req = {
        "author": "analyst.sarah@finguard.internal",
        "disposition": "CONFIRMED_FRAUD",
        "analyst_notes": "Organized fraud ring activity confirmed via mule network pattern.",
        "include_copilot_draft": True,
    }
    resp = client.post(f"/cases/{case_id}/reports", json=report_req)
    assert resp.status_code == 201
    report = resp.json()

    assert report["case_id"] == case_id
    assert report["author"] == "analyst.sarah@finguard.internal"
    assert report["disposition"] == "CONFIRMED_FRAUD"
    assert report["verified_evidence_count"] >= 1
    assert "## 1. Executive Summary" in report["report_markdown"]
    assert "## 2. Key Evidence & Cryptographic Verification" in report["report_markdown"]
    assert "Cryptographic Sign-off" in report["report_markdown"]

    # Verify report lookup
    get_resp = client.get(f"/reports/{report['report_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["report_id"] == report["report_id"]


def test_evidence_access_audit_logging(client):
    """8. Test tamper-evident audit logging records all evidence access and verification events."""
    case_id = "CASE-AUDIT-001"

    # Collect evidence -> triggers COLLECT audit
    collect_resp = client.post(
        "/evidence/collect",
        json={
            "case_id": case_id,
            "evidence_type": "DECISION_RECORD",
            "title": "Phase 20 Fusion Decision Record",
            "payload": {"risk_score": 0.94, "priority": "P0"},
        },
    )
    evidence_id = collect_resp.json()["evidence_id"]

    # View evidence -> triggers VIEW audit
    client.get(f"/evidence/{evidence_id}")

    # Verify integrity -> triggers VERIFY_INTEGRITY audit
    client.post(f"/evidence/{evidence_id}/verify")

    # Fetch audit log
    audit_resp = client.get(f"/evidence/audit?case_id={case_id}")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()

    actions = [e["action"] for e in logs]
    assert "COLLECT" in actions
    assert "VIEW" in actions
    assert "VERIFY_INTEGRITY" in actions

