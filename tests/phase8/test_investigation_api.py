"""
Tests for FastAPI Investigation Management Endpoints (Phase 8).
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_endpoint(client):
    """Test /health returns healthy status and case store readiness."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "case_store_status" in data
    assert "bedrock_model_id" in data


def test_list_cases_endpoint(client):
    """Test /cases returns list of cases."""
    response = client.get("/cases")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "cases" in data
    assert data["total"] >= 1


def test_get_case_details(client):
    """Test /cases/{case_id} returns case details and AI summary."""
    response = client.get("/cases/CASE-123")
    assert response.status_code == 200
    case = response.json()
    assert case["case_id"] == "CASE-123"
    assert case["transaction_id"] == "TXN-20261112-000001"
    assert case["ai_summary"] is not None
    assert "executive_summary" in case["ai_summary"]


def test_patch_case_analyst_update(client):
    """Test PATCH /cases/{case_id} exactly matching Phase 8 documentation."""
    payload = {
        "status": "IN_REVIEW",
        "assigned_to": "analyst@example.com",
        "note": "Reviewing device and transaction velocity patterns.",
    }

    response = client.patch(
        "/cases/CASE-123",
        json=payload,
        headers={"X-Analyst-Email": "analyst@example.com"},
    )
    assert response.status_code == 200
    case = response.json()

    assert case["status"] == "IN_REVIEW"
    assert case["assigned_to"] == "analyst@example.com"
    assert len(case["notes"]) >= 1
    latest_note = case["notes"][-1]
    assert latest_note["content"] == "Reviewing device and transaction velocity patterns."
    assert latest_note["author"] == "analyst@example.com"


def test_create_case_endpoint(client):
    """Test POST /cases manual creation."""
    payload = {
        "case_id": "CASE-TEST-CREATE",
        "transaction_id": "TXN-TEST-CREATE-001",
        "account_id": "ACC-CREATE",
        "customer_id": "CUS-CREATE",
        "amount": 65000.0,
        "currency": "INR",
        "risk_score": 0.82,
        "risk_level": "HIGH",
    }

    response = client.post("/cases", json=payload)
    assert response.status_code in (200, 201)
    case = response.json()
    assert case["case_id"] == "CASE-TEST-CREATE"
    assert case["ai_summary"] is not None

