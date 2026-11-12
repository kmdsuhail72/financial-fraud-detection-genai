"""
FinGuard AI — Real-Time Risk Decision Engine (Phase 7).

Evaluates model outputs against bank risk policies to categorize
transactions into LOW, REVIEW, or HIGH risk, and flags accounts requiring investigation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

RiskLevel = Literal["LOW", "REVIEW", "HIGH"]
RiskAction = Literal["ALLOW", "REVIEW", "INVESTIGATE"]


@dataclass(frozen=True)
class RiskDecision:
    transaction_id: str
    fraud_probability: float
    anomaly_score: float
    risk_score: float
    risk_level: RiskLevel
    action: RiskAction
    requires_investigation: bool
    reason: str


class RiskDecisionEngine:
    """
    Computes unified risk scores and applies financial institution risk thresholds.
    """

    def __init__(
        self,
        threshold_high: float = 0.60,
        threshold_review: float = 0.35,
        weight_fraud_probability: float = 0.65,
        weight_anomaly_score: float = 0.35,
    ):
        self.threshold_high = threshold_high
        self.threshold_review = threshold_review
        self.w_fraud = weight_fraud_probability
        self.w_anomaly = weight_anomaly_score

    def calculate_risk(
        self,
        transaction_id: str,
        fraud_probability: float,
        anomaly_score: float,
    ) -> RiskDecision:
        """
        Calculates composite risk score:
            R = (w_fraud * P_fraud) + (w_anomaly * A_anomaly)
        and classifies into LOW, REVIEW, or HIGH.
        """
        # Clamp inputs
        p = max(0.0, min(1.0, float(fraud_probability)))
        a = max(0.0, min(1.0, float(anomaly_score)))

        # Weighted composite score
        combined_score = (self.w_fraud * p) + (self.w_anomaly * a)
        combined_score = round(combined_score, 4)

        if combined_score >= self.threshold_high:
            level: RiskLevel = "HIGH"
            action: RiskAction = "INVESTIGATE"
            requires_investigation = True
            reason = f"Combined risk score ({combined_score:.4f}) exceeds HIGH threshold ({self.threshold_high:.2f})"
        elif combined_score >= self.threshold_review:
            level = "REVIEW"
            action = "REVIEW"
            requires_investigation = False
            reason = f"Combined risk score ({combined_score:.4f}) exceeds REVIEW threshold ({self.threshold_review:.2f})"
        else:
            level = "LOW"
            action = "ALLOW"
            requires_investigation = False
            reason = f"Risk score ({combined_score:.4f}) within normal operating bounds"

        return RiskDecision(
            transaction_id=transaction_id,
            fraud_probability=round(p, 4),
            anomaly_score=round(a, 4),
            risk_score=combined_score,
            risk_level=level,
            action=action,
            requires_investigation=requires_investigation,
            reason=reason,
        )
