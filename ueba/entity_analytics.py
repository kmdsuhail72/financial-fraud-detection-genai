"""High-level entity behavioral analytics and aggregate metrics."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from collections import Counter

from ueba.correlation_engine import FraudThreatCorrelationEngine
from ueba.feature_engineer import UEBAFeatureEngineer
from ueba.ml_engine import IsolationForestAnomalyDetector
from ueba.models import (
    BehavioralAnomalyResult,
    CorrelateRiskRequest,
    EntityRiskLevel,
    FraudThreatCorrelation,
    PeerGroup,
    ScoreEventRequest,
    UserEntityProfile,
)
from ueba.profile_store import ProfileStore, get_profile_store
from ueba.rule_engine import UEBARuleEngine


class UEBAEntityAnalytics:
    """Manages UEBA lifecycle: feature extraction, anomaly scoring, correlation, and aggregated posture."""

    def __init__(
        self,
        profile_store: Optional[ProfileStore] = None,
        detector: Optional[IsolationForestAnomalyDetector] = None,
    ):
        self.profile_store = profile_store or get_profile_store()
        self.detector = detector or IsolationForestAnomalyDetector()
        self.feature_engineer = UEBAFeatureEngineer()
        self.rule_engine = UEBARuleEngine()
        self.correlation_engine = FraudThreatCorrelationEngine()

    def get_overview_metrics(self) -> Dict[str, Any]:
        """Calculates macro metrics across all tracked behavioral entities."""
        profiles = self.profile_store.list_profiles(limit=1000)
        total = len(profiles)
        if total == 0:
            return {
                "total_entities": 0,
                "critical_risk_count": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "avg_risk_score": 0.0,
                "peer_group_counts": {},
                "top_anomalies": {},
            }

        risk_counts = Counter(p.risk_level.value for p in profiles)
        peer_counts = Counter(p.peer_group.value for p in profiles)
        all_anomalies: List[str] = []
        for p in profiles:
            all_anomalies.extend(p.active_anomalies)
        anomaly_counts = dict(Counter(all_anomalies).most_common(8))

        avg_risk = sum(p.current_risk_score for p in profiles) / total

        return {
            "total_entities": total,
            "critical_risk_count": risk_counts.get(EntityRiskLevel.CRITICAL.value, 0),
            "high_risk_count": risk_counts.get(EntityRiskLevel.HIGH.value, 0),
            "medium_risk_count": risk_counts.get(EntityRiskLevel.MEDIUM.value, 0),
            "low_risk_count": risk_counts.get(EntityRiskLevel.LOW.value, 0),
            "avg_risk_score": round(avg_risk, 1),
            "peer_group_counts": dict(peer_counts),
            "top_anomalies": anomaly_counts,
        }

    def score_event(self, request: ScoreEventRequest) -> BehavioralAnomalyResult:
        """Calculates point-in-time features, triggers behavioral rules, and ML anomaly scores."""
        profile = self.profile_store.get_profile(request.entity_id)
        if not profile:
            from ueba.models import BehavioralBaseline
            # Generate default fallback baseline
            baseline = BehavioralBaseline(
                avg_amount=150.0,
                std_amount=80.0,
                max_amount_historical=1000.0,
                active_hours=[8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
                known_devices=[request.device_id] if request.device_id else ["dev_default"],
                known_ips=[request.ip_address] if request.ip_address else ["127.0.0.1"],
                known_cities=[request.city] if request.city else ["Unknown"],
            )
            profile = UserEntityProfile(
                entity_id=request.entity_id,
                baseline=baseline,
                peer_group=PeerGroup.RETAIL,
            )
            self.profile_store.save_profile(profile)

        features = self.feature_engineer.extract_features(request, profile.baseline)
        rule_flags = self.rule_engine.evaluate_rules(features)
        anomaly_score = self.detector.score_sample(features)
        is_anomaly = anomaly_score >= 0.65 or len(rule_flags) > 0

        explanation_parts = []
        if rule_flags:
            explanation_parts.append(f"Triggered behavioral rules: {', '.join(rule_flags)}")
        if anomaly_score >= 0.65:
            explanation_parts.append(f"ML Isolation Forest detected high deviation (score: {anomaly_score:.2f})")
        if not explanation_parts:
            explanation_parts.append("Transaction conforms to expected baseline behavior.")

        result = BehavioralAnomalyResult(
            anomaly_id=f"ANOM-{request.event_id[-8:]}",
            entity_id=request.entity_id,
            event_id=request.event_id,
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly,
            rule_flags=rule_flags,
            features=features,
            explanation="; ".join(explanation_parts),
        )

        # Update entity profile active anomalies and score
        if is_anomaly:
            existing = set(profile.active_anomalies)
            for rf in rule_flags:
                existing.add(rf)
            profile.active_anomalies = list(existing)
            # Adjust risk score upward
            profile.current_risk_score = min(100.0, profile.current_risk_score + anomaly_score * 25.0)
            if profile.current_risk_score >= 80.0:
                profile.risk_level = EntityRiskLevel.CRITICAL
            elif profile.current_risk_score >= 60.0:
                profile.risk_level = EntityRiskLevel.HIGH
            elif profile.current_risk_score >= 35.0:
                profile.risk_level = EntityRiskLevel.MEDIUM
            self.profile_store.save_profile(profile)

        return result

    def correlate_event(self, request: CorrelateRiskRequest) -> FraudThreatCorrelation:
        """Blends UEBA with fraud probability, IOC score, and cloud findings."""
        correlation = self.correlation_engine.correlate(request)

        # Update entity profile with blended risk
        profile = self.profile_store.get_profile(request.entity_id)
        if profile:
            profile.current_risk_score = correlation.blended_risk_score
            profile.risk_level = correlation.risk_level
            self.profile_store.save_profile(profile)

        return correlation
