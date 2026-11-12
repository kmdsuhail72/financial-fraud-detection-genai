"""
Unit test for FastAPI application endpoints.
"""
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "FinGuard AI"


def test_submit_transaction_endpoint():
    payload = {
        "transaction_id": "TXN-20261112-000001",
        "account_id": "ACC-100045",
        "customer_id": "CUS-200045",
        "transaction_type": "CARD_PAYMENT",
        "amount": 87500.00,
        "currency": "INR",
        "merchant_id": "MER-90012",
        "merchant_category": "ELECTRONICS",
        "transaction_timestamp": "2026-11-12T10:30:00Z",
        "channel": "MOBILE",
        "location": {
            "country": "IN",
            "city": "Kolkata"
        },
        "device_id": "DEV-45002",
        "ip_address": "192.0.2.10",
        "is_international": False
    }
    response = client.post("/api/v1/transactions", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "ACCEPTED"


def test_fraud_score_endpoint():
    payload = {
        "transaction_id": "TXN-20261112-000001",
        "amount": 87500.00,
        "avg_amount_24h": 12500.00,
        "transaction_count_5m": 4,
        "transaction_count_1h": 7,
        "amount_deviation": 7.0,
        "new_device": True,
        "location_change": False,
        "is_international": False,
        "merchant_risk": 0.42,
        "account_age_days": 180
    }
    response = client.post("/api/v1/fraud/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "unified_risk_score" in data
    assert data["unified_risk_score"] > 60.0


def test_generate_ai_investigation_endpoint():
    response = client.post("/api/v1/cases/CASE-20261112-00001/investigate")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "CASE-20261112-00001"
    assert "key_evidence" in data
    assert len(data["key_evidence"]) > 0

