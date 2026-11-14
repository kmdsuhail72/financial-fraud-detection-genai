"""
FinGuard AI — Performance Capacity Planning Calculator
Estimates required Kubernetes pod replicas and cluster capacity based on
expected peak RPS, target utilization, and traffic spike headroom.
"""
from __future__ import annotations

import math
from performance.models import CapacityEstimate, CapacityRequest


def calculate_capacity(
    peak_rps: float = 100.0,
    pod_capacity_rps: float = 25.0,
    target_utilization_pct: float = 65.0,
    headroom_pct: float = 30.0,
) -> CapacityEstimate:
    """
    Computes required pod replicas using industry-standard SRE capacity equations:
    1. Effective per-pod capacity = pod_capacity_rps * (target_utilization_pct / 100)
    2. Peak traffic with headroom = peak_rps * (1 + headroom_pct / 100)
    3. Recommended replicas = ceil(traffic_with_headroom / effective_pod_capacity)
    """
    eff_pod_capacity = pod_capacity_rps * (target_utilization_pct / 100.0)
    traffic_with_headroom = peak_rps * (1.0 + (headroom_pct / 100.0))
    base_replicas = max(1, math.ceil(peak_rps / pod_capacity_rps))
    recommended_replicas = max(1, math.ceil(traffic_with_headroom / max(eff_pod_capacity, 0.001)))

    total_cluster_capacity = recommended_replicas * pod_capacity_rps
    safety_buffer = round(total_cluster_capacity - peak_rps, 2)

    explanation = (
        f"For {peak_rps:.1f} RPS peak traffic with {headroom_pct:.0f}% headroom ({traffic_with_headroom:.1f} RPS total), "
        f"and {pod_capacity_rps:.1f} RPS capacity per pod at {target_utilization_pct:.0f}% target utilization "
        f"({eff_pod_capacity:.2f} effective RPS/pod), exactly {recommended_replicas} pod replicas are recommended."
    )

    return CapacityEstimate(
        peak_rps=peak_rps,
        pod_capacity_rps=pod_capacity_rps,
        target_utilization_pct=target_utilization_pct,
        headroom_pct=headroom_pct,
        effective_pod_capacity_rps=round(eff_pod_capacity, 2),
        traffic_with_headroom_rps=round(traffic_with_headroom, 2),
        base_replicas=base_replicas,
        recommended_replicas=recommended_replicas,
        total_cluster_capacity_rps=round(total_cluster_capacity, 2),
        safety_buffer_rps=safety_buffer,
        formula_explanation=explanation,
    )

