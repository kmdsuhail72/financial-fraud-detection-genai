"""
FinGuard AI — Phase 24 Customer Risk Profiling Engine.
Calculates explainable rules-based risk scores and assigns risk tiers (LOW, MEDIUM, HIGH, CRITICAL).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from aml.models import (
    AMLAlert,
    AMLRuleType,
    CustomerRiskProfile,
    CustomerRiskTier,
)


class CustomerRiskProfiler:
    """Calculates explainable rules-based customer AML risk scores and maintains profiles."""

    def calculate_risk(
        self,
        profile: CustomerRiskProfile,
        new_alerts: List[AMLAlert],
        incremental_volume: float = 0.0,
    ) -> CustomerRiskProfile:
        score = 15  # Baseline score for active retail customer
        factors: List[str] = []

        # PEP Risk
        if profile.pep_flag:
            score += 35
            factors.append("Politically Exposed Person (PEP) designation")

        # Jurisdiction Risk
        high_risk_countries = ["IR", "KP", "SY", "RU", "MM", "CU"]
        if profile.country.upper() in high_risk_countries:
            score += 25
            factors.append(f"High-risk non-cooperative jurisdiction ({profile.country})")

        # Historical & New Alerts
        total_alerts = profile.lifetime_aml_alerts_count + len(new_alerts)
        if total_alerts > 0:
            alert_penalty = min(40, total_alerts * 15)
            score += alert_penalty
            factors.append(f"Recorded {total_alerts} AML transaction monitoring alert(s)")

        # Specific Severe Alert Flags
        has_structuring = any(
            a.rule_type == AMLRuleType.POSSIBLE_STRUCTURING for a in new_alerts
        ) or any("structuring" in f.lower() for f in profile.risk_factors)
        if has_structuring:
            score += 20
            factors.append("Active structuring / smurfing pattern detected")

        # Transaction Volume
        new_total_vol = profile.total_transaction_volume + incremental_volume
        if new_total_vol >= 50000.0:
            score += 10
            factors.append(f"Cumulative transaction volume exceeds $50,000 (${new_total_vol:,.2f})")

        # Cap score at 100
        score = min(100, max(5, score))

        # Determine Tier
        if score >= 81:
            tier = CustomerRiskTier.CRITICAL
        elif score >= 61:
            tier = CustomerRiskTier.HIGH
        elif score >= 31:
            tier = CustomerRiskTier.MEDIUM
        else:
            tier = CustomerRiskTier.LOW

        profile.risk_score = score
        profile.risk_tier = tier
        profile.risk_factors = factors
        profile.total_transaction_volume = new_total_vol
        profile.lifetime_aml_alerts_count = total_alerts
        profile.updated_at = datetime.now(timezone.utc)

        return profile

