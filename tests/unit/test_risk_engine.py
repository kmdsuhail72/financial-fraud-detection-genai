"""
Unit test for Unified Risk Score calculation:
R = 100 * (0.65 * P + 0.35 * A)
"""
import pytest


def calculate_risk(p_supervised: float, a_anomaly: float) -> float:
    return round(100.0 * (0.65 * p_supervised + 0.35 * a_anomaly), 2)


def test_risk_score_bounds():
    # Minimum boundary
    assert calculate_risk(0.0, 0.0) == 0.0
    # Maximum boundary
    assert calculate_risk(1.0, 1.0) == 100.0


def test_risk_score_sample():
    # P = 0.9250, A = 0.8800 -> 100 * (0.65 * 0.9250 + 0.35 * 0.8800) = 100 * (0.60125 + 0.308) = 90.93
    assert calculate_risk(0.9250, 0.8800) == 90.93


def test_risk_tier_classification():
    score = calculate_risk(0.9250, 0.8800)
    assert score >= 80.0  # CRITICAL tier

