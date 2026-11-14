"""
FinGuard AI — Enterprise Performance Engineering & Capacity Planning Router
Exposes APIs for capacity planning calculations, benchmark simulations,
latency percentile analytics, and performance SLO validation.
"""
from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query, status

from performance.models import (
    BenchmarkRequest,
    BenchmarkSummary,
    CapacityEstimate,
    CapacityRequest,
    PerformanceHealthResponse,
    PerformanceSLO,
)
from performance.service import performance_service

performance_router = APIRouter(prefix="/performance", tags=["Performance Engineering & Capacity Planning"])


@performance_router.get("/health", response_model=PerformanceHealthResponse)
def get_performance_health():
    """Health check for the Performance Engineering subsystem."""
    return performance_service.get_health()


@performance_router.post("/capacity/estimate", response_model=CapacityEstimate)
def estimate_capacity(req: CapacityRequest):
    """
    Calculates recommended Kubernetes pod replicas and cluster capacity
    based on expected peak RPS, target utilization, and traffic headroom.
    """
    return performance_service.estimate_capacity(req)


@performance_router.post("/benchmark/simulate", response_model=BenchmarkSummary)
def simulate_benchmark(
    target_url: str = Query("http://127.0.0.1:8000/health", description="Target endpoint"),
    total_requests: int = Query(200, ge=10, le=2000, description="Total requests"),
    base_latency_ms: float = Query(14.0, ge=1.0, description="Baseline latency in ms"),
    jitter_ms: float = Query(20.0, ge=0.0, description="Latency jitter in ms"),
    simulated_failures: int = Query(0, ge=0, description="Number of simulated 5xx failures"),
):
    """Executes a benchmark simulation and computes p50, p90, p95, p99 latencies."""
    return performance_service.run_benchmark_simulation(
        target_url=target_url,
        total_requests=total_requests,
        base_latency_ms=base_latency_ms,
        jitter_ms=jitter_ms,
        simulated_failures=simulated_failures,
    )


@performance_router.get("/benchmark/history", response_model=List[BenchmarkSummary])
def get_benchmark_history(limit: int = Query(10, ge=1, le=50)):
    """Retrieves recent benchmark run summaries."""
    return performance_service.list_benchmarks(limit=limit)


@performance_router.get("/slos", response_model=List[PerformanceSLO])
def get_performance_slos():
    """Retrieves standard performance SLO targets across services."""
    return performance_service.get_slos()


@performance_router.get("/plans")
def get_load_test_plans() -> Dict[str, Any]:
    """Returns metadata regarding configured Locust and JMeter load test assets."""
    return {
        "locust": {
            "scenario_file": "locust/locustfile.py",
            "user_class": "FinGuardLoadUser",
            "default_tasks": ["/health (10x)", "/score (8x)", "/investigations/cases (3x)", "/metrics (2x)"],
            "command_example": "locust -f locust/locustfile.py --host http://127.0.0.1:8000",
        },
        "jmeter": {
            "test_plan_file": "jmeter/finguard_performance_plan.jmx",
            "threads": 100,
            "ramp_up_sec": 10,
            "loop_count": 50,
            "command_example": "jmeter -n -t jmeter/finguard_performance_plan.jmx -l results.jtl",
        },
        "kubernetes": {
            "hpa_manifest": "k8s/performance/hpa-performance.yaml",
            "target_cpu_utilization": 65,
            "min_replicas": 3,
            "max_replicas": 24,
        },
    }

