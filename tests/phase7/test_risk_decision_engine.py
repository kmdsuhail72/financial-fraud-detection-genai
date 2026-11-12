"""
Tests for Risk Decision Engine.
"""
import pytest
from lambda_scoring.risk_engine import RiskDecisionEngine


def test_risk_decision_high_fraud():
    """Verify high risk calculation matches exact formula and triggers investigation."""
    engine = RiskDecisionEngine(
        threshold_high=0.60,
        threshold_review=0.35,
        weight_fraud_probability=0.65,
        weight_anomaly_score=0.35,
    )

    # Example from Phase 7 prompt: P=0.87, A=0.72 -> R = 0.65*0.87 + 0.35*0.72 = 0.8175
    decision = engine.calculate_risk(
        transaction_id="txn-10001",
        fraud_probability=0.87,
        anomaly_score=0.72,
    )

    assert decision.transaction_id == "txn-10001"
    assert decision.fraud_probability == 0.87
    assert decision.anomaly_score == 0.72
    assert decision.risk_score == 0.8175
    assert decision.risk_level == "HIGH"
    assert decision.action == "INVESTIGATE"
    assert decision.requires_investigation is True


def test_risk_decision_review_tier():
    """Verify medium risk transaction enters REVIEW tier."""
    engine = RiskDecisionEngine(threshold_high=0.60, threshold_review=0.35)

    decision = engine.calculate_risk(
        transaction_id="txn-10002",
        fraud_probability=0.45,
        anomaly_score=0.30,
    )

    # R = 0.65*0.45 + 0.35*0.30 = 0.2925 + 0.105 = 0.3975
    assert decision.risk_score == 0.3975
    assert decision.risk_level == "REVIEW"
    assert decision.action == "REVIEW"
    assert decision.requires_investigation is False


def test_risk_decision_low_tier():
    """Verify normal transaction enters LOW tier."""
    engine = RiskDecisionEngine(threshold_high=0.60, threshold_review=0.35)

    decision = engine.calculate_risk(
        transaction_id="txn-10003",
        fraud_probability=0.05,
        anomaly_score=0.10,
    )

    # R = 0.65*0.05 + 0.35*0.10 = 0.0325 + 0.035 = 0.0675
    assert decision.risk_score == 0.0675
    assert decision.risk_level == "LOW"
    assert decision.action == "ALLOW"
    assert decision.requires_investigation is False

