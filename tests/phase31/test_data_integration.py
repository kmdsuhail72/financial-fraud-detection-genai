"""
FinGuard AI — Phase 31: Enterprise Data Integration Test Suite.
Validates:
1. Health check endpoint (/integrations/health)
2. Core Banking System (CBS) adapter event normalization
3. Payment Gateway lifecycle event mapping (Razorpay/Stripe)
4. Idempotent ingestion and duplicate detection
5. Cryptographic HMAC-SHA256 signed webhook verification
6. Rejection of webhooks with invalid HMAC signatures (401 Unauthorized)
7. Retry exhaustion and Dead-Letter Queue (DLQ) processing
8. Ingestion audit logging and integration KPIs (/integrations/metrics)
"""
import hashlib
import hmac
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.app import app
from integrations.adapters import DEFAULT_WEBHOOK_SECRET
from integrations.models import EventStatus
from integrations.service import integration_service


@pytest.fixture
def client():
    return TestClient(app)


def test_integrations_health_check(client):
    """1. Health check endpoint (/integrations/health)."""
    resp = client.get("/integrations/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "data_integration"
    assert data["phase"] == "Phase-31"
    assert "core_banking" in data["connectors"]
    assert "payment_gateway" in data["connectors"]
    assert data["idempotency_enabled"] is True


def test_core_banking_adapter_ingestion(client):
    """2. Core banking transaction event mapping and canonical normalization."""
    fixture_path = Path("examples/core_banking_event.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    payload["cbs_txn_id"] = "CBS-TEST-TXN-101"
    resp = client.post("/integrations/core-banking/events", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["source"] == "CORE_BANKING"
    assert data["event_type"] == "TRANSACTION_POSTED"
    assert data["amount"] == 350000.0
    assert data["customer_id"] == "CIF-IND-40291"
    assert data["account_id"] == "ACC-HDFC-991203"
    assert data["status"] == "PROCESSED"
    assert data["normalized_payload"]["channel"] == "NETBANKING"


def test_payment_gateway_adapter_ingestion(client):
    """3. Payment gateway event lifecycle mapping."""
    fixture_path = Path("examples/payment_gateway_event.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    payload["gateway_payment_id"] = "pay_test_gw_99210"
    resp = client.post("/integrations/payment-gateway/events", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["source"] == "PAYMENT_GATEWAY"
    assert data["event_type"] == "PAYMENT_CAPTURED"
    assert data["amount"] == 285000.0
    assert data["status"] == "PROCESSED"
    assert data["normalized_payload"]["provider"] == "RAZORPAY"


def test_idempotency_duplicate_event_detection(client):
    """4. Deduplication of repeated events using idempotency keys."""
    payload = {
        "cbs_txn_id": "CBS-IDEMPOTENT-DUP-01",
        "account_number": "ACC-IDEM-001",
        "customer_cif": "CIF-IDEM-99",
        "amount": 75000.0,
        "txn_type": "CREDIT",
        "channel": "UPI"
    }

    # First ingestion -> PROCESSED
    res1 = client.post("/integrations/core-banking/events", json=payload)
    assert res1.status_code == 201
    assert res1.json()["status"] == "PROCESSED"

    # Second ingestion with same cbs_txn_id -> DUPLICATE
    res2 = client.post("/integrations/core-banking/events", json=payload)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["status"] == "DUPLICATE"
    assert data2["idempotency_key"] == res1.json()["idempotency_key"]


def test_signed_webhook_verification_success(client):
    """5. Valid HMAC-SHA256 signed webhook ingestion."""
    webhook_body = {
        "id": "evt_hook_rzp_99014",
        "email": "sarah.connor@cyberdyne.internal",
        "amount": 185000.0,
        "currency": "INR",
        "status": "payment.authorized"
    }
    raw_bytes = json.dumps(webhook_body).encode("utf-8")
    signature = hmac.new(DEFAULT_WEBHOOK_SECRET.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    resp = client.post(
        "/integrations/webhooks/razorpay",
        content=raw_bytes,
        headers={"Content-Type": "application/json", "X-Signature": signature}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "WEBHOOK"
    assert data["status"] == "PROCESSED"
    assert data["amount"] == 185000.0


def test_signed_webhook_invalid_signature_rejection(client):
    """6. Webhook with tampered / invalid signature returns 401 Unauthorized."""
    webhook_body = {"id": "evt_tampered_01", "amount": 999999.0}
    raw_bytes = json.dumps(webhook_body).encode("utf-8")
    invalid_sig = "deadbeef00000000000000000000000000000000000000000000000000000000"

    resp = client.post(
        "/integrations/webhooks/stripe",
        content=raw_bytes,
        headers={"Content-Type": "application/json", "X-Signature": invalid_sig}
    )
    assert resp.status_code == 401
    assert "invalid webhook hmac" in resp.json()["detail"].lower()


def test_retry_handling_and_dead_letter_queue(client):
    """7. Retry exhaustion triggers Dead-Letter Queue (DLQ) routing."""
    failing_payload = {
        "event_id": "EVT-FAIL-SIM-99",
        "force_failure": True,
        "amount": 50000.0,
        "notes": "Upstream timeout test"
    }
    # Invoke service retry processing with simulated failure
    dlq_res = integration_service.process_with_retry_and_dlq(
        source="MOCK_BANKING_API",
        payload=failing_payload,
        max_retries=3
    )
    assert dlq_res.status == EventStatus.DEAD_LETTER
    assert dlq_res.retry_count == 3

    # Verify event appears in DLQ list endpoint
    dlq_list_resp = client.get("/integrations/dead-letters")
    assert dlq_list_resp.status_code == 200
    dlqs = dlq_list_resp.json()
    assert len(dlqs) >= 1
    reasons = [d["failure_reason"] for d in dlqs]
    assert any("simulated provider timeout" in r.lower() for r in reasons)


def test_integration_audit_and_metrics(client):
    """8. Audit trail history and ingestion metrics aggregations."""
    audit_resp = client.get("/integrations/audit")
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    assert len(audits) >= 2
    actions = [a["action"] for a in audits]
    assert "EVENT_INGESTED" in actions

    metrics_resp = client.get("/integrations/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["total_events_received"] >= 3
    assert "processed_count" in metrics
    assert "duplicate_count" in metrics
    assert "dead_letter_count" in metrics
    assert "success_rate_percent" in metrics
    assert metrics["success_rate_percent"] > 0
