"""
FinGuard AI — Phase 27: Synthetic Identity & Identity Graph Test Suite.
Validates:
1. Health check endpoint (/identity/graph/health)
2. Customer identity registration into graph
3. Collision detection across phones, devices, and emails
4. Subgraph ego network extraction
5. Explainable synthetic risk score & tier calculation
6. Identity ring cluster discovery (connected components)
7. Correlation with KYC & document verification metadata
8. Analyst review adjudication & audit trail tracking
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from identity_graph.service import get_identity_graph_service
from identity_graph.models import SyntheticRiskTier, InvestigationDecision


@pytest.fixture
def client():
    return TestClient(app)


def test_identity_graph_health_endpoint(client):
    """1. Test health check on /identity/graph/health."""
    resp = client.get("/identity/graph/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "identity_graph"


def test_customer_identity_registration(client):
    """2. Test registering a customer identity and attributes into graph."""
    payload = {
        "customer_id": "CUST-TEST-NEW-01",
        "full_name": "Marcus Aurelius",
        "phone": "+1-555-9090",
        "email": "marcus@rome-demo.org",
        "address": "1 Palatine Hill, Rome",
        "device_id": "DEV-IOS-9901",
        "ip_address": "198.51.100.99",
        "document_id": "DOC-9901-PASS",
        "kyc_status": "APPROVED",
        "doc_verification_status": "VERIFIED_AUTHENTIC_BYTES"
    }
    resp = client.post("/identity/graph/register", json=payload)
    assert resp.status_code == 201
    profile = resp.json()
    assert profile["customer_id"] == "CUST-TEST-NEW-01"
    assert profile["risk_score"] < 30.0  # Clean customer
    assert profile["risk_tier"] == "LOW"


def test_identity_collision_detection(client):
    """3. Test detecting collisions when two customers share a phone and device."""
    shared_phone = "+1-555-7777"
    shared_device = "DEV-COLLIDE-77"

    # Ingest Customer A
    client.post("/identity/graph/register", json={
        "customer_id": "CUST-COLLIDE-A",
        "full_name": "Identity Candidate A",
        "phone": shared_phone,
        "device_id": shared_device
    })

    # Ingest Customer B sharing phone and device
    client.post("/identity/graph/register", json={
        "customer_id": "CUST-COLLIDE-B",
        "full_name": "Identity Candidate B",
        "phone": shared_phone,
        "device_id": shared_device
    })

    resp = client.get("/identity/graph/collisions")
    assert resp.status_code == 200
    collisions = resp.json()
    assert len(collisions) >= 2

    shared_values = [c["shared_attribute_value"] for c in collisions]
    assert shared_phone in shared_values
    assert shared_device in shared_values

    # Verify both customers are listed in collision
    matching_col = next(c for c in collisions if c["shared_attribute_value"] == shared_phone)
    assert "CUST-COLLIDE-A" in matching_col["customer_ids"]
    assert "CUST-COLLIDE-B" in matching_col["customer_ids"]


def test_subgraph_ego_network_retrieval(client):
    """4. Test retrieving ego network around a specific customer."""
    resp = client.get("/identity/graph/subgraph?customer_id=CUST-US-9011&max_depth=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_nodes"] > 0
    node_ids = [n["node_id"] for n in data["nodes"]]
    assert "CUST-US-9011" in node_ids
    assert any(n["node_type"] == "PHONE" for n in data["nodes"])


def test_synthetic_identity_risk_scoring(client):
    """5. Test risk calculation on clean customer vs seeded synthetic ring member."""
    # 5a. Clean customer (Sarah Connor)
    r_clean = client.get("/identity/graph/customers/CUST-US-9011/risk")
    assert r_clean.status_code == 200
    clean_profile = r_clean.json()
    assert clean_profile["risk_tier"] == "LOW"
    assert clean_profile["collision_count"] == 0

    # 5b. Synthetic Ring Member (Alex Mercer)
    r_ring = client.get("/identity/graph/customers/CUST-SYN-001/risk")
    assert r_ring.status_code == 200
    ring_profile = r_ring.json()
    assert ring_profile["risk_tier"] in ["HIGH", "CRITICAL"]
    assert ring_profile["collision_count"] >= 2
    assert len(ring_profile["colliding_customers"]) >= 2
    assert "CUST-SYN-002" in ring_profile["colliding_customers"]


def test_identity_ring_cluster_discovery(client):
    """6. Test connected components discovery of the seeded synthetic ring."""
    resp = client.get("/identity/graph/clusters")
    assert resp.status_code == 200
    clusters = resp.json()
    assert len(clusters) >= 1

    # Find the ring containing CUST-SYN-001, CUST-SYN-002, CUST-SYN-003
    planted_cluster = next((cl for cl in clusters if "CUST-SYN-001" in cl["customer_ids"]), None)
    assert planted_cluster is not None
    assert planted_cluster["customer_count"] >= 3
    assert planted_cluster["cluster_risk_score"] >= 60.0
    assert planted_cluster["cluster_risk_tier"] in ["HIGH", "CRITICAL"]


def test_kyc_and_forensic_correlation(client):
    """7. Test that KYC and document verification status flags elevate synthetic risk."""
    # Register customer with EDD_REQUIRED and INCONSISTENT_FIELDS
    client.post("/identity/graph/register", json={
        "customer_id": "CUST-RISK-CORRELATION",
        "full_name": "Compromised Profile",
        "phone": "+1-555-4433",
        "kyc_status": "EDD_REQUIRED",
        "doc_verification_status": "INCONSISTENT_FIELDS"
    })

    resp = client.get("/identity/graph/customers/CUST-RISK-CORRELATION/risk")
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["risk_score"] >= 40.0  # Base (5) + KYC (15) + Forensic (25) = 45.0
    reasons = " ".join(profile["risk_reasons"])
    assert "EDD_REQUIRED" in reasons
    assert "INCONSISTENT_FIELDS" in reasons


def test_analyst_review_workflow_and_audit(client):
    """8. Test analyst review adjudication (FLAG_SYNTHETIC_RING) and audit trail logging."""
    cid = "CUST-SYN-002"
    review_payload = {
        "analyst_id": "fraud-investigator-dane",
        "decision": "FLAG_SYNTHETIC_RING",
        "rationale": "Applicant shares residential address, hardware device, and phone with known shell entity.",
        "escalate_to_sar": True
    }
    rev_resp = client.post(f"/identity/graph/customers/{cid}/review", json=review_payload)
    assert rev_resp.status_code == 200

    # Verify audit trail
    audit_resp = client.get(f"/identity/graph/customers/{cid}/audit-trail")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    assert len(events) >= 1
    review_event = next((e for e in events if e["event_type"] == "IDENTITY_INVESTIGATION_DECIDED"), None)
    assert review_event is not None
    assert review_event["actor"] == "fraud-investigator-dane"
    assert review_event["details"]["decision"] == "FLAG_SYNTHETIC_RING"
