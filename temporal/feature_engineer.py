"""Rolling, As-Of Temporal Feature Engineer (Causality Enforcing, No Lookahead Leakage)."""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from temporal.models import TemporalEntityFeatures, TemporalTransactionEvent
from temporal.temporal_graph import TemporalGraph


class TemporalFeatureEngineer:
    """Computes rolling multi-window velocity, burst, and deviation features strictly as-of timestamp."""

    def __init__(self, graph: TemporalGraph):
        self.graph = graph

    def compute_features(
        self,
        entity_id: str,
        as_of_timestamp: float,
        current_event: Optional[TemporalTransactionEvent] = None,
    ) -> TemporalEntityFeatures:
        """
        Calculates 5-minute, 1-hour, and 24-hour rolling velocity and amounts as-of `as_of_timestamp`.
        """
        # Fetch historical events strictly <= as_of_timestamp (within 24 hours / 86400 seconds)
        hist = self.graph.get_entity_events(
            entity_id=entity_id,
            as_of=as_of_timestamp,
            window_seconds=86400.0,
            limit=200,
        )

        # Include current event if provided and not already in hist
        all_events = list(hist)
        if current_event and not any(e.transaction_id == current_event.transaction_id for e in all_events):
            all_events.append(current_event)

        all_events.sort(key=lambda e: e.timestamp)

        # Sliding window counts
        t_5m = as_of_timestamp - 300.0
        t_1h = as_of_timestamp - 3600.0
        t_24h = as_of_timestamp - 86400.0

        ev_5m = [e for e in all_events if e.timestamp >= t_5m]
        ev_1h = [e for e in all_events if e.timestamp >= t_1h]
        ev_24h = [e for e in all_events if e.timestamp >= t_24h]

        tx_count_5m = len(ev_5m)
        tx_count_1h = len(ev_1h)
        tx_count_24h = len(ev_24h)

        amount_sum_1h = sum(e.amount for e in ev_1h)

        amounts_24h = [e.amount for e in ev_24h]
        amount_avg_24h = float(np.mean(amounts_24h)) if amounts_24h else 0.0
        amount_std_24h = float(np.std(amounts_24h)) if len(amounts_24h) > 1 else 0.0

        # Burst ratio: 5m frequency projected to 1h rate vs actual 1h frequency
        velocity_burst_ratio = (tx_count_5m * 12.0) / (tx_count_1h + 1.0)

        counterparties_1h = {e.target_account for e in ev_1h if e.target_account}
        distinct_counterparties_1h = len(counterparties_1h)

        devices_24h = {e.device_id for e in ev_24h if e.device_id}
        distinct_devices_24h = len(devices_24h)

        ips_24h = {e.ip_address for e in ev_24h if e.ip_address}
        distinct_ips_24h = len(ips_24h)

        # New device / IP relative to prior history
        is_new_device = False
        is_new_ip = False
        if current_event:
            is_new_device = self.graph.is_new_device_for_entity(entity_id, current_event.device_id)
            is_new_ip = self.graph.is_new_ip_for_entity(entity_id, current_event.ip_address)

        # Time elapsed since prior transaction
        time_since_prior = 86400.0
        if len(all_events) >= 2:
            time_since_prior = max(0.1, all_events[-1].timestamp - all_events[-2].timestamp)

        return TemporalEntityFeatures(
            entity_id=entity_id,
            as_of_timestamp=as_of_timestamp,
            tx_count_5m=tx_count_5m,
            tx_count_1h=tx_count_1h,
            tx_count_24h=tx_count_24h,
            amount_sum_1h=round(amount_sum_1h, 2),
            amount_avg_24h=round(amount_avg_24h, 2),
            amount_std_24h=round(amount_std_24h, 2),
            velocity_burst_ratio=round(velocity_burst_ratio, 2),
            distinct_counterparties_1h=distinct_counterparties_1h,
            distinct_devices_24h=distinct_devices_24h,
            distinct_ips_24h=distinct_ips_24h,
            is_new_device=is_new_device,
            is_new_ip=is_new_ip,
            time_since_prior_tx_sec=round(time_since_prior, 2),
        )

