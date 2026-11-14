"""
FinGuard AI — Performance Analytics & Latency Percentiles Engine
Computes p50, p90, p95, p99, average latency, and throughput from benchmark runs.
"""
from __future__ import annotations

from typing import List
from performance.models import BenchmarkSummary


def compute_benchmark_analytics(
    target_url: str,
    latencies_ms: List[float],
    total_duration_sec: float,
    failed_requests: int = 0,
) -> BenchmarkSummary:
    """Computes full latency distribution percentiles and throughput."""
    total_requests = len(latencies_ms) + failed_requests
    successful_requests = len(latencies_ms)

    if not latencies_ms:
        return BenchmarkSummary(
            target_url=target_url,
            total_requests=total_requests,
            successful_requests=0,
            failed_requests=failed_requests,
            error_rate_pct=100.0 if total_requests > 0 else 0.0,
            total_duration_sec=total_duration_sec,
            throughput_rps=0.0,
            avg_latency_ms=0.0,
            min_latency_ms=0.0,
            max_latency_ms=0.0,
            p50_latency_ms=0.0,
            p90_latency_ms=0.0,
            p95_latency_ms=0.0,
            p99_latency_ms=0.0,
        )

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)

    p50 = sorted_lats[int(n * 0.50)]
    p90 = sorted_lats[min(int(n * 0.90), n - 1)]
    p95 = sorted_lats[min(int(n * 0.95), n - 1)]
    p99 = sorted_lats[min(int(n * 0.99), n - 1)]

    avg_lat = sum(sorted_lats) / n
    min_lat = sorted_lats[0]
    max_lat = sorted_lats[-1]

    throughput = round(total_requests / max(total_duration_sec, 0.001), 2)
    error_rate = round((failed_requests / max(total_requests, 1)) * 100.0, 2)

    return BenchmarkSummary(
        target_url=target_url,
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        error_rate_pct=error_rate,
        total_duration_sec=round(total_duration_sec, 3),
        throughput_rps=throughput,
        avg_latency_ms=round(avg_lat, 2),
        min_latency_ms=round(min_lat, 2),
        max_latency_ms=round(max_lat, 2),
        p50_latency_ms=round(p50, 2),
        p90_latency_ms=round(p90, 2),
        p95_latency_ms=round(p95, 2),
        p99_latency_ms=round(p99, 2),
    )
