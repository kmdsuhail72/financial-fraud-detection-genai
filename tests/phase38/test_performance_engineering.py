"""
FinGuard AI — Phase 38: Enterprise Performance Engineering & Capacity Planning Test Suite.
Validates:
1. Performance subsystem health & readiness (/performance/health)
2. Capacity calculator baseline: 100 RPS, 25 RPS/pod, 65% target utilization, 30% headroom -> 8 replicas
3. Capacity calculator dynamic scaling scenarios
4. Latency percentiles analytics: p50, p90, p95, p99, and throughput calculation
5. JMeter test plan XML validation & Kubernetes HPA YAML validation
6. Locustfile structure, tasks distribution, and wait times
"""
from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient
import yaml

from api.app import app
from performance.capacity import calculate_capacity
from performance.service import performance_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_performance_health_and_capabilities(client: TestClient):
    """1. Validates /performance/health returns operational readiness of performance tools."""
    resp = client.get("/performance/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "READY"
    assert data["locust_scenarios_ready"] is True
    assert data["jmeter_plans_ready"] is True
    assert data["benchmarks_run_count"] >= 1


def test_capacity_calculation_baseline_100rps(client: TestClient):
    """
    2. Validates the capacity equation matching Phase 38 specification:
    100 RPS peak, 25 RPS/pod capacity, 65% utilization, 30% headroom -> exactly 8 replicas.
    """
    payload = {
        "peak_rps": 100.0,
        "pod_capacity_rps": 25.0,
        "target_utilization_pct": 65.0,
        "headroom_pct": 30.0,
    }
    resp = client.post("/performance/capacity/estimate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["recommended_replicas"] == 8
    assert data["effective_pod_capacity_rps"] == 16.25
    assert data["traffic_with_headroom_rps"] == 130.0
    assert data["base_replicas"] == 4
    assert data["total_cluster_capacity_rps"] == 200.0
    assert data["safety_buffer_rps"] == 100.0
    assert "8 pod replicas are recommended" in data["formula_explanation"]


def test_capacity_calculation_scaling_scenarios():
    """3. Validates dynamic scaling under multiple throughput tiers."""
    # Test 500 RPS workload
    est_500 = calculate_capacity(peak_rps=500.0, pod_capacity_rps=25.0, target_utilization_pct=65.0, headroom_pct=30.0)
    # (500 * 1.30) / (25 * 0.65) = 650 / 16.25 = 40 replicas
    assert est_500.recommended_replicas == 40
    assert est_500.total_cluster_capacity_rps == 1000.0

    # Test 50 RPS workload with 20% headroom
    est_50 = calculate_capacity(peak_rps=50.0, pod_capacity_rps=20.0, target_utilization_pct=50.0, headroom_pct=20.0)
    # (50 * 1.20) / (20 * 0.50) = 60 / 10 = 6 replicas
    assert est_50.recommended_replicas == 6


def test_benchmark_simulation_and_percentiles(client: TestClient):
    """4. Validates API benchmark simulation and statistical percentile computations (p50, p90, p95, p99)."""
    resp = client.post("/performance/benchmark/simulate?total_requests=200&base_latency_ms=15.0&jitter_ms=10.0")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_requests"] == 200
    assert data["successful_requests"] == 200
    assert data["error_rate_pct"] == 0.0
    assert data["throughput_rps"] > 0.0

    # Validate monotonic percentile hierarchy
    assert data["min_latency_ms"] <= data["p50_latency_ms"]
    assert data["p50_latency_ms"] <= data["p90_latency_ms"]
    assert data["p90_latency_ms"] <= data["p95_latency_ms"]
    assert data["p95_latency_ms"] <= data["p99_latency_ms"]
    assert data["p99_latency_ms"] <= data["max_latency_ms"]


def test_jmeter_xml_and_kubernetes_yaml_validation():
    """5. Validates that Apache JMeter test plan is well-formed XML and Kubernetes manifests are valid YAML."""
    jmeter_file = Path("jmeter/finguard_performance_plan.jmx")
    assert jmeter_file.exists()
    tree = ET.parse(jmeter_file)
    root = tree.getroot()
    assert root.tag == "jmeterTestPlan"
    assert root.attrib.get("version") == "1.2"

    # Validate Kubernetes HPA YAML
    hpa_file = Path("k8s/performance/hpa-performance.yaml")
    assert hpa_file.exists()
    with open(hpa_file, "r") as fp:
        hpa_manifest = yaml.safe_load(fp)
    assert hpa_manifest["kind"] == "HorizontalPodAutoscaler"
    assert hpa_manifest["spec"]["metrics"][0]["resource"]["target"]["averageUtilization"] == 65

    # Validate Kubernetes Resource Planning YAML
    resource_file = Path("k8s/performance/resource-planning.yaml")
    assert resource_file.exists()
    with open(resource_file, "r") as fp:
        res_manifest = yaml.safe_load(fp)
    assert res_manifest["kind"] == "ConfigMap"


def test_locustfile_structure_and_tasks():
    """6. Validates Locustfile configuration, HTTP user class, and task weights."""
    locust_file = Path("locust/locustfile.py")
    assert locust_file.exists()
    content = locust_file.read_text(encoding="utf-8")

    assert "class FinGuardLoadUser(HttpUser):" in content
    assert "@task(10)" in content
    assert "@task(8)" in content
    assert 'self.client.post("/score"' in content
    assert 'self.client.get("/health"' in content
    assert "between(0.05, 0.25)" in content

