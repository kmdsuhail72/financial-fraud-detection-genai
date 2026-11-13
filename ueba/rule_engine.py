"""Deterministic Heuristic Rule Engine for UEBA Behavioral Red Flags."""

from __future__ import annotations

from typing import List, Tuple
from ueba.models import BehavioralFeatures


class UEBARuleEngine:
    """Evaluates rule-based behavioral violation heuristics on point-in-time features."""

    @classmethod
    def evaluate_rules_with_explanations(cls, features: BehavioralFeatures) -> Tuple[List[str], List[str]]:
        """
        Evaluates rule violations.

        Returns:
            Tuple of (triggered_rule_keys, human_readable_explanations)
        """
        rule_flags: List[str] = []
        explanations: List[str] = []

        # 1. Amount Spike
        if features.amount_deviation_ratio >= 4.0 or features.amount_z_score >= 3.0:
            rule_flags.append("UNUSUAL_AMOUNT_SPIKE")
            explanations.append(
                f"Amount is {features.amount_deviation_ratio:.1f}x higher than entity baseline (Z-score: {features.amount_z_score:+.1f})."
            )

        # 2. Off-Hours Activity with Elevated Value
        if features.is_off_hours and features.amount_deviation_ratio >= 1.5:
            rule_flags.append("OFF_HOURS_ELEVATED_VALUE")
            explanations.append("Transaction initiated during anomalous entity off-hours with above-average value.")

        # 3. New Device Burst
        if features.is_new_device and features.velocity_1h >= 2:
            rule_flags.append("NEW_DEVICE_BURST")
            explanations.append(f"Unrecognized device fingerprint executing rapid transactions ({features.velocity_1h} within 1h).")

        # 4. Impossible Travel / Location Mismatch
        if features.impossible_travel_flag:
            rule_flags.append("IMPOSSIBLE_TRAVEL_VELOCITY")
            explanations.append("Activity observed from a new city in rapid succession to prior transactions.")

        # 5. New IP Network Access
        if features.is_new_ip and features.is_off_hours:
            rule_flags.append("UNRECOGNIZED_IP_OFF_HOURS")
            explanations.append("Access from an unrecognized IP address during anomalous activity hours.")

        return rule_flags, explanations

    @classmethod
    def evaluate_rules(cls, features: BehavioralFeatures) -> List[str]:
        """Evaluates rule violations and returns list of rule flag keys."""
        flags, _ = cls.evaluate_rules_with_explanations(features)
        return flags
