"""Phase 20 — Multi-Signal Risk Fusion Engine with Dynamic Renormalization & Priority Orchestration."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from decision.models import (
    DecisionAction,
    DecisionRequest,
    FraudClassification,
    FraudDecisionResponse,
    RiskPolicyConfig,
    RiskPriority,
    SignalContribution,
    SignalPayload,
)

logger = logging.getLogger("finguard-decision-engine")


class RiskFusionEngine:
    """
    Evaluates multi-signal telemetry across ML, UEBA, Graph, Temporal, and Threat Intel pillars.
    Performs dynamic weight renormalization for missing signals and maps scores to risk policies.
    """

    ALL_SIGNALS = ["ml", "ueba", "graph", "temporal", "threat_intel"]

    SIGNAL_DESCRIPTIONS = {
        "ml": "Ensemble ML model statistical fraud probability (Phase 7)",
        "ueba": "Behavioral deviation from user/account baseline (Phase 14)",
        "graph": "Graph community, centrality & GNN latent risk (Phase 16-18)",
        "temporal": "Temporal velocity burst & GRU sequence risk (Phase 19)",
        "threat_intel": "Threat intelligence IOC & IP/domain reputation (Phase 13)",
    }

    def __init__(self, policy: Optional[RiskPolicyConfig] = None):
        self.policy = policy or RiskPolicyConfig()

    def evaluate(self, request: DecisionRequest) -> FraudDecisionResponse:
        """
        Executes multi-signal fusion:
        1. Identifies present vs missing signals.
        2. Renormalizes weights over active signals.
        3. Computes composite risk score.
        4. Maps to policy thresholds (P0, P1, P2, P3).
        5. Synthesizes explainable decision reasons.
        """
        signals = request.signals

        # Map signal payload attributes to dictionary
        raw_signals: Dict[str, Optional[float]] = {
            "ml": signals.ml_score,
            "ueba": signals.ueba_anomaly_score,
            "graph": signals.graph_risk_score,
            "temporal": signals.temporal_risk_score,
            "threat_intel": signals.threat_intel_score,
        }

        # Filter active signals
        active_signals = {k: v for k, v in raw_signals.items() if v is not None}
        total_available = len(self.ALL_SIGNALS)
        covered_count = len(active_signals)
        coverage_pct = round((covered_count / total_available) * 100.0, 1)

        contributions: List[SignalContribution] = []
        composite_score = 0.0

        if not active_signals:
            # Nominal default if zero signals provided
            composite_score = 0.05
        else:
            # 1. Renormalize weights
            active_weight_sum = sum(self.policy.weights.get(k, 0.0) for k in active_signals)
            if active_weight_sum <= 0.0:
                active_weight_sum = 1.0

            # 2. Weighted multi-signal fusion
            for sig_name, raw_val in active_signals.items():
                base_w = self.policy.weights.get(sig_name, 0.0)
                eff_w = base_w / active_weight_sum
                weighted_val = eff_w * raw_val
                composite_score += weighted_val

            composite_score = min(1.0, max(0.0, round(composite_score, 4)))

            # 3. Compute percentage contributions
            for sig_name, raw_val in active_signals.items():
                base_w = self.policy.weights.get(sig_name, 0.0)
                eff_w = base_w / active_weight_sum
                weighted_val = eff_w * raw_val
                pct_contrib = (weighted_val / composite_score * 100.0) if composite_score > 0 else 0.0

                contributions.append(
                    SignalContribution(
                        signal_name=sig_name,
                        raw_score=round(raw_val, 4),
                        effective_weight=round(eff_w, 4),
                        weighted_score=round(weighted_val, 4),
                        percentage_contribution=round(pct_contrib, 1),
                    )
                )

        # Sort contributions by weighted score descending
        contributions.sort(key=lambda c: c.weighted_score, reverse=True)

        # 4. Map to Policy Thresholds
        classification, priority, action = self._classify_score(composite_score)

        # 5. Synthesize Explainable Reasons
        reasons = self._generate_explainability(
            composite_score=composite_score,
            classification=classification,
            priority=priority,
            contributions=contributions,
            coverage_pct=coverage_pct,
            missing_signals=[s for s in self.ALL_SIGNALS if s not in active_signals],
            metadata=signals.metadata,
        )

        decision_id = f"DEC-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        return FraudDecisionResponse(
            decision_id=decision_id,
            transaction_id=request.transaction_id,
            account_id=request.account_id,
            timestamp=round(time.time(), 2),
            composite_risk_score=composite_score,
            classification=classification,
            priority=priority,
            recommended_action=action,
            signal_coverage_pct=coverage_pct,
            signals_evaluated=covered_count,
            signal_contributions=contributions,
            risk_reasons=reasons,
            policy_version=self.policy.policy_version,
            is_advisory=True,
        )

    def _classify_score(self, score: float) -> Tuple[FraudClassification, RiskPriority, DecisionAction]:
        th = self.policy.thresholds
        low_max = th.get("low_max", 0.35)
        med_max = th.get("medium_max", 0.70)
        high_max = th.get("high_max", 0.90)

        if score <= low_max:
            return FraudClassification.LOW, RiskPriority.P3, DecisionAction.APPROVE
        elif score <= med_max:
            return FraudClassification.MEDIUM, RiskPriority.P2, DecisionAction.MONITOR
        elif score <= high_max:
            return FraudClassification.HIGH, RiskPriority.P1, DecisionAction.CHALLENGE
        else:
            return FraudClassification.CRITICAL, RiskPriority.P0, DecisionAction.ESCALATE

    def _generate_explainability(
        self,
        composite_score: float,
        classification: FraudClassification,
        priority: RiskPriority,
        contributions: List[SignalContribution],
        coverage_pct: float,
        missing_signals: List[str],
        metadata: Dict[str, Any],
    ) -> List[str]:
        reasons: List[str] = []

        # 1. Primary classification reason
        reasons.append(
            f"Composite risk score of {composite_score:.2f} maps to {classification.value} classification (Priority {priority.value})."
        )

        # 2. Leading signal attribution
        if contributions:
            top = contributions[0]
            reasons.append(
                f"Leading risk driver: '{top.signal_name.upper()}' signal (score: {top.raw_score:.2f}, {top.percentage_contribution:.1f}% contribution)."
            )

        # 3. Contextual flags
        if metadata.get("is_emulator"):
            reasons.append("Critical red flag: Hardware emulator profile observed in device metadata.")
        if metadata.get("is_tor") or metadata.get("is_vpn"):
            reasons.append("Network red flag: Traffic ingress through anonymized Tor or proxy network.")
        if metadata.get("velocity_burst"):
            reasons.append("Temporal red flag: High-frequency transaction velocity burst within 5-minute window.")

        # 4. Signal coverage note
        if missing_signals:
            missing_str = ", ".join(s.upper() for s in missing_signals)
            reasons.append(
                f"Signal coverage: {coverage_pct:.0f}% ({len(contributions)}/5 signals present). Excluded [{missing_str}] and renormalized remaining weights."
            )
        else:
            reasons.append("Full multi-signal coverage: 100% of detection pillars evaluated.")

        return reasons

    def update_policy(self, updated_policy: RiskPolicyConfig) -> RiskPolicyConfig:
        """Dynamically updates active policy configuration."""
        self.policy = updated_policy
        logger.info("Updated active risk policy to version: %s", updated_policy.policy_version)
        return self.policy

