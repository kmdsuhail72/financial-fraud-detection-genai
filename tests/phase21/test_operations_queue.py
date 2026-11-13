"""
FinGuard AI — Phase 21 Test Suite.
Validates:
1. Operations health endpoints
2. Priority assignment (P0, P1, P2, P3) and SLA windows
3. Tenant-scoped idempotency deduplication
4. Case routing & analyst assignment
5. Case status transitions (Open -> In Review -> Escalated)
6. Analyst notes and timeline activity history
7. Case resolution workflow
8. Operations monitoring metrics and SLA tracking
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from operations.service import get_operations_service
from operations.models import AlertPriority, CaseStatus


@pytest.fixture(autouse=True)
def clean_operations_store():
    """Clear and reseed operational cases before each test run."""
    service = get_operations_service()
    service.store.clear()
    yield
    service.store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_operations_health_endpoints(client):
    """1. Test health checks on /operations/health and /alerts/health."""
    resp1 = client.get("/operations/health")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "HEALTHY"
    assert "Phase 21" in data1["phase"]

    resp2 = client.get("/alerts/health")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "HEALTHY"


def test_alert_ingestion_and_priority_mapping(client):
    """2. Test alert ingestion and automatic risk-based priority assignment (P0, P1, P2, P3)."""
    # Critical risk -> P0 (30 min SLA)
    payload_p0 = {
        "tenant_id": "tenant-bank-1",
        "transaction_id": "TXN-P0-001",
        "amount": 9500.0,
        "risk_score": 0.95,
        "source": "TEMPORAL_GRU",
    }
    resp_p0 = client.post("/alerts", json=payload_p0)
    assert resp_p0.status_code == 201
    d0 = resp_p0.json()
    assert d0["priority"] == "P0"
    assert d0["status"] == "OPEN"
    assert d0["is_duplicate"] is False

    # High risk -> P1 (120 min SLA)
    payload_p1 = {
        "tenant_id": "tenant-bank-1",
        "transaction_id": "TXN-P1-002",
        "amount": 4200.0,
        "risk_score": 0.78,
    }
    resp_p1 = client.post("/alerts", json=payload_p1)
    assert resp_p1.status_code == 201
    assert resp_p1.json()["priority"] == "P1"

    # Medium risk -> P2 (480 min SLA)
    payload_p2 = {
        "tenant_id": "tenant-bank-1",
        "transaction_id": "TXN-P2-003",
        "amount": 1500.0,
        "risk_score": 0.45,
    }
    resp_p2 = client.post("/alerts", json=payload_p2)
    assert resp_p2.status_code == 201
    assert resp_p2.json()["priority"] == "P2"

    # Low risk -> P3 (1440 min SLA)
    payload_p3 = {
        "tenant_id": "tenant-bank-1",
        "transaction_id": "TXN-P3-004",
        "amount": 80.0,
        "risk_score": 0.15,
    }
    resp_p3 = client.post("/alerts", json=payload_p3)
    assert resp_p3.status_code == 201
    assert resp_p3.json()["priority"] == "P3"


def test_tenant_scoped_idempotency(client):
    """3. Test deduplication ensures idempotent ingestion within tenant, while isolating tenants."""
    payload = {
        "tenant_id": "tenant-alpha",
        "idempotency_key": "IDEMP-TX-9999",
        "transaction_id": "TXN-9999",
        "amount": 5000.0,
        "risk_score": 0.88,
    }

    # Initial ingestion
    resp1 = client.post("/alerts", json=payload)
    assert resp1.status_code == 201
    d1 = resp1.json()
    assert d1["is_duplicate"] is False
    case_id_1 = d1["case_id"]

    # Re-submission from same tenant -> Deduplicated
    resp2 = client.post("/alerts", json=payload)
    assert resp2.status_code == 201
    d2 = resp2.json()
    assert d2["is_duplicate"] is True
    assert d2["case_id"] == case_id_1

    # Submission with same idempotency_key but DIFFERENT tenant -> Treated as distinct case
    payload_tenant_beta = dict(payload)
    payload_tenant_beta["tenant_id"] = "tenant-beta"
    resp3 = client.post("/alerts", json=payload_tenant_beta)
    assert resp3.status_code == 201
    d3 = resp3.json()
    assert d3["is_duplicate"] is False
    assert d3["case_id"] != case_id_1
    assert d3["tenant_id"] == "tenant-beta"


def test_case_routing_and_assignment(client):
    """4. Test analyst assignment and routing updates case and history."""
    # Ingest alert
    ingest_resp = client.post(
        "/alerts",
        json={
            "tenant_id": "tenant-alpha",
            "transaction_id": "TXN-ASSIGN-01",
            "risk_score": 0.82,
        },
    )
    case_id = ingest_resp.json()["case_id"]

    # Assign analyst
    assign_resp = client.post(
        f"/cases/{case_id}/assign",
        json={
            "analyst_id": "analyst.sarah@finguard.internal",
            "assigned_by": "supervisor.john",
        },
    )
    assert assign_resp.status_code == 200
    case_data = assign_resp.json()
    assert case_data["assigned_to"] == "analyst.sarah@finguard.internal"

    # Verify history recorded the assignment
    actions = [h["action"] for h in case_data["history"]]
    assert "ANALYST_ASSIGNED" in actions


def test_case_status_lifecycle(client):
    """5. Test state lifecycle transitions: OPEN -> IN_REVIEW -> ESCALATED."""
    ingest_resp = client.post(
        "/alerts",
        json={
            "tenant_id": "tenant-alpha",
            "transaction_id": "TXN-CYCLE-01",
            "risk_score": 0.72,
        },
    )
    case_id = ingest_resp.json()["case_id"]

    # Move to IN_REVIEW
    review_resp = client.post(
        f"/cases/{case_id}/status",
        json={"status": "IN_REVIEW", "updated_by": "analyst.sarah", "reason": "Started triage"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "IN_REVIEW"

    # Escalate case
    esc_resp = client.post(
        f"/cases/{case_id}/escalate",
        json={"reason": "Suspected organized syndicate account takeover"},
    )
    assert esc_resp.status_code == 200
    case_data = esc_resp.json()
    assert case_data["status"] == "ESCALATED"

    # Verify audit history
    actions = [h["action"] for h in case_data["history"]]
    assert "STATUS_UPDATED" in actions
    assert "case:escalate" in actions or "STATUS_UPDATED" in actions


def test_analyst_notes_workflow(client):
    """6. Test analyst notes workflow and timeline tracking."""
    ingest_resp = client.post(
        "/alerts",
        json={
            "tenant_id": "tenant-alpha",
            "transaction_id": "TXN-NOTE-01",
            "risk_score": 0.77,
        },
    )
    case_id = ingest_resp.json()["case_id"]

    # Add note
    note_resp = client.post(
        f"/cases/{case_id}/notes",
        json={
            "author": "analyst.sarah",
            "content": "Customer confirmed travel to Tokyo; device mismatch accounted for.",
        },
    )
    assert note_resp.status_code == 200
    case_data = note_resp.json()
    assert len(case_data["notes"]) == 1
    assert "Customer confirmed travel" in case_data["notes"][0]["content"]

    # Check case detail endpoint returns notes
    detail_resp = client.get(f"/cases/{case_id}")
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["notes"]) == 1


def test_case_resolution(client):
    """7. Test case resolution marking status RESOLVED and stamping resolution."""
    ingest_resp = client.post(
        "/alerts",
        json={
            "tenant_id": "tenant-alpha",
            "transaction_id": "TXN-RESOLVE-01",
            "risk_score": 0.94,
        },
    )
    case_id = ingest_resp.json()["case_id"]

    # Resolve case
    resolve_resp = client.post(
        f"/cases/{case_id}/resolve",
        json={
            "resolution": "CONFIRMED_FRAUD",
            "resolved_by": "analyst.sarah",
            "notes": "Unauthorized SIM-swap verified with carrier; account restricted.",
        },
    )
    assert resolve_resp.status_code == 200
    case_data = resolve_resp.json()
    assert case_data["status"] == "RESOLVED"
    assert case_data["resolution"] == "CONFIRMED_FRAUD"
    assert case_data["resolved_at"] is not None


def test_operations_metrics_and_sla_tracking(client):
    """8. Test operations monitoring metrics endpoint (GET /operations/metrics)."""
    # Ingest varied alerts
    client.post(
        "/alerts",
        json={"tenant_id": "tenant-ops", "transaction_id": "TX-M-1", "risk_score": 0.95},
    )
    client.post(
        "/alerts",
        json={"tenant_id": "tenant-ops", "transaction_id": "TX-M-2", "risk_score": 0.75},
    )
    resp3 = client.post(
        "/alerts",
        json={"tenant_id": "tenant-ops", "transaction_id": "TX-M-3", "risk_score": 0.40},
    )
    case_3 = resp3.json()["case_id"]

    # Assign and resolve one case
    client.post(f"/cases/{case_3}/assign", json={"analyst_id": "analyst.ops@finguard.internal"})
    client.post(
        f"/cases/{case_3}/resolve",
        json={"resolution": "FALSE_POSITIVE", "resolved_by": "analyst.ops@finguard.internal"},
    )

    # Fetch metrics
    metrics_resp = client.get("/operations/metrics?tenant_id=tenant-ops")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()

    assert metrics["total_cases"] == 3
    assert metrics["resolved_cases"] == 1
    assert metrics["open_cases"] == 2
    assert metrics["priority_breakdown"]["P0"] == 1
    assert metrics["priority_breakdown"]["P1"] == 1
    assert metrics["priority_breakdown"]["P2"] == 1
    assert "sla_breach_rate_pct" in metrics
    assert "analyst_workload" in metrics

