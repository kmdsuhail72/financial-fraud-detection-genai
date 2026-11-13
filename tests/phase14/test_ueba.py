"""Unit and Integration Tests for Phase 14 Enterprise Security Analytics & UEBA."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Prevent AWS metadata queries during testing
os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.app import app
from security.auth import create_test_token
from ueba.correlation_engine import FraudThreatCorrelationEngine
from ueba.feature_engineer import UEBAFeatureEngineer
from ueba.ml_engine import IsolationForestAnomalyDetector
from ueba.models import (
    BehavioralBaseline,
    BehavioralFeatures,
    CorrelateRiskRequest,
    EntityRiskLevel,
    PeerGroup,
    ScoreEventRequest,
    UserEntityProfile,
)
from ueba.profile_store import ProfileStore
from ueba.rule_engine import UEBARuleEngine


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_test_token(
        sub="analyst-1",
        email="analyst@finguard.internal",
        roles=["Investigator", "Analyst"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_baseline():
    return BehavioralBaseline(
        avg_amount=100.0,
        std_amount=20.0,
        max_amount_historical=300.0,
        active_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17],
        known_devices=["dev_phone_1", "dev_laptop_1"],
        known_ips=["198.51.100.10"],
        known_cities=["New York"],
        daily_velocity_mean=2.0,
        hourly_velocity_mean=0.3,
    )


# 1. Feature Engineering Test
def test_feature_engineer_baseline_deviation(sample_baseline):
    engineer = UEBAFeatureEngineer()

    # Normal transaction
    event_normal = {
        "amount": 105.0,
        "hour_of_day": 11,
        "device_id": "dev_phone_1",
        "ip_address": "198.51.100.10",
        "city": "New York",
        "velocity_1h": 1,
        "velocity_24h": 2,
    }
    feats_norm = engineer.extract_features(event_normal, sample_baseline)
    assert 1.0 <= feats_norm.amount_deviation_ratio <= 1.1
    assert -0.5 <= feats_norm.amount_z_score <= 0.5
    assert not feats_norm.is_off_hours
    assert not feats_norm.is_new_device
    assert not feats_norm.is_new_ip
    assert not feats_norm.is_new_city
    assert not feats_norm.impossible_travel_flag

    # Anomalous transaction
    event_anom = {
        "amount": 950.0,
        "hour_of_day": 3,
        "device_id": "dev_unknown_rogue",
        "ip_address": "203.0.113.88",
        "city": "Tokyo",
        "velocity_1h": 4,
        "velocity_24h": 7,
    }
    feats_anom = engineer.extract_features(event_anom, sample_baseline)
    assert feats_anom.amount_deviation_ratio >= 9.0
    assert feats_anom.amount_z_score >= 40.0
    assert feats_anom.is_off_hours
    assert feats_anom.is_new_device
    assert feats_anom.is_new_ip
    assert feats_anom.is_new_city
    assert feats_anom.impossible_travel_flag


# 2. Feature Vector Conversion Test
def test_feature_vector_conversion():
    feats = BehavioralFeatures(
        amount=500.0,
        amount_deviation_ratio=5.0,
        amount_z_score=4.2,
        is_off_hours=True,
        is_new_device=True,
        is_new_ip=False,
        is_new_city=True,
        velocity_1h=3,
        velocity_24h=6,
        velocity_z_score=2.5,
        impossible_travel_flag=True,
    )
    vec = UEBAFeatureEngineer.to_feature_vector(feats)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (8,)
    assert vec[0] == 5.0  # deviation ratio
    assert vec[1] == 4.2  # amount z-score
    assert vec[2] == 1.0  # is_off_hours
    assert vec[3] == 1.0  # is_new_device
    assert vec[4] == 0.0  # is_new_ip
    assert vec[5] == 1.0  # is_new_city
    assert vec[6] == 3.0  # velocity_1h
    assert vec[7] == 2.5  # velocity_z_score


# 3. Rule Engine Anomaly Triggers Test
def test_rule_engine_anomalies():
    engine = UEBARuleEngine()

    # Rule 1: UNUSUAL_AMOUNT_SPIKE
    feats_spike = BehavioralFeatures(
        amount=1200.0,
        amount_deviation_ratio=7.5,
        amount_z_score=4.5,
    )
    flags = engine.evaluate_rules(feats_spike)
    assert "UNUSUAL_AMOUNT_SPIKE" in flags

    # Rule 2: OFF_HOURS_ELEVATED_VALUE
    feats_off_hours = BehavioralFeatures(
        amount=400.0,
        amount_deviation_ratio=3.0,
        is_off_hours=True,
    )
    flags = engine.evaluate_rules(feats_off_hours)
    assert "OFF_HOURS_ELEVATED_VALUE" in flags

    # Rule 3: NEW_DEVICE_BURST
    feats_burst = BehavioralFeatures(
        amount=100.0,
        is_new_device=True,
        velocity_1h=5,
    )
    flags = engine.evaluate_rules(feats_burst)
    assert "NEW_DEVICE_BURST" in flags

    # Rule 4: IMPOSSIBLE_TRAVEL_VELOCITY
    feats_travel = BehavioralFeatures(
        amount=150.0,
        impossible_travel_flag=True,
    )
    flags = engine.evaluate_rules(feats_travel)
    assert "IMPOSSIBLE_TRAVEL_VELOCITY" in flags


# 4. Isolation Forest ML Engine Test
def test_isolation_forest_detector_fit_and_score(sample_baseline):
    detector = IsolationForestAnomalyDetector(n_estimators=50, contamination=0.1, random_state=42)

    # Generate training baseline features
    normal_features = [
        BehavioralFeatures(
            amount=100.0,
            amount_deviation_ratio=1.0 + float(i % 3) * 0.1,
            amount_z_score=float(i % 3) * 0.2,
            is_off_hours=False,
            is_new_device=False,
            is_new_ip=False,
            is_new_city=False,
            velocity_1h=1,
            velocity_z_score=0.1,
        )
        for i in range(100)
    ]
    detector.fit(normal_features)

    # Score normal feature
    score_normal = detector.score_sample(normal_features[0])
    assert 0.0 <= score_normal <= 1.0

    # Score anomaly feature
    anomaly_feat = BehavioralFeatures(
        amount=5000.0,
        amount_deviation_ratio=15.0,
        amount_z_score=20.0,
        is_off_hours=True,
        is_new_device=True,
        is_new_ip=True,
        is_new_city=True,
        velocity_1h=8,
        velocity_z_score=6.0,
        impossible_travel_flag=True,
    )
    score_anomaly = detector.score_sample(anomaly_feat)
    assert score_anomaly > score_normal

    # Model save & load test
    save_path = Path("data/test_iforest.joblib")
    try:
        detector.save(str(save_path))
        loaded = IsolationForestAnomalyDetector.load(str(save_path))
        score_loaded = loaded.score_sample(anomaly_feat)
        assert abs(score_loaded - score_anomaly) < 1e-4
    finally:
        if save_path.exists():
            save_path.unlink()


# 5. Fraud Threat Correlation Engine Test
def test_fraud_threat_correlation_engine():
    correlator = FraudThreatCorrelationEngine()

    # High multi-signal threat
    result = correlator.correlate(
        entity_id="CUS-100099",
        event_id="EVT-202611-9999",
        ueba_anomaly_score=0.92,
        fraud_probability=0.88,
        ioc_reputation_score=85.0,
        security_finding_severity=9.0,
    )
    assert result.blended_risk_score >= 80.0
    assert result.risk_level == EntityRiskLevel.CRITICAL
    assert len(result.correlated_signals) >= 3
    assert any("Immediate Account Hold" in rec for rec in result.investigation_recommendations)

    # Low risk nominal event
    nominal = correlator.correlate(
        entity_id="CUS-100001",
        event_id="EVT-202611-0001",
        ueba_anomaly_score=0.15,
        fraud_probability=0.05,
        ioc_reputation_score=0.0,
        security_finding_severity=0.0,
    )
    assert nominal.blended_risk_score < 35.0
    assert nominal.risk_level == EntityRiskLevel.LOW


# 6. Profile Store CRUD Test
def test_profile_store_crud():
    store = ProfileStore()  # In-memory default seeded
    assert store.count() >= 30

    profiles = store.list_profiles(limit=10)
    assert len(profiles) == 10

    # Filter by Peer Group
    retail = store.list_profiles(peer_group=PeerGroup.RETAIL)
    assert all(p.peer_group == PeerGroup.RETAIL for p in retail)

    # Filter by Risk Level
    critical = store.list_profiles(risk_level=EntityRiskLevel.CRITICAL)
    assert all(p.risk_level == EntityRiskLevel.CRITICAL for p in critical)

    # Fetch and update single profile
    first_id = profiles[0].entity_id
    prof = store.get_profile(first_id)
    assert prof is not None
    prof.current_risk_score = 99.0
    prof.risk_level = EntityRiskLevel.CRITICAL
    store.save_profile(prof)

    updated = store.get_profile(first_id)
    assert updated.current_risk_score == 99.0
    assert updated.risk_level == EntityRiskLevel.CRITICAL


# 7. API GET Endpoints Test (/ueba/metrics & /ueba/entities)
def test_api_get_entities_and_metrics(client, auth_headers):
    # Metrics
    resp_metrics = client.get("/ueba/metrics", headers=auth_headers)
    assert resp_metrics.status_code == 200
    metrics = resp_metrics.json()
    assert metrics["total_entities"] >= 30
    assert "critical_risk_count" in metrics
    assert "avg_risk_score" in metrics
    assert "peer_group_counts" in metrics

    # Entities
    resp_entities = client.get("/ueba/entities?limit=5", headers=auth_headers)
    assert resp_entities.status_code == 200
    entities = resp_entities.json()
    assert len(entities) == 5
    assert "entity_id" in entities[0]
    assert "baseline" in entities[0]

    # Single Entity Profile
    test_id = entities[0]["entity_id"]
    resp_single = client.get(f"/ueba/entities/{test_id}", headers=auth_headers)
    assert resp_single.status_code == 200
    assert resp_single.json()["entity_id"] == test_id


# 8. API Scoring and Correlation Endpoints Test (/ueba/score & /ueba/correlate)
def test_api_score_and_correlate_endpoints(client, auth_headers):
    # Score event
    score_payload = {
        "entity_id": "CUS-100001",
        "event_id": "EVT-TEST-001",
        "amount": 2500.0,
        "currency": "USD",
        "hour_of_day": 3,
        "device_id": "dev_test_device",
        "ip_address": "203.0.113.19",
        "city": "Unknown City",
        "velocity_1h": 3,
        "velocity_24h": 5,
    }
    resp_score = client.post("/ueba/score", json=score_payload, headers=auth_headers)
    assert resp_score.status_code == 200
    score_data = resp_score.json()
    assert "anomaly_score" in score_data
    assert "rule_flags" in score_data
    assert "explanation" in score_data

    # Correlate risk
    correlate_payload = {
        "entity_id": "CUS-100001",
        "event_id": "EVT-TEST-001",
        "ueba_anomaly_score": score_data["anomaly_score"],
        "fraud_probability": 0.85,
        "ioc_reputation_score": 75.0,
        "security_finding_severity": 8.0,
    }
    resp_corr = client.post("/ueba/correlate", json=correlate_payload, headers=auth_headers)
    assert resp_corr.status_code == 200
    corr_data = resp_corr.json()
    assert corr_data["blended_risk_score"] > 60.0
    assert corr_data["risk_level"] in ["HIGH", "CRITICAL"]
    assert len(corr_data["investigation_recommendations"]) > 0

