"""
FinGuard AI — Service Level Objectives (SLO) & Error Budget Engine
Tracks service compliance, computes error budget consumption, burn rates,
and percentile latencies.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional
from observability.models import SLODefinition, SLOStatus


class SLOMonitor:
    """Manages FinGuard Service Level Objectives and Error Budgets."""

    def __init__(self) -> None:
        self._definitions: Dict[str, SLODefinition] = {}
        self._init_default_slos()

    def _init_default_slos(self) -> None:
        defaults = [
            SLODefinition(
                id="slo-avail-core",
                name="FinGuard Core API Availability",
                service="finguard-gateway",
                target_percentage=99.9,
                time_window_days=30,
                metric_type="availability",
                description="99.9% of non-4xx API requests succeed without 5xx errors over a 30-day rolling window.",
            ),
            SLODefinition(
                id="slo-lat-scoring",
                name="Fraud Scoring Latency p95",
                service="fraud-scoring-service",
                target_percentage=99.5,
                time_window_days=30,
                metric_type="latency",
                threshold_value=200.0,  # 200 ms target
                description="99.5% of real-time fraud scoring requests return inferences in under 200ms.",
            ),
            SLODefinition(
                id="slo-avail-txn",
                name="Transaction Ingestion Availability",
                service="transaction-service",
                target_percentage=99.95,
                time_window_days=30,
                metric_type="availability",
                description="99.95% of incoming payment and transaction events are ingested without packet drops.",
            ),
        ]
        for d in defaults:
            self._definitions[d.id] = d

    def register_slo(self, slo: SLODefinition) -> None:
        self._definitions[slo.id] = slo

    def list_slos(self) -> List[SLODefinition]:
        return list(self._definitions.values())

    def evaluate_slo(
        self,
        slo_id: str,
        total_requests: int = 150000,
        bad_requests: int = 42,
        simulated_latencies: Optional[List[float]] = None,
    ) -> Optional[SLOStatus]:
        """Calculates SLO status, remaining error budget, and burn rates."""
        definition = self._definitions.get(slo_id)
        if not definition:
            return None

        current_percentage = round(((total_requests - bad_requests) / max(total_requests, 1)) * 100.0, 3)
        target = definition.target_percentage
        budget_total_percentage = round(100.0 - target, 3)

        allowed_bad_requests = max(int(total_requests * (budget_total_percentage / 100.0)), 1)
        consumed_percentage = round((bad_requests / allowed_bad_requests) * 100.0, 2)
        remaining_percentage = round(max(100.0 - consumed_percentage, 0.0), 2)

        # Burn rates (1.0x means consuming budget exactly at target rate over 30 days)
        burn_rate_1h = round(consumed_percentage / 100.0 * (30 * 24 / 720.0), 2)
        burn_rate_6h = round(burn_rate_1h * 0.95, 2)

        status_str = "MET"
        if remaining_percentage <= 0:
            status_str = "BREACHED"
        elif remaining_percentage < 25.0 or burn_rate_1h > 5.0:
            status_str = "AT_RISK"

        # Latency calculations
        lats = simulated_latencies or [random.uniform(15.0, 85.0) for _ in range(200)]
        lats_sorted = sorted(lats)
        n = len(lats_sorted)

        p50 = round(lats_sorted[int(n * 0.50)], 2)
        p90 = round(lats_sorted[int(n * 0.90)], 2)
        p95 = round(lats_sorted[int(n * 0.95)], 2)
        p99 = round(lats_sorted[int(n * 0.99)], 2)

        return SLOStatus(
            slo_id=definition.id,
            name=definition.name,
            service=definition.service,
            target_percentage=target,
            current_percentage=current_percentage,
            status=status_str,
            error_budget_total_percentage=budget_total_percentage,
            error_budget_consumed_percentage=consumed_percentage,
            error_budget_remaining_percentage=remaining_percentage,
            burn_rate_1h=burn_rate_1h,
            burn_rate_6h=burn_rate_6h,
            total_requests=total_requests,
            bad_requests=bad_requests,
            p50_latency_ms=p50,
            p90_latency_ms=p90,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
        )

    def evaluate_all(self) -> List[SLOStatus]:
        """Evaluates all registered SLOs."""
        statuses = []
        for slo_id in self._definitions:
            status = self.evaluate_slo(slo_id)
            if status:
                statuses.append(status)
        return statuses


# Global singleton SLO monitor
slo_monitor = SLOMonitor()
