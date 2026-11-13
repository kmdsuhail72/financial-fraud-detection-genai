"""Explainable IOC Risk and Confidence Scoring Engine for FinGuard AI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple
from threat_intel.models import (
    AnalystFeedback,
    AnalystVerdict,
    IOCRecord,
    IOCSeverity,
    IOCStatus,
)


class IOCRiskEngine:
    """Calculates explainable risk scores, confidence levels, and lifecycle status for indicators."""

    @classmethod
    def evaluate_risk(
        cls,
        base_reputation: float,
        base_confidence: float,
        threat_types: List[str],
        source_feeds: List[str],
        analyst_verdicts: List[AnalystFeedback],
        expires_at: datetime | None = None,
    ) -> Tuple[float, float, IOCSeverity, IOCStatus, List[str]]:
        """
        Evaluates composite risk score (0-100), confidence (0.0-1.0), severity, and status.

        Returns:
            Tuple of (final_reputation_score, final_confidence, severity, status, explanations)
        """
        explanations: List[str] = []
        score = base_reputation
        confidence = base_confidence

        explanations.append(f"Base provider reputation score: {base_reputation:.1f}/100 with confidence {base_confidence:.2f}")

        # Multiple source feeds boost confidence
        if len(source_feeds) > 1:
            confidence = min(1.0, confidence + 0.05 * (len(source_feeds) - 1))
            explanations.append(f"Corroborated across {len(source_feeds)} distinct threat feeds (+confidence)")

        # Severe threat categories carry severity weight
        high_threats = {"c2", "ransomware", "credential_theft", "botnet"}
        if any(t.lower() in high_threats for t in threat_types):
            score = min(100.0, score + 10.0)
            explanations.append(f"Elevated risk due to critical threat categories: {', '.join(threat_types)}")

        # Analyst Feedback overrides and calibrations
        status = IOCStatus.ACTIVE
        if analyst_verdicts:
            latest = analyst_verdicts[-1]
            if latest.verdict == AnalystVerdict.FALSE_POSITIVE:
                score = 0.0
                confidence = 1.0
                status = IOCStatus.REVOKED
                explanations.append(f"Overridden by human analyst ({latest.analyst_id}): Marked as FALSE_POSITIVE. Risk neutralized.")
            elif latest.verdict == AnalystVerdict.BENIGN:
                score = max(0.0, score * 0.1)
                status = IOCStatus.REVOKED
                explanations.append(f"Analyst ({latest.analyst_id}) adjudicated indicator as BENIGN.")
            elif latest.verdict == AnalystVerdict.TRUE_POSITIVE:
                score = min(100.0, max(85.0, score + 15.0))
                confidence = 1.0
                status = IOCStatus.ACTIVE
                explanations.append(f"Analyst confirmed TRUE_POSITIVE ({latest.analyst_id}). Maximum confidence applied.")
            elif latest.verdict == AnalystVerdict.SUSPICIOUS:
                score = min(100.0, score + 10.0)
                status = IOCStatus.UNDER_REVIEW
                explanations.append(f"Analyst flagged as SUSPICIOUS under review.")

        # Check expiration
        now = datetime.now(timezone.utc)
        if expires_at and expires_at < now and status != IOCStatus.REVOKED:
            status = IOCStatus.EXPIRED
            score = score * 0.5
            explanations.append(f"Indicator expired on {expires_at.isoformat()}. Score damped by 50%.")

        score = round(max(0.0, min(100.0, score)), 2)
        confidence = round(max(0.0, min(1.0, confidence)), 2)

        # Map to severity
        if score >= 85.0:
            severity = IOCSeverity.CRITICAL
        elif score >= 65.0:
            severity = IOCSeverity.HIGH
        elif score >= 40.0:
            severity = IOCSeverity.MEDIUM
        elif score >= 15.0:
            severity = IOCSeverity.LOW
        else:
            severity = IOCSeverity.INFO

        return score, confidence, severity, status, explanations

