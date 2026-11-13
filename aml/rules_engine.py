"""
FinGuard AI — Phase 24 Anti-Money Laundering (AML) Rules Engine.
Evaluates transactions for Large Cash, Structuring, Rapid Inflow/Outflow, and High Velocity patterns.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from aml.models import (
    AMLAlert,
    AMLRuleType,
    AMLTransaction,
    CustomerRiskProfile,
    TransactionDirection,
)


class AMLRulesEngine:
    """Explainable transaction-monitoring rules engine for AML and suspicious activity detection."""

    def evaluate_transaction(
        self,
        current_txn: AMLTransaction,
        customer_history: List[AMLTransaction],
        profile: CustomerRiskProfile,
    ) -> List[AMLAlert]:
        alerts: List[AMLAlert] = []

        # ---------------------------------------------------------
        # Rule 1: Large Cash / High-Value Transaction (>= $10,000)
        # ---------------------------------------------------------
        if current_txn.amount >= 10000.0:
            alerts.append(
                AMLAlert(
                    rule_type=AMLRuleType.LARGE_CASH_TRANSACTION,
                    severity="CRITICAL" if current_txn.amount >= 50000.0 else "HIGH",
                    description=(
                        f"Large financial transaction of ${current_txn.amount:,.2f} {current_txn.currency} "
                        f"exceeds the statutory $10,000 reporting threshold (FinCEN CTR / AML Rule)."
                    ),
                    trigger_amount=current_txn.amount,
                    trigger_transaction_ids=[current_txn.transaction_id],
                )
            )

        # ---------------------------------------------------------
        # Rule 2: Possible Structuring / Smurfing ($8,500 - $9,999)
        # ---------------------------------------------------------
        if 8500.0 <= current_txn.amount < 10000.0:
            # Check if previous transactions within 24h were also near threshold
            recent_threshold_txns = [
                t for t in customer_history
                if 8500.0 <= t.amount < 10000.0
                and abs((current_txn.timestamp - t.timestamp).total_seconds()) <= 86400
            ]
            if len(recent_threshold_txns) >= 1:
                trigger_ids = [t.transaction_id for t in recent_threshold_txns] + [current_txn.transaction_id]
                total_structured_amount = current_txn.amount + sum(t.amount for t in recent_threshold_txns)
                alerts.append(
                    AMLAlert(
                        rule_type=AMLRuleType.POSSIBLE_STRUCTURING,
                        severity="CRITICAL",
                        description=(
                            f"Suspected structuring pattern detected: {len(trigger_ids)} transactions just below "
                            f"$10,000 CTR reporting threshold (Total: ${total_structured_amount:,.2f})."
                        ),
                        trigger_amount=total_structured_amount,
                        trigger_transaction_ids=trigger_ids,
                    )
                )

        # ---------------------------------------------------------
        # Rule 3: Rapid Inflow / Outflow (Layering / Pass-Through)
        # ---------------------------------------------------------
        if current_txn.direction == TransactionDirection.OUTFLOW and current_txn.amount >= 4000.0:
            # Check recent inflows in last 1 hour
            recent_inflows = [
                t for t in customer_history
                if t.direction == TransactionDirection.INFLOW
                and t.amount >= 4000.0
                and 0 <= (current_txn.timestamp - t.timestamp).total_seconds() <= 3600
            ]
            for inflow in recent_inflows:
                drain_ratio = current_txn.amount / inflow.amount
                if 0.80 <= drain_ratio <= 1.20:
                    alerts.append(
                        AMLAlert(
                            rule_type=AMLRuleType.RAPID_INFLOW_OUTFLOW,
                            severity="HIGH",
                            description=(
                                f"Rapid pass-through layering observed: ${inflow.amount:,.2f} inflow on {inflow.timestamp.strftime('%H:%M')} "
                                f"was followed by immediate ${current_txn.amount:,.2f} outflow ({drain_ratio * 100:.1f}% drain) within 1 hour."
                            ),
                            trigger_amount=current_txn.amount,
                            trigger_transaction_ids=[inflow.transaction_id, current_txn.transaction_id],
                        )
                    )
                    break

        # ---------------------------------------------------------
        # Rule 4: High Velocity Burst (>= 5 transactions in 10 mins)
        # ---------------------------------------------------------
        burst_txns = [
            t for t in customer_history
            if abs((current_txn.timestamp - t.timestamp).total_seconds()) <= 600
        ]
        if len(burst_txns) >= 4:  # 4 previous + 1 current = 5 total
            trigger_ids = [t.transaction_id for t in burst_txns] + [current_txn.transaction_id]
            burst_volume = current_txn.amount + sum(t.amount for t in burst_txns)
            alerts.append(
                AMLAlert(
                    rule_type=AMLRuleType.HIGH_VELOCITY,
                    severity="HIGH",
                    description=(
                        f"High velocity anomaly: {len(trigger_ids)} transactions executed within a 10-minute window "
                        f"(Cumulative Volume: ${burst_volume:,.2f})."
                    ),
                    trigger_amount=burst_volume,
                    trigger_transaction_ids=trigger_ids,
                )
            )

        return alerts

