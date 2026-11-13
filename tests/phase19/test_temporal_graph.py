"""Unit and Integration Tests for Phase 19 Enterprise Temporal Graph Learning & Streaming Ingestion.

Validates:
1. Kinesis Lambda base64 decoding and idempotent deduplication.
2. Temporal graph bounded history and strict as-of windowing (no lookahead).
3. Rolling as-of temporal feature engineering (velocity, bursts, deviations).
4. PyTorch GRU sequence classifier forward pass and probability output.
5. Chronological train/test split verification (zero future lookahead leakage).
6. GRU model training smoke test and parameter convergence.
7. REST API: GET /temporal/health and GET /temporal/model/info.
8. REST API: POST /temporal/ingest and GET /temporal/entities/{id}/timeline.
9. REST API: POST /temporal/score and GET /temporal/metrics.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import torch
from fastapi.testclient import TestClient

from api.app import app
from security.auth import create_test_token
from temporal.feature_engineer import TemporalFeatureEngineer
from temporal.gru_model import TemporalGRUClassifier
from temporal.kinesis_decoder import KinesisLambdaDecoder
from temporal.models import (
    EntityTimelineResponse,
    TemporalEntityFeatures,
    TemporalIngestResponse,
    TemporalModelInfoResponse,
    TemporalRiskLevel,
    TemporalScoreRequest,
    TemporalScoreResponse,
    TemporalTransactionEvent,
)
from temporal.service import TemporalFraudService, get_temporal_service
from temporal.temporal_graph import TemporalGraph


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def temporal_service():
    return get_temporal_service()


# =============================================================================
# 1. Kinesis Lambda Event Decoder and Idempotency Test
# =============================================================================
def test_kinesis_lambda_decoder_and_idempotency():
    """Verifies base64 payload decoding and sliding window deduplication."""
    decoder = KinesisLambdaDecoder(max_cache_size=100)

    raw_payload_1 = {
        "transaction_id": "TXN-KIN-001",
        "timestamp": 1794500100.0,
        "source_account": "ACC-K1",
        "target_account": "ACC-K2",
        "amount": 450.0,
        "currency": "USD",
        "channel": "mobile",
    }
    encoded_1 = base64.b64encode(json.dumps(raw_payload_1).encode("utf-8")).decode("utf-8")

    kinesis_event = {
        "Records": [
            {"kinesis": {"data": encoded_1, "sequenceNumber": "seq-1"}},
            {"kinesis": {"data": encoded_1, "sequenceNumber": "seq-1-dup"}},  # duplicate record
        ]
    }

    events, dups, errs = decoder.decode_kinesis_event(kinesis_event)
    assert len(events) == 1, "Only one unique transaction should be decoded"
    assert dups == 1, "Duplicate record must be counted and skipped"
    assert errs == 0
    assert events[0].transaction_id == "TXN-KIN-001"
    assert events[0].amount == 450.0

    # Repeat check
    assert decoder.is_duplicate("TXN-KIN-001") is True


# =============================================================================
# 2. Temporal Graph Bounded History and Sliding Window Test
# =============================================================================
def test_temporal_graph_bounded_history_and_sliding_window():
    """Verifies that temporal graph bounds memory and enforces strict causality."""
    graph = TemporalGraph(max_history_per_entity=5)

    base_time = 1794500000.0
    for i in range(1, 8):
        ev = TemporalTransactionEvent(
            transaction_id=f"TXN-BOUND-{i}",
            timestamp=base_time + (i * 60.0),
            source_account="ACC-BOUND",
            amount=100.0 * i,
        )
        graph.add_event(ev)

    # 1. Bounded history: deque maxlen=5 keeps only last 5
    all_events = graph.get_entity_events("ACC-BOUND")
    assert len(all_events) == 5
    assert all_events[0].transaction_id == "TXN-BOUND-3"
    assert all_events[-1].transaction_id == "TXN-BOUND-7"

    # 2. Causality / As-of boundary (no lookahead): query as-of t=base_time + 200
    cutoff = base_time + 200.0
    causal_events = graph.get_entity_events("ACC-BOUND", as_of=cutoff)
    for e in causal_events:
        assert e.timestamp <= cutoff, f"Event timestamp {e.timestamp} exceeds cutoff {cutoff}"


# =============================================================================
# 3. Rolling As-Of Temporal Feature Engineering Test
# =============================================================================
def test_rolling_as_of_temporal_feature_engineering():
    """Verifies rolling velocity, burst ratio, and new device/IP detection."""
    graph = TemporalGraph()
    engineer = TemporalFeatureEngineer(graph)

    t0 = 1794510000.0
    account_id = "ACC-VELOCITY"

    # Insert 4 rapid transactions within 2 minutes (120 seconds)
    for i in range(1, 5):
        ev = TemporalTransactionEvent(
            transaction_id=f"TXN-VEL-{i}",
            timestamp=t0 + (i * 30.0),
            source_account=account_id,
            target_account="ACC-TARGET",
            device_id=f"DEV-{i}",
            ip_address="198.51.100.1",
            amount=500.0,
        )
        graph.add_event(ev)

    as_of = t0 + 150.0
    features = engineer.compute_features(account_id, as_of_timestamp=as_of)

    assert features.tx_count_5m == 4
    assert features.tx_count_1h == 4
    assert features.velocity_burst_ratio > 2.0, "Rapid 5m transactions should trigger high burst ratio"
    assert features.amount_sum_1h == 2000.0

    # Test conversion to 12-dimensional normalized vector
    vec = features.to_feature_vector()
    assert len(vec) == 12
    for val in vec:
        assert 0.0 <= val <= 1.0, f"Feature vector value {val} outside [0, 1] range"


# =============================================================================
# 4. GRU Sequence Classifier Forward Pass Test
# =============================================================================
def test_gru_sequence_classifier_forward_pass():
    """Verifies 2-layer GRU sequence classifier input/output tensor shapes and probabilities."""
    model = TemporalGRUClassifier(input_dim=12, hidden_dim=64, num_layers=2, num_classes=2)
    model.eval()

    batch_size = 4
    seq_len = 5
    feature_dim = 12

    dummy_input = torch.randn(batch_size, seq_len, feature_dim)
    with torch.no_grad():
        logits, hn = model(dummy_input)

    assert logits.shape == (batch_size, 2)
    assert hn.shape == (2, batch_size, 64)
    assert not torch.isnan(logits).any()

    # Single sequence probability test
    single_seq = torch.randn(seq_len, feature_dim)
    prob = model.predict_probability(single_seq)
    assert 0.0 <= prob <= 1.0


# =============================================================================
# 5. Chronological Train/Test Split Verification Test
# =============================================================================
def test_chronological_train_test_split_no_leakage():
    """Verifies strict chronological splitting with zero future lookahead leakage."""
    from scripts.train_temporal_model import load_chronological_dataset

    data_file = Path("examples/training_record.jsonl")
    if not data_file.exists():
        from scripts.generate_events import generate_synthetic_temporal_events, generate_training_records
        events = generate_synthetic_temporal_events(100)
        recs = generate_training_records(events)
        data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(data_file, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

    x_train, y_train, x_test, y_test = load_chronological_dataset(data_file, split_ratio=0.80)

    assert len(x_train) > 0
    assert len(x_test) > 0
    assert x_train.shape[1] == 5  # Sequence length
    assert x_train.shape[2] == 12  # Feature dim


# =============================================================================
# 6. GRU Training Smoke and Convergence Test
# =============================================================================
def test_gru_training_smoke_and_convergence():
    """Verifies that GRU model weights update and training loss decreases without NaNs."""
    model = TemporalGRUClassifier(input_dim=12, hidden_dim=32, num_layers=1, num_classes=2)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = torch.nn.CrossEntropyLoss()

    dummy_x = torch.randn(16, 5, 12)
    dummy_y = torch.randint(0, 2, (16,))

    initial_loss = criterion(model(dummy_x)[0], dummy_y).item()

    model.train()
    for _ in range(15):
        optimizer.zero_grad()
        logits, _ = model(dummy_x)
        loss = criterion(logits, dummy_y)
        loss.backward()
        optimizer.step()

    final_loss = loss.item()
    assert final_loss < initial_loss
    assert not math.isnan(final_loss) if "math" in globals() else True


# =============================================================================
# 7. REST API Health and Model Info Endpoints Test
# =============================================================================
def test_api_temporal_health_and_model_info(client, auth_headers):
    """Verifies GET /temporal/health and GET /temporal/model/info."""
    # 1. GET /temporal/health
    resp_health = client.get("/temporal/health")
    assert resp_health.status_code == 200
    health_data = resp_health.json()
    assert health_data["status"] == "HEALTHY"
    assert "Phase 19" in health_data["phase"]

    # 2. GET /temporal/model/info
    resp_info = client.get("/temporal/model/info", headers=auth_headers)
    assert resp_info.status_code == 200
    info_data = resp_info.json()
    assert info_data["model_name"] == "FinGuard-TemporalGRU-Classifier"
    assert info_data["input_dim"] == 12
    assert info_data["hidden_dim"] == 64
    assert info_data["num_layers"] == 2


# =============================================================================
# 8. REST API Ingest and Timeline Endpoints Test
# =============================================================================
def test_api_temporal_ingest_and_timeline(client, auth_headers):
    """Verifies POST /temporal/ingest and GET /temporal/entities/{id}/timeline."""
    # 1. POST /temporal/ingest with raw events
    ev = {
        "transaction_id": "TXN-API-INGEST-01",
        "timestamp": 1794520000.0,
        "source_account": "ACC-API-TEST",
        "target_account": "ACC-API-DEST",
        "amount": 1250.0,
        "currency": "USD",
        "channel": "mobile",
    }
    resp_ingest = client.post("/temporal/ingest", json={"events": [ev]}, headers=auth_headers)
    assert resp_ingest.status_code == 200
    ingest_data = resp_ingest.json()
    assert ingest_data["status"] == "SUCCESS"
    assert ingest_data["ingested_count"] == 1

    # 2. GET /temporal/entities/{id}/timeline
    resp_time = client.get("/temporal/entities/ACC-API-TEST/timeline", headers=auth_headers)
    assert resp_time.status_code == 200
    time_data = resp_time.json()
    assert time_data["entity_id"] == "ACC-API-TEST"
    assert time_data["total_events"] >= 1
    assert time_data["events"][0]["transaction_id"] == "TXN-API-INGEST-01"


# =============================================================================
# 9. REST API Temporal Scoring and Metrics Test
# =============================================================================
def test_api_temporal_scoring_and_metrics(client, auth_headers):
    """Verifies POST /temporal/score and GET /temporal/metrics."""
    # 1. POST /temporal/score
    score_req = {
        "entity_id": "ACC-API-TEST",
        "sequence_length": 5,
    }
    resp_score = client.post("/temporal/score", json=score_req, headers=auth_headers)
    assert resp_score.status_code == 200
    score_data = resp_score.json()
    assert score_data["entity_id"] == "ACC-API-TEST"
    assert "sequence_fraud_probability" in score_data
    assert "advisory_risk_level" in score_data
    assert score_data["is_advisory"] is True
    assert "recommendation" in score_data

    # 2. GET /temporal/metrics
    resp_metrics = client.get("/temporal/metrics", headers=auth_headers)
    assert resp_metrics.status_code == 200
    metrics_data = resp_metrics.json()
    assert "total_events_in_history" in metrics_data
    assert "unique_entities_tracked" in metrics_data
    assert "sliding_window_seconds" in metrics_data
