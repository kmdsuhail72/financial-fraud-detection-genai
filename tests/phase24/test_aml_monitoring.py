"""
FinGuard AI — Phase 24 Anti-Money Laundering (AML) Test Suite.
Validates:
1. Health check endpoint (HTTP 200)
2. Large Cash Transaction rule trigger (>= $10,000 threshold)
3. Structuring / Smurfing detection ($8,500 - $9,999 cluster)
4. Rapid Inflow/Outflow pass-through layering detection
5. High Velocity burst transaction detection
6. Customer risk profiling and PEP tier elevation
7. Case lifecycle status transitions and analyst notes
8. Suspicious Activity Report (SAR) investigation draft generation
"""
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from api.app import app
from aml.service import get_aml_service
from aml.models import AMLCaseStatus, CustomerRiskTier, TransactionDirection


@pytest.fixture(autouse=True)
def clean_aml_store():
    """Clear AML store before each test run."""
    service = get_aml_service()
    service.store.clear()
    yield
    service.store.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_aml_health_endpoint(client):
    """1. Test health check on /aml/health."""
    resp = client.get("/aml/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert "Phase 24" in data["phase"]


def test_large_cash_transaction_rule(client):
    """2. Test transaction exceeding $10,000 triggers LARGE_CASH_TRANSACTION alert."""
    payload = {
        "transaction_id": "TXN-LARGE-TEST-01",
        "customer_id": "CUST-LARGE-01",
        "amount": 14500.0,
        "currency": "USD",
        "direction": "OUTFLOW",
        "payment_method": "CASH_DEPOSIT",
    }
    resp = client.post("/aml/monitor/transaction", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["alerts_triggered"]) == 1
    alert = data["alerts_triggered"][0]
    assert alert["rule_type"] == "LARGE_CASH_TRANSACTION"
    assert alert["trigger_amount"] == 14500.0
    assert data["case_id"] is not None


def test_possible_structuring_rule(client):
    """3. Test multiple transactions just below $10,000 trigger POSSIBLE_STRUCTURING alert."""
    cid = "CUST-STRUCT-01"

    # First transaction: $9,200
    r1 = client.post(
        "/aml/monitor/transaction",
        json={
            "transaction_id": "TXN-S1",
            "customer_id": cid,
            "amount": 9200.0,
            "direction": "OUTFLOW",
        },
    )
    assert r1.status_code == 200
    # First alone does not trigger structuring
    assert len(r1.json()["alerts_triggered"]) == 0

    # Second transaction within hours: $9,500
    r2 = client.post(
        "/aml/monitor/transaction",
        json={
            "transaction_id": "TXN-S2",
            "customer_id": cid,
            "amount": 9500.0,
            "direction": "OUTFLOW",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()

    assert len(d2["alerts_triggered"]) >= 1
    rules = [a["rule_type"] for a in d2["alerts_triggered"]]
    assert "POSSIBLE_STRUCTURING" in rules
    assert d2["case_id"] is not None


def test_rapid_inflow_outflow_rule(client):
    """4. Test rapid pass-through layering: large inflow followed by immediate 90% outflow."""
    cid = "CUST-LAYER-01"

    # Step 1: Inflow of $8,000
    r_in = client.post(
        "/aml/monitor/transaction",
        json={
            "transaction_id": "TXN-IN-01",
            "customer_id": cid,
            "amount": 8000.0,
            "direction": "INFLOW",
        },
    )
    assert r_in.status_code == 200

    # Step 2: Rapid outflow of $7,200 (90% drain)
    r_out = client.post(
        "/aml/monitor/transaction",
        json={
            "transaction_id": "TXN-OUT-01",
            "customer_id": cid,
            "amount": 7200.0,
            "direction": "OUTFLOW",
        },
    )
    assert r_out.status_code == 200
    d_out = r_out.json()

    rules = [a["rule_type"] for a in d_out["alerts_triggered"]]
    assert "RAPID_INFLOW_OUTFLOW" in rules


def test_high_velocity_rule(client):
    """5. Test 5 transactions within a 10-minute window trigger HIGH_VELOCITY alert."""
    cid = "CUST-VELO-01"

    for i in range(1, 5):
        client.post(
            "/aml/monitor/transaction",
            json={
                "transaction_id": f"TXN-V-{i}",
                "customer_id": cid,
                "amount": 1000.0,
                "direction": "OUTFLOW",
            },
        )

    # 5th transaction
    resp5 = client.post(
        "/aml/monitor/transaction",
        json={
            "transaction_id": "TXN-V-5",
            "customer_id": cid,
            "amount": 1000.0,
            "direction": "OUTFLOW",
        },
    )
    assert resp5.status_code == 200
    d5 = resp5.json()

    rules = [a["rule_type"] for a in d5["alerts_triggered"]]
    assert "HIGH_VELOCITY" in rules


def test_customer_risk_profiling_and_pep(client):
    """6. Test customer risk score and tier calculation with PEP flag and alert penalties."""
    service = get_aml_service()
    # Create customer with PEP flag
    service.store.get_or_create_profile(
        customer_id="CUST-PEP-01",
        name="Senator Marcus Wright",
        country="US",
        pep_flag=True,
    )

    # Trigger large cash alert
    client.post(
        "/aml/monitor/transaction",
        json={
            "transaction_id": "TXN-PEP-01",
            "customer_id": "CUST-PEP-01",
            "amount": 35000.0,
            "direction": "OUTFLOW",
        },
    )

    # Query customer profile
    prof_resp = client.get("/aml/customers/CUST-PEP-01")
    assert prof_resp.status_code == 200
    profile = prof_resp.json()

    assert profile["pep_flag"] is True
    assert profile["risk_score"] >= 50
    assert profile["risk_tier"] in ["HIGH", "CRITICAL"]
    assert any("PEP" in f for f in profile["risk_factors"])


def test_aml_case_lifecycle_and_notes(client):
    """7. Test AML case status updates (UNDER_INVESTIGATION -> ESCALATED) and notes."""
    # Trigger alert to spawn case
    res = client.post(
        "/aml/monitor/transaction",
        json={
            "transaction_id": "TXN-CASE-01",
            "customer_id": "CUST-CASE-01",
            "amount": 18000.0,
            "direction": "OUTFLOW",
        },
    )
    case_id = res.json()["case_id"]

    # Update status to UNDER_INVESTIGATION
    s_resp = client.post(
        f"/aml/cases/{case_id}/status",
        json={"status": "UNDER_INVESTIGATION", "notes": "Commencing review of counterparties"},
    )
    assert s_resp.status_code == 200
    assert s_resp.json()["status"] == "UNDER_INVESTIGATION"

    # Add note
    n_resp = client.post(
        f"/aml/cases/{case_id}/notes",
        json={"author": "lead.aml.analyst", "content": "Counterparty is a high-risk crypto off-ramp."},
    )
    assert n_resp.status_code == 200
    assert len(n_resp.json()["notes"]) == 1

    # Escalate
    esc_resp = client.post(
        f"/aml/cases/{case_id}/status",
        json={"status": "ESCALATED", "notes": "Escalated for SAR filing review"},
    )
    assert esc_resp.status_code == 200
    assert esc_resp.json()["status"] == "ESCALATED"


def test_sar_investigation_draft_generation(client):
    """8. Test generation of formal Suspicious Activity Report (SAR) investigation draft."""
    # Trigger structuring
    cid = "CUST-SAR-01"
    client.post(
        "/aml/monitor/transaction",
        json={"transaction_id": "TX-SAR-1", "customer_id": cid, "amount": 9400.0, "direction": "OUTFLOW"},
    )
    r2 = client.post(
        "/aml/monitor/transaction",
        json={"transaction_id": "TX-SAR-2", "customer_id": cid, "amount": 9600.0, "direction": "OUTFLOW"},
    )
    case_id = r2.json()["case_id"]

    # Generate SAR Draft
    sar_resp = client.post(
        f"/aml/cases/{case_id}/sar-draft",
        json={
            "prepared_by": "senior.aml.officer@finguard.internal",
            "recommended_disposition": "RECOMMEND_SAR_FILING",
        },
    )
    assert sar_resp.status_code == 200
    draft = sar_resp.json()

    assert draft["case_id"] == case_id
    assert draft["customer_id"] == cid
    assert draft["recommended_disposition"] == "RECOMMEND_SAR_FILING"
    assert draft["total_suspicious_amount"] >= 19000.0
    assert "POSSIBLE_STRUCTURING" in draft["violating_patterns"]
    assert "## 1. Suspicious Activity Narrative" in draft["report_markdown"]
    assert "FinGuard AI" in draft["report_markdown"]

