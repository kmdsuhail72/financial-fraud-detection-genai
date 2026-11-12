"""
Tests for Real-Time Scoring FastAPI Application.
"""
import pytest
from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Test /health probe returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data


def test_score_endpoint_exact_spec(client):
    """Test /score matches the user-provided request and response schema exactly."""
    payload = {
        "transaction_id": "txn-demo",
        "features": {
            "amount": 12500,
            "currency": "INR",
            "channel": "mobile",
            "transaction_count_5m_prior": 4,
            "transaction_count_1h_prior": 12,
            "new_device_flag": True,
            "home_city_mismatch": False,
            "is_international": True,
        },
    }

    response = client.post("/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["transaction_id"] == "txn-demo"
    assert "fraud_probability" in data
    assert "anomaly_score" in data
    assert "risk_score" in data
    assert "risk_level" in data
    assert "classifier_threshold" in data
    assert "model_version" in data

    assert 0.0 <= data["fraud_probability"] <= 1.0
    assert 0.0 <= data["anomaly_score"] <= 1.0
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_score_batch_endpoint(client):
    """Test /score/batch with multiple transactions."""
    payload = [
        {
            "transaction_id": "txn-001",
            "features": {"amount": 500, "transaction_count_5m_prior": 0},
        },
        {
            "transaction_id": "txn-002",
            "features": {"amount": 500000, "transaction_count_5m_prior": 10, "new_device_flag": True},
        },
    ]

    response = client.post("/score/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["transaction_id"] == "txn-001"
    assert data[1]["transaction_id"] == "txn-002"
    # Higher risk for txn-002
    assert data[1]["risk_score"] >= data[0]["risk_score"]


def test_model_metadata_endpoint(client):
    """Test /model/metadata returns feature manifest and thresholds."""
    response = client.get("/model/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "model_version" in data
    assert "classifier_threshold" in data
    assert "feature_manifest" in data
