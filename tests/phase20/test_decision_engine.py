"""Unit and Integration Tests for Phase 20 Enterprise Fraud Decision Engine & Risk Orchestration.

Validates:
1. Multi-signal weighted fusion across ML (35%), UEBA (20%), Graph (20%), Temporal (15%), Threat Intel (10%).
2. Dynamic weight renormalization and signal coverage tracking for missing signals.
3. Default risk policy mapping: LOW (P3), MEDIUM (P2), HIGH (P1), CRITICAL (P0).
4. Dynamic risk policy configuration update and semantic versioning.
5. Explainable decision risk reasons and signal attribution breakdown.
6. Decision store idempotency and deduplication per transaction ID.
7. REST API: GET /decisions/health and GET /decisions/policies/active.
8. REST API: POST /decisions with full and partial signal payloads.
9. REST API: GET /decisions query filtering by priority/classification and GET /decisions/{id}.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from api.app import app
from decision.engine import RiskFusionEngine
from decision.models import (
    DecisionAction,
    DecisionRequest,
    FraudClassification,
    FraudDecisionResponse,
    RiskPolicyConfig,
    RiskPriority,
    SignalPayload,
)
from decision.service import DecisionService, get_decision_service
from decision.store import DecisionStore
from security.auth import create_test_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def clean_engine():
    return RiskFusionEngine()


@pytest.fixture
def clean_store():
    return DecisionStore()


# =============================================================================
# 1. Multi-Signal Weighted Fusion Test
# =============================================================================
def test_multi_signal_weighted_fusion(clean_engine):
    """Verifies weighted multi-signal fusion when all 5 detection pillars are present."""
    req = DecisionRequest(
        transaction_id="TXN-FUSION-001",
        account_id="ACC-001",
        amount=12000.0,
        signals=SignalPayload(
            ml_score=0.90,          # 0.90 * 0.35 = 0.315
            ueba_anomaly_score=0.80, # 0.80 * 0.20 = 0.160
            graph_risk_score=0.85,  # 0.85 * 0.20 = 0.170
            temporal_risk_score=0.90,# 0.90 * 0.15 = 0.135
            threat_intel_score=0.70, # 0.70 * 0.10 = 0.070
        ),
    )
    decision = clean_engine.evaluate(req)

    # Sum = 0.315 + 0.160 + 0.170 + 0.135 + 0.070 = 0.850
    assert pytest.approx(decision.composite_risk_score, 0.001) == 0.850
    assert decision.signals_evaluated == 5
    assert decision.signal_coverage_pct == 100.0
    assert decision.classification == FraudClassification.HIGH
    assert decision.priority == RiskPriority.P1
    assert decision.recommended_action == DecisionAction.CHALLENGE


# =============================================================================
# 2. Missing Signal Renormalization Test
# =============================================================================
def test_missing_signal_renormalization(clean_engine):
    """Verifies that missing signals are excluded and remaining weights renormalized."""
    # Only ML (weight: 0.35) and Graph (weight: 0.20) present -> Active weight sum = 0.55
    req = DecisionRequest(
        transaction_id="TXN-RENORM-001",
        account_id="ACC-002",
        amount=500.0,
        signals=SignalPayload(
            ml_score=0.80,
            graph_risk_score=0.60,
            # ueba, temporal, threat_intel are None
        ),
    )
    decision = clean_engine.evaluate(req)

    # Renormalized weights:
    # ML: 0.35 / 0.55 = 0.63636...
    # Graph: 0.20 / 0.55 = 0.36363...
    # Expected score: 0.80 * (0.35/0.55) + 0.60 * (0.20/0.55) = 0.50909 + 0.21818 = 0.7273
    expected_score = round((0.80 * (0.35 / 0.55)) + (0.60 * (0.20 / 0.55)), 4)
    assert pytest.approx(decision.composite_risk_score, 0.001) == expected_score
    assert decision.signals_evaluated == 2
    assert decision.signal_coverage_pct == 40.0
    assert len(decision.signal_contributions) == 2


# =============================================================================
# 3. Risk Policy Priority Classification Test
# =============================================================================
def test_risk_policy_priority_classification(clean_engine):
    """Verifies mapping across all 4 default risk bands (P0, P1, P2, P3)."""
    # 1. LOW / P3 (<= 0.35)
    r_low = clean_engine.evaluate(
        DecisionRequest(
            transaction_id="TXN-P3",
            account_id="ACC-1",
            amount=50.0,
            signals=SignalPayload(ml_score=0.10, ueba_anomaly_score=0.20),
        )
    )
    assert r_low.classification == FraudClassification.LOW
    assert r_low.priority == RiskPriority.P3
    assert r_low.recommended_action == DecisionAction.APPROVE

    # 2. MEDIUM / P2 (0.35 - 0.70)
    r_med = clean_engine.evaluate(
        DecisionRequest(
            transaction_id="TXN-P2",
            account_id="ACC-2",
            amount=500.0,
            signals=SignalPayload(ml_score=0.55, ueba_anomaly_score=0.50),
        )
    )
    assert r_med.classification == FraudClassification.MEDIUM
    assert r_med.priority == RiskPriority.P2
    assert r_med.recommended_action == DecisionAction.MONITOR

    # 3. HIGH / P1 (0.70 - 0.90)
    r_high = clean_engine.evaluate(
        DecisionRequest(
            transaction_id="TXN-P1",
            account_id="ACC-3",
            amount=5000.0,
            signals=SignalPayload(ml_score=0.82, ueba_anomaly_score=0.75),
        )
    )
    assert r_high.classification == FraudClassification.HIGH
    assert r_high.priority == RiskPriority.P1
    assert r_high.recommended_action == DecisionAction.CHALLENGE

    # 4. CRITICAL / P0 (> 0.90)
    r_crit = clean_engine.evaluate(
        DecisionRequest(
            transaction_id="TXN-P0",
            account_id="ACC-4",
            amount=50000.0,
            signals=SignalPayload(ml_score=0.98, ueba_anomaly_score=0.95),
        )
    )
    assert r_crit.classification == FraudClassification.CRITICAL
    assert r_crit.priority == RiskPriority.P0
    assert r_crit.recommended_action == DecisionAction.ESCALATE


# =============================================================================
# 4. Dynamic Policy Update and Versioning Test
# =============================================================================
def test_dynamic_policy_update_and_versioning(clean_engine):
    """Verifies runtime policy threshold updates and version tracking."""
    custom_policy = RiskPolicyConfig(
        policy_id="POL-CUSTOM-STRICT",
        policy_version="2026.11-strict-v2",
        thresholds={"low_max": 0.20, "medium_max": 0.50, "high_max": 0.75},
        weights={"ml": 0.50, "ueba": 0.50},
    )
    clean_engine.update_policy(custom_policy)

    assert clean_engine.policy.policy_version == "2026.11-strict-v2"

    # Score of 0.60 was MEDIUM in default policy, but becomes HIGH in strict policy (0.50 < score <= 0.75)
    r = clean_engine.evaluate(
        DecisionRequest(
            transaction_id="TXN-STRICT-01",
            account_id="ACC-STRICT",
            amount=100.0,
            signals=SignalPayload(ml_score=0.60, ueba_anomaly_score=0.60),
        )
    )
    assert r.classification == FraudClassification.HIGH
    assert r.priority == RiskPriority.P1
    assert r.policy_version == "2026.11-strict-v2"


# =============================================================================
# 5. Explainable Reasons and Signal Attribution Test
# =============================================================================
def test_explainable_reasons_and_signal_attribution(clean_engine):
    """Verifies that decision explanations highlight leading drivers and context flags."""
    req = DecisionRequest(
        transaction_id="TXN-EXPLAIN-01",
        account_id="ACC-EXP",
        amount=15000.0,
        signals=SignalPayload(
            ml_score=0.95,
            temporal_risk_score=0.90,
            metadata={"is_emulator": True, "velocity_burst": True},
        ),
    )
    decision = clean_engine.evaluate(req)

    assert len(decision.risk_reasons) >= 3
    reasons_text = " ".join(decision.risk_reasons)
    assert "ML" in reasons_text or "Leading risk driver" in reasons_text
    assert "emulator" in reasons_text.lower()
    assert "velocity" in reasons_text.lower()


# =============================================================================
# 6. Decision Store Idempotency Test
# =============================================================================
def test_decision_store_idempotency(clean_store, clean_engine):
    """Verifies that repeated evaluation of identical transaction ID returns existing decision."""
    service = DecisionService(engine=clean_engine, store=clean_store)

    req = DecisionRequest(
        transaction_id="TXN-IDEMP-001",
        account_id="ACC-IDEMP",
        amount=1000.0,
        signals=SignalPayload(ml_score=0.85),
    )

    dec_1 = service.evaluate_transaction(req)
    dec_2 = service.evaluate_transaction(req)

    assert dec_1.decision_id == dec_2.decision_id
    assert dec_1.timestamp == dec_2.timestamp
    assert len(clean_store.list_decisions()) == 1


# =============================================================================
# 7. REST API Health and Active Policy Endpoints Test
# =============================================================================
def test_api_decision_health_and_active_policy(client, auth_headers):
    """Verifies GET /decisions/health and GET /decisions/policies/active."""
    # 1. GET /decisions/health
    resp_health = client.get("/decisions/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "HEALTHY"

    # 2. GET /decisions/policies/active
    resp_pol = client.get("/decisions/policies/active", headers=auth_headers)
    assert resp_pol.status_code == 200
    pol_data = resp_pol.json()
    assert "weights" in pol_data
    assert pol_data["weights"]["ml"] == 0.35
    assert pol_data["weights"]["graph"] == 0.20


# =============================================================================
# 8. REST API Create Decision Test
# =============================================================================
def test_api_create_decision(client, auth_headers):
    """Verifies POST /decisions endpoint with full multi-signal payload."""
    payload = {
        "transaction_id": "TXN-API-DEC-001",
        "account_id": "ACC-API-BURST",
        "amount": 14500.0,
        "currency": "USD",
        "signals": {
          "ml_score": 0.94,
          "ueba_anomaly_score": 0.88,
          "graph_risk_score": 0.96,
          "temporal_risk_score": 0.98,
          "threat_intel_score": 0.92,
          "metadata": {
            "is_emulator": True,
            "velocity_burst": True
          }
        }
    }
    resp = client.post("/decisions", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    dec = resp.json()
    assert dec["transaction_id"] == "TXN-API-DEC-001"
    assert dec["composite_risk_score"] >= 0.90
    assert dec["priority"] == "P0"
    assert dec["classification"] == "CRITICAL"
    assert dec["recommended_action"] == "ESCALATE"
    assert dec["signal_coverage_pct"] == 100.0


# =============================================================================
# 9. REST API List and Get Decision Endpoints Test
# =============================================================================
def test_api_list_and_get_decision(client, auth_headers):
    """Verifies GET /decisions with priority filter and GET /decisions/{id}."""
    # 1. List with priority filter
    resp_list = client.get("/decisions?priority=P0", headers=auth_headers)
    assert resp_list.status_code == 200
    decisions = resp_list.json()
    assert isinstance(decisions, list)
    assert len(decisions) >= 1
    assert decisions[0]["priority"] == "P0"

    # 2. Get by valid ID
    dec_id = decisions[0]["decision_id"]
    resp_get = client.get(f"/decisions/{dec_id}", headers=auth_headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["decision_id"] == dec_id

    # 3. Get invalid ID
    resp_invalid = client.get("/decisions/DEC-NONEXISTENT-999", headers=auth_headers)
    assert resp_invalid.status_code == 404

