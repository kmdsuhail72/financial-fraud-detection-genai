"""
FinGuard AI — Phase 29: Payment Risk Assessment & Intelligence Engine.
Evaluates payment transactions against rules: velocity, high-value, geographic mismatch,
new beneficiaries, international status, and device intelligence.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from payment_fraud.models import (
    AlertAction,
    PaymentAssessmentResponse,
    PaymentEvent,
    PaymentRiskSignal,
    RiskLevel,
)

HIGH_VALUE_THRESHOLD = 200000.0  # ₹2,00,000 threshold


def evaluate_payment_risk(
    payment: PaymentEvent,
    recent_10m_txn_count: int = 0
) -> PaymentAssessmentResponse:
    """
    Evaluates a payment event against rules and produces an explainable assessment score (0-100).
    Points breakdown:
    - High-value payment (>= ₹2,00,000): 20 points
    - New beneficiary: 15 points
    - City mismatch: 10 points
    - Rolling 10-minute velocity (>= 3 prior txns): 25 points
    - International payment: 20 points
    - Missing device context: 15 points
    """
    signals: List[PaymentRiskSignal] = []

    # 1. High-value detection
    if payment.amount >= HIGH_VALUE_THRESHOLD:
        signals.append(
            PaymentRiskSignal(
                signal_name="High-value payment",
                points=20,
                category="Amount",
                description=f"Transaction amount ₹{payment.amount:,.2f} exceeds high-value threshold of ₹{HIGH_VALUE_THRESHOLD:,.2f}",
            )
        )

    # 2. New beneficiary detection
    if payment.is_new_beneficiary:
        signals.append(
            PaymentRiskSignal(
                signal_name="New beneficiary",
                points=15,
                category="Payee",
                description=f"First-time transfer to beneficiary '{payment.beneficiary_name or payment.beneficiary_account}'",
            )
        )

    # 3. Geographic intelligence (Customer home city vs transaction city)
    if payment.customer_home_city and payment.transaction_city:
        home = payment.customer_home_city.strip().lower()
        txn_loc = payment.transaction_city.strip().lower()
        if home != txn_loc:
            signals.append(
                PaymentRiskSignal(
                    signal_name="City mismatch",
                    points=10,
                    category="Geography",
                    description=f"Home city '{payment.customer_home_city}' differs from transaction city '{payment.transaction_city}'",
                )
            )

    # 4. Velocity detection (rolling 10-minute window)
    if recent_10m_txn_count >= 3:
        signals.append(
            PaymentRiskSignal(
                signal_name="Velocity anomaly",
                points=25,
                category="Velocity",
                description=f"Detected {recent_10m_txn_count} transactions in the rolling 10-minute window",
            )
        )

    # 5. International cross-border payment
    if payment.is_international or (payment.currency and payment.currency.upper() != "INR"):
        signals.append(
            PaymentRiskSignal(
                signal_name="International payment",
                points=20,
                category="CrossBorder",
                description=f"Cross-border payment flag set or non-domestic currency '{payment.currency}'",
            )
        )

    # 6. Device context intelligence
    if not payment.device_context or not payment.device_context.device_id:
        signals.append(
            PaymentRiskSignal(
                signal_name="Missing device context",
                points=15,
                category="Device",
                description="Transaction lacks authenticated device fingerprint or hardware context",
            )
        )

    # Calculate total points
    raw_points = sum(s.points for s in signals)
    final_score = min(100, max(0, raw_points))

    # Alert prioritization & classification
    if final_score < 30:
        risk_level = RiskLevel.LOW
        action = AlertAction.MONITOR
    elif final_score < 70:
        risk_level = RiskLevel.MEDIUM
        action = AlertAction.REVIEW
    else:
        risk_level = RiskLevel.HIGH
        action = AlertAction.PRIORITY_REVIEW

    summary = (
        f"Payment of {payment.currency} {payment.amount:,.2f} via {payment.payment_rail.value} "
        f"scored {final_score}/100 ({risk_level.value}) triggering action '{action.value}' "
        f"across {len(signals)} risk signal(s)."
    )

    assessment_id = f"PA-{uuid.uuid4().hex[:10].upper()}"

    return PaymentAssessmentResponse(
        assessment_id=assessment_id,
        transaction_id=payment.transaction_id,
        customer_id=payment.customer_id,
        amount=payment.amount,
        currency=payment.currency,
        payment_rail=payment.payment_rail,
        risk_score=final_score,
        risk_level=risk_level,
        action=action,
        signals=signals,
        summary=summary,
        assessed_at=datetime.now(timezone.utc),
    )

