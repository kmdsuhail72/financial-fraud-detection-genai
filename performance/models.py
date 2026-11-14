"""
FinGuard AI — Enterprise Performance Engineering & Capacity Planning Models
Schemas for capacity estimation, latency percentiles, benchmarking, and performance SLOs.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CapacityRequest(BaseModel):
    peak_rps: float = Field(100.0, ge=1.0, description="Expected peak requests per second", json_schema_extra={"example": 100.0})
    pod_capacity_rps: float = Field(25.0, ge=1.0, description="Per-pod assumed capacity in RPS", json_schema_extra={"example": 25.0})
    target_utilization_pct: float = Field(65.0, ge=10.0, le=100.0, description="Target CPU/thread utilization percentage", json_schema_extra={"example": 65.0})
    headroom_pct: float = Field(30.0, ge=0.0, le=200.0, description="Headroom buffer percentage for traffic spikes", json_schema_extra={"example": 30.0})

    model_config = ConfigDict(extra="allow")


class CapacityEstimate(BaseModel):
    peak_rps: float
    pod_capacity_rps: float
    target_utilization_pct: float
    headroom_pct: float
    effective_pod_capacity_rps: float
    traffic_with_headroom_rps: float
    base_replicas: int
    recommended_replicas: int
    total_cluster_capacity_rps: float
    safety_buffer_rps: float
    formula_explanation: str
    calculated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    model_config = ConfigDict(extra="allow")


class BenchmarkRequest(BaseModel):
    target_url: str = Field("http://127.0.0.1:8000/health", description="Target endpoint URL", json_schema_extra={"example": "http://127.0.0.1:8000/health"})
    total_requests: int = Field(200, ge=1, le=5000, description="Total number of requests to execute", json_schema_extra={"example": 200})
    concurrency: int = Field(10, ge=1, le=100, description="Concurrent simulated virtual users", json_schema_extra={"example": 10})
    http_method: str = Field("GET", description="HTTP method (GET, POST)", json_schema_extra={"example": "GET"})
    payload: Optional[Dict[str, Any]] = Field(None, description="Optional request payload for POST")

    model_config = ConfigDict(extra="allow")


class BenchmarkSummary(BaseModel):
    target_url: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate_pct: float
    total_duration_sec: float
    throughput_rps: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    tested_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    model_config = ConfigDict(extra="allow")


class PerformanceSLO(BaseModel):
    service_name: str
    target_throughput_rps: float
    target_p95_latency_ms: float
    max_error_rate_pct: float
    status: str  # PASS | AT_RISK | FAIL

    model_config = ConfigDict(extra="allow")


class PerformanceHealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    locust_scenarios_ready: bool
    jmeter_plans_ready: bool
    benchmarks_run_count: int
    default_capacity_rps: float
    timestamp: str

    model_config = ConfigDict(extra="allow")

