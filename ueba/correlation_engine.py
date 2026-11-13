"""Fraud-Threat Correlation Engine uniting UEBA, ML Fraud, Threat Intel, and Security Findings."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union

from ueba.models import CorrelateRiskRequest, EntityRiskLevel, FraudThreatCorrelation


class FraudThreatCorrelationEngine:
    """Correlates behavioral anomalies with real-time ML fraud scores, IOC reputation, and cloud alerts."""

    @classmethod
    def correlate(
        cls,
        entity_id: Union[CorrelateRiskRequest, str],
        event_id: Optional[str] = None,
        ueba_anomaly_score: Optional[float] = None,
        fraud_probability: float = 0.0,
        ioc_reputation_score: float = 0.0,
        security_finding_severity: float = 0.0,
        **kwargs,
    ) -> FraudThreatCorrelation:
        """
        Blends multi-domain security and fraud signals into an actionable entity risk dossier.
        """
        if isinstance(entity_id, CorrelateRiskRequest):
            req = entity_id
            actual_entity_id = req.entity_id
            actual_event_id = req.event_id
            s_raw_ueba = req.ueba_anomaly_score
            s_raw_fraud = req.fraud_probability
            s_raw_ioc = req.ioc_reputation_score
            s_raw_sec = req.security_finding_severity
        else:
            actual_entity_id = str(entity_id)
            actual_event_id = event_id or "unknown-event"
            s_raw_ueba = ueba_anomaly_score if ueba_anomaly_score is not None else 0.0
            s_raw_fraud = fraud_probability
            s_raw_ioc = ioc_reputation_score
            s_raw_sec = security_finding_severity

        # Normalize all signals to [0.0, 1.0] scale
        s_ueba = min(1.0, max(0.0, s_raw_ueba))
        s_fraud = min(1.0, max(0.0, s_raw_fraud))
        s_ioc = min(1.0, max(0.0, s_raw_ioc / 100.0))
        s_sec = min(1.0, max(0.0, s_raw_sec / 10.0))

        signals: List[str] = []
        recommendations: List[str] = []

        if s_ueba >= 0.65:
            signals.append(f"High behavioral anomaly deviation ({s_ueba:.2f})")
        if s_fraud >= 0.70:
            signals.append(f"Elevated ML fraud probability ({s_fraud:.2f})")
        if s_ioc >= 0.50:
            signals.append(f"Threat intelligence IOC match (Reputation: {s_raw_ioc:.1f}/100)")
        if s_sec >= 0.60:
            signals.append(f"Concurrent cloud security finding (Severity: {s_raw_sec:.1f}/10)")

        # Blended formulation: emphasizes peak threat without dilution
        max_threat = max(s_ueba, s_fraud, s_ioc, s_sec)
        weighted_avg = 0.35 * s_ueba + 0.35 * s_fraud + 0.15 * s_ioc + 0.15 * s_sec
        blended_ratio = min(1.0, 0.60 * max_threat + 0.40 * weighted_avg)
        blended_score = round(blended_ratio * 100.0, 2)

        # Risk Classification & Recommendations
        if blended_score >= 80.0:
            level = EntityRiskLevel.CRITICAL
            recommendations.append("Immediate Account Hold: Suspend automated fund dispersal pending voice verification.")
            recommendations.append("Session Invalidation: Revoke active session tokens and force MFA re-authentication.")
            recommendations.append("Cross-Domain Escalation: Correlate concurrent IAM and IP activity with Threat Intel.")
        elif blended_score >= 60.0:
            level = EntityRiskLevel.HIGH
            recommendations.append("Step-Up Authentication: Enforce hardware token or biometric verification.")
            recommendations.append("Review Velocity Burst: Route to senior fraud analyst queue with high priority.")
        elif blended_score >= 35.0:
            level = EntityRiskLevel.MEDIUM
            recommendations.append("Monitor Baseline: Observe entity activity over the subsequent 48-hour window.")
        else:
            level = EntityRiskLevel.LOW
            recommendations.append("Standard Processing: Maintain normal automated transaction routing.")

        if not signals:
            signals.append("Standard baseline activity within nominal operational parameters.")

        corr_id = f"corr-{uuid.uuid4().hex[:10]}"

        return FraudThreatCorrelation(
            correlation_id=corr_id,
            entity_id=actual_entity_id,
            event_id=actual_event_id,
            ueba_anomaly_score=round(s_ueba, 4),
            fraud_probability=round(s_fraud, 4),
            ioc_reputation_score=round(s_raw_ioc, 2),
            security_finding_severity=round(s_raw_sec, 2),
            blended_risk_score=blended_score,
            risk_level=level,
            correlated_signals=signals,
            investigation_recommendations=recommendations,
            timestamp=datetime.now(timezone.utc),
        )
