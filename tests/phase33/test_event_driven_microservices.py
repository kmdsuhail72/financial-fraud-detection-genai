"""
FinGuard AI — Phase 33: Enterprise Microservices & Event-Driven Architecture Test Suite.
Validates:
1. Microservices architecture health & contract capabilities (/microservices/health)
2. Event bus pub/sub routing to registered microservice handlers
3. Transactional outbox persistence and asynchronous flush
4. End-to-end Saga forward orchestration (happy path)
5. Saga reverse-order compensation on step failure
6. Idempotency deduplication for transactions and events
7. Dead-letter queue (DLQ) routing upon retry exhaustion
8. Distributed tracing propagation (correlation & causation IDs) and operational metrics
"""
import pytest
from fastapi.testclient import TestClient

from api.app import app
from events.event_bus import event_bus
from events.models import EventContract, OutboxStatus
from events.outbox import transactional_outbox
from events.saga import saga_orchestrator
from events.service import microservices_coordinator


@pytest.fixture
def client():
    # Reset in-memory state before tests
    microservices_coordinator.reset()
    return TestClient(app)


def test_microservices_health_and_contracts(client):
    """1. Validates /microservices/health and architectural boundaries."""
    resp = client.get("/microservices/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "event_driven_microservices"
    assert data["phase"] == "Phase-33"
    services = data["architecture"]["services"]
    assert "transaction-service" in services
    assert "fraud-scoring-service" in services
    assert "ledger-service" in services
    assert "notification-service" in services
    patterns = data["architecture"]["patterns"]
    assert "transactional_outbox" in patterns
    assert "saga_orchestration_forward_and_compensate" in patterns
    assert "dead_letter_queue_redrive" in patterns
    assert "idempotency_deduplication" in patterns


def test_event_bus_publish_and_subscriber_routing(client):
    """2. Validates event bus subscriber registration and routing."""
    received = []

    def subscriber_handler(evt: EventContract):
        received.append(evt)

    event_bus.subscribe("test.routing.v1", subscriber_handler)

    test_evt = EventContract(
        event_type="test.routing.v1",
        source="test-service",
        correlation_id="corr-test-route",
        payload={"message": "hello routing"},
    )
    ok = event_bus.publish(test_evt)
    assert ok is True
    assert len(received) == 1
    assert received[0].payload["message"] == "hello routing"
    assert received[0].correlation_id == "corr-test-route"


def test_transactional_outbox_pattern(client):
    """3. Validates outbox PENDING record persistence and flush to Event Bus."""
    # Create an event directly in outbox
    test_evt = EventContract(
        event_type="outbox.test.event.v1",
        source="transaction-service",
        payload={"order_id": "ORD-999"},
    )
    record = transactional_outbox.record_event(
        aggregate_type="Order",
        aggregate_id="ORD-999",
        event=test_evt,
    )
    assert record.status == OutboxStatus.PENDING

    # Verify pending state from API
    pending_resp = client.get("/microservices/outbox?status=PENDING")
    assert pending_resp.status_code == 200
    records = pending_resp.json()
    assert any(r["outbox_id"] == record.outbox_id for r in records)

    # Flush outbox
    flush_resp = client.post("/microservices/outbox/flush")
    assert flush_resp.status_code == 200
    flush_data = flush_resp.json()
    assert flush_data["events_published"] >= 1

    # Verify updated status to PUBLISHED
    pub_resp = client.get("/microservices/outbox?status=PUBLISHED")
    assert pub_resp.status_code == 200
    published_records = pub_resp.json()
    assert any(r["outbox_id"] == record.outbox_id for r in published_records)


def test_saga_orchestration_happy_path(client):
    """4. Validates forward Saga execution when all microservices succeed."""
    payload = {
        "transaction_id": "TXN-SAGA-SUCCESS-01",
        "customer_id": "CUST-881",
        "amount": 25000.0,
        "currency": "INR",
        "rail": "UPI",
    }
    resp = client.post("/microservices/transactions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    saga_data = data["data"]
    assert saga_data["saga_status"] == "COMPLETED"
    assert saga_data["steps_executed"] == 4
    assert len(saga_data["compensation_log"]) == 0

    # Retrieve saga details
    saga_id = saga_data["saga_id"]
    get_resp = client.get(f"/microservices/saga/{saga_id}")
    assert get_resp.status_code == 200
    instance = get_resp.json()
    assert instance["status"] == "COMPLETED"
    assert all(step["status"] == "EXECUTED" for step in instance["steps"])


def test_saga_reverse_order_compensation(client):
    """5. Validates reverse-order compensation when a downstream microservice fails."""
    # Force failure at Step 3: SettleTransaction
    payload = {
        "transaction_id": "TXN-SAGA-FAIL-02",
        "customer_id": "CUST-992",
        "amount": 75000.0,
        "currency": "INR",
        "rail": "IMPS",
        "force_failure_at_step": "SettleTransaction",
    }
    resp = client.post("/microservices/transactions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "compensated"
    saga_data = data["data"]
    assert saga_data["saga_status"] == "COMPENSATED"
    assert "Simulated failure at SettleTransaction" in saga_data["error"]

    # Verify compensation log has entries in reverse order
    comp_log = saga_data["compensation_log"]
    assert len(comp_log) == 2  # EvaluateFraudRisk and AuthorizeHold compensated
    assert "EvaluateFraudRisk" in comp_log[0]
    assert "AuthorizeHold" in comp_log[1]

    # Check Saga status via API
    saga_id = saga_data["saga_id"]
    get_resp = client.get(f"/microservices/saga/{saga_id}")
    assert get_resp.status_code == 200
    instance = get_resp.json()
    assert instance["status"] == "COMPENSATED"
    assert instance["steps"][0]["status"] == "COMPENSATED"
    assert instance["steps"][1]["status"] == "COMPENSATED"
    assert instance["steps"][2]["status"] == "FAILED"
    assert instance["steps"][3]["status"] == "PENDING"


def test_idempotency_deduplication(client):
    """6. Validates that duplicate requests with the same Idempotency-Key return cached response."""
    payload = {
        "transaction_id": "TXN-IDEM-001",
        "customer_id": "CUST-555",
        "amount": 10000.0,
        "currency": "INR",
        "rail": "UPI",
    }
    headers = {"Idempotency-Key": "unique-idempotency-key-abc-123"}

    # Initial request
    resp1 = client.post("/microservices/transactions", json=payload, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["idempotent_replay"] is False

    # Second duplicate request with exact same Idempotency-Key
    resp2 = client.post("/microservices/transactions", json=payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["idempotent_replay"] is True
    assert data2["data"]["transaction_id"] == "TXN-IDEM-001"


def test_dead_letter_queue_and_retry_exhaustion(client):
    """7. Validates bounded retries and automatic DLQ routing on handler failure."""
    retry_counter = {"attempts": 0}

    def poison_handler(evt: EventContract):
        retry_counter["attempts"] += 1
        raise ValueError("Simulated unrecoverable poison payload exception")

    event_bus.subscribe("poison.event.v1", poison_handler)

    poison_event = EventContract(
        event_type="poison.event.v1",
        source="external-payment-stream",
        correlation_id="corr-poison-dlq",
        payload={"corrupted": True},
    )

    # Publish poison event: event bus tries 3 times and routes to DLQ
    success = event_bus.publish(poison_event)
    assert success is False
    assert retry_counter["attempts"] == 3

    # Verify DLQ record via API
    dlq_resp = client.get("/microservices/dlq")
    assert dlq_resp.status_code == 200
    dlq_records = dlq_resp.json()
    assert len(dlq_records) >= 1
    target = next((d for d in dlq_records if d["original_event"]["event_id"] == poison_event.event_id), None)
    assert target is not None
    assert target["retry_attempts"] == 3
    assert "Simulated unrecoverable poison payload exception" in target["failure_reason"]


def test_distributed_tracing_and_metrics(client):
    """8. Validates correlation/causation ID propagation and aggregated metrics."""
    # Execute a transaction to generate trace data
    payload = {
        "transaction_id": "TXN-TRACE-01",
        "customer_id": "CUST-TRACE",
        "amount": 18000.0,
        "currency": "INR",
        "rail": "UPI",
    }
    tx_resp = client.post("/microservices/transactions", json=payload)
    assert tx_resp.status_code == 200
    corr_id = tx_resp.json()["data"]["correlation_id"]

    # Query events filtered by correlation ID
    events_resp = client.get(f"/microservices/events?correlation_id={corr_id}")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 2
    for evt in events:
        assert evt["correlation_id"] == corr_id

    # Verify operational metrics
    metrics_resp = client.get("/microservices/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["total_events_published"] >= 1
    assert metrics["total_events_consumed"] >= 1
    assert metrics["sagas_completed"] >= 1
    assert metrics["service_health"]["transaction_service"] == "healthy"
    assert metrics["service_health"]["fraud_scoring_service"] == "healthy"

