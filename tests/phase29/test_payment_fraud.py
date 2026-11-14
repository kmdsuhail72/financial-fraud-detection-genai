"""
FinGuard AI — Phase 29: Payment Fraud Intelligence Test Suite.
Validates:
1. Health check endpoint (/payments/health)
2. Benchmark payment event assessment (₹2,85,000, new beneficiary, Bengaluru -> Mumbai, 45/100 MEDIUM REVIEW)
3. Low-risk domestic payment (MONITOR)
4. High-risk multi-signal payment (PRIORITY_REVIEW)
5. Rolling 10-minute velocity anomaly detection
6. Missing device context detection
7. Assessment retrieval by transaction ID and 404 handling
8. Payment risk metrics aggregation
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.app import app
from payment_fraud.models import AlertAction, PaymentRail, RiskLevel


@pytest.fixture
def client():
    return TestClient(app)


def test_payment_health_check(client):
    """1. Health check endpoint (/payments/health)."""
    resp = client.get("/payments/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "payment_fraud_intelligence"
    assert data["phase"] == "Phase-29"
    assert "UPI" in data["rails"]
    assert "CARD" in data["rails"]


def test_sample_benchmark_payment_assessment(client):
    """2. Benchmark payment event evaluation (₹2,85,000, new payee, Bengaluru->Mumbai)."""
    fixture_path = Path("examples/payment_event.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Use a unique transaction ID for isolation
    payload["transaction_id"] = "TXN-TEST-BENCHMARK-45"
    payload["customer_id"] = "CUST-BLR-40291"

    resp = client.post("/payments/assess", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["transaction_id"] == "TXN-TEST-BENCHMARK-45"
    assert data["risk_score"] == 45
    assert data["risk_level"] == "MEDIUM"
    assert data["action"] == "REVIEW"
    assert data["payment_rail"] == "UPI"

    # Verify signals
    signals = {s["signal_name"]: s["points"] for s in data["signals"]}
    assert signals.get("High-value payment") == 20
    assert signals.get("New beneficiary") == 15
    assert signals.get("City mismatch") == 10
    assert sum(signals.values()) == 45


def test_low_risk_payment_monitor(client):
    """3. Normal domestic transaction yields low score and MONITOR action."""
    payload = {
        "transaction_id": "TXN-TEST-SAFE-01",
        "customer_id": "CUST-SAFE-100",
        "amount": 2500.0,
        "currency": "INR",
        "payment_rail": "IMPS",
        "beneficiary_account": "ACC-EXISTING-99",
        "beneficiary_name": "Local Grocery Store",
        "is_new_beneficiary": False,
        "customer_home_city": "Delhi",
        "transaction_city": "Delhi",
        "is_international": False,
        "device_context": {
            "device_id": "DEV-SAFE-IPHONE",
            "ip_address": "103.22.45.10",
        },
    }
    resp = client.post("/payments/assess", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["risk_score"] == 0
    assert data["risk_level"] == "LOW"
    assert data["action"] == "MONITOR"
    assert len(data["signals"]) == 0


def test_high_risk_multi_signal_priority_review(client):
    """4. High-value, foreign currency, new beneficiary, and missing device context yields PRIORITY_REVIEW."""
    payload = {
        "transaction_id": "TXN-TEST-CRITICAL-99",
        "customer_id": "CUST-HIGH-RISK-01",
        "amount": 950000.0,
        "currency": "USD",
        "payment_rail": "RTGS",
        "beneficiary_account": "ACC-OVERSEAS-5501",
        "beneficiary_name": "Cayman Offshore Trading",
        "is_new_beneficiary": True,
        "customer_home_city": "Chennai",
        "transaction_city": "Singapore",
        "is_international": True,
        "device_context": None,  # Missing device context
    }
    resp = client.post("/payments/assess", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    # Points: High-value (20) + New beneficiary (15) + City mismatch (10) + International (20) + Missing device (15) = 80
    assert data["risk_score"] == 80
    assert data["risk_level"] == "HIGH"
    assert data["action"] == "PRIORITY_REVIEW"
    assert len(data["signals"]) == 5


def test_rolling_10_minute_velocity_detection(client):
    """5. Multiple payments within 10-minute window trigger velocity detection."""
    cust_id = "CUST-RAPID-VELOCITY-01"

    # Send 3 rapid payments
    for i in range(1, 4):
        p = {
            "transaction_id": f"TXN-RAPID-{i}",
            "customer_id": cust_id,
            "amount": 5000.0,
            "currency": "INR",
            "payment_rail": "UPI",
            "beneficiary_account": f"ACC-BEN-{i}",
            "is_new_beneficiary": False,
            "customer_home_city": "Mumbai",
            "transaction_city": "Mumbai",
            "device_context": {"device_id": "DEV-TEST-01"},
        }
        res = client.post("/payments/assess", json=p)
        assert res.status_code == 201

    # 4th transaction within the window should flag velocity anomaly (25 points)
    p_4th = {
        "transaction_id": "TXN-RAPID-4TH-TRIGGER",
        "customer_id": cust_id,
        "amount": 5000.0,
        "currency": "INR",
        "payment_rail": "UPI",
        "beneficiary_account": "ACC-BEN-4",
        "is_new_beneficiary": False,
        "customer_home_city": "Mumbai",
        "transaction_city": "Mumbai",
        "device_context": {"device_id": "DEV-TEST-01"},
    }
    res4 = client.post("/payments/assess", json=p_4th)
    assert res4.status_code == 201
    data4 = res4.json()

    signal_names = [s["signal_name"] for s in data4["signals"]]
    assert "Velocity anomaly" in signal_names
    velocity_signal = next(s for s in data4["signals"] if s["signal_name"] == "Velocity anomaly")
    assert velocity_signal["points"] == 25


def test_missing_device_context_detection(client):
    """6. Missing device context triggers device risk signal (15 points)."""
    payload = {
        "transaction_id": "TXN-NO-DEVICE-CTX",
        "customer_id": "CUST-ANON-007",
        "amount": 10000.0,
        "currency": "INR",
        "payment_rail": "CARD",
        "beneficiary_account": "ACC-MERCHANT-01",
        "is_new_beneficiary": False,
        "customer_home_city": "Pune",
        "transaction_city": "Pune",
        "device_context": None,
    }
    resp = client.post("/payments/assess", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["risk_score"] == 15
    signal_names = [s["signal_name"] for s in data["signals"]]
    assert "Missing device context" in signal_names


def test_payment_assessment_retrieval_and_404(client):
    """7. Assessment retrieval by transaction ID and 404 behavior."""
    # Seeded benchmark transaction
    resp = client.get("/payments/assessments/TXN-2026-UPI-285000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_id"] == "TXN-2026-UPI-285000"
    assert data["risk_score"] == 45

    # Non-existent transaction
    resp_404 = client.get("/payments/assessments/TXN-NON-EXISTENT-999")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


def test_payment_metrics_endpoint(client):
    """8. Metrics aggregations and KPI calculations."""
    resp = client.get("/payments/metrics")
    assert resp.status_code == 200
    metrics = resp.json()

    assert metrics["total_assessed"] >= 3
    assert "monitor_count" in metrics
    assert "review_count" in metrics
    assert "priority_review_count" in metrics
    assert "avg_risk_score" in metrics
    assert "high_value_count" in metrics
    assert "new_beneficiary_count" in metrics
    assert "city_mismatch_count" in metrics
    assert "velocity_flagged_count" in metrics
    assert metrics["total_assessed"] == (
        metrics["monitor_count"] + metrics["review_count"] + metrics["priority_review_count"]
    )
