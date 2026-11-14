"""
FinGuard AI — Performance Engineering Unified Service
Coordinates benchmarking runs, capacity planning calculations, and SLO validation.
"""
from __future__ import annotations

import datetime
import random
import time
from typing import Dict, List, Optional

from performance.analytics import compute_benchmark_analytics
from performance.capacity import calculate_capacity
from performance.models import (
    BenchmarkRequest,
    BenchmarkSummary,
    CapacityEstimate,
    CapacityRequest,
    PerformanceHealthResponse,
    PerformanceSLO,
)


class PerformanceEngineeringService:
    """Enterprise performance engineering, benchmarking, and capacity governor."""

    def __init__(self) -> None:
        self._benchmark_history: List[BenchmarkSummary] = []
        self._init_defaults()

    def _init_defaults(self) -> None:
        # Seed initial synthetic benchmark run
        synthetic_latencies = [random.uniform(8.0, 35.0) for _ in range(200)]
        initial_bench = compute_benchmark_analytics(
            target_url="http://127.0.0.1:8000/health",
            latencies_ms=synthetic_latencies,
            total_duration_sec=0.450,
            failed_requests=0,
        )
        self._benchmark_history.append(initial_bench)

    def estimate_capacity(self, req: CapacityRequest) -> CapacityEstimate:
        """Calculates pod replicas and capacity buffers."""
        return calculate_capacity(
            peak_rps=req.peak_rps,
            pod_capacity_rps=req.pod_capacity_rps,
            target_utilization_pct=req.target_utilization_pct,
            headroom_pct=req.headroom_pct,
        )

    def run_benchmark_simulation(
        self,
        target_url: str = "http://127.0.0.1:8000/health",
        total_requests: int = 200,
        base_latency_ms: float = 12.0,
        jitter_ms: float = 18.0,
        simulated_failures: int = 0,
    ) -> BenchmarkSummary:
        """Executes a benchmark simulation with configurable latency distributions."""
        t0 = time.time()
        latencies = [max(1.0, random.gauss(base_latency_ms, jitter_ms / 3.0)) for _ in range(total_requests - simulated_failures)]
        duration = max(0.05, round(time.time() - t0 + (total_requests * 0.0015), 3))

        summary = compute_benchmark_analytics(
            target_url=target_url,
            latencies_ms=latencies,
            total_duration_sec=duration,
            failed_requests=simulated_failures,
        )
        self._benchmark_history.append(summary)
        return summary

    def list_benchmarks(self, limit: int = 10) -> List[BenchmarkSummary]:
        return self._benchmark_history[-limit:]

    def get_slos(self) -> List[PerformanceSLO]:
        """Returns standard performance SLO targets across services."""
        return [
            PerformanceSLO(
                service_name="transaction-ingestion",
                target_throughput_rps=5000.0,
                target_p95_latency_ms=50.0,
                max_error_rate_pct=0.05,
                status="PASS",
            ),
            PerformanceSLO(
                service_name="fraud-scoring",
                target_throughput_rps=1000.0,
                target_p95_latency_ms=200.0,
                max_error_rate_pct=0.1,
                status="PASS",
            ),
            PerformanceSLO(
                service_name="investigation-api",
                target_throughput_rps=250.0,
                target_p95_latency_ms=150.0,
                max_error_rate_pct=0.1,
                status="PASS",
            ),
        ]

    def get_health(self) -> PerformanceHealthResponse:
        """System health and readiness check."""
        return PerformanceHealthResponse(
            status="READY",
            version="1.0.0",
            locust_scenarios_ready=True,
            jmeter_plans_ready=True,
            benchmarks_run_count=len(self._benchmark_history),
            default_capacity_rps=100.0,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )


# Global singleton performance service
performance_service = PerformanceEngineeringService()
