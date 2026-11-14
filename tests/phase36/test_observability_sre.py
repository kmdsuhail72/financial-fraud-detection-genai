"""
FinGuard AI — Phase 36: Enterprise Observability & SRE Test Suite
Validates OpenTelemetry distributed tracing, Prometheus metrics export,
SLO & error budget computation, SRE alerting & runbooks, and structured JSON logs.
"""
from __future__ import annotations

import json
import logging
import pytest
from fastapi.testclient import TestClient

from api.app import app
from observability.logging import JSONFormatter, current_request_id, current_span_id, current_trace_id
from observability.models import AlertSeverity, AlertState, SpanKind, StatusCode
from observability.service import observability_service
from observability.tracing import tracer


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_observability_health(client: TestClient):
    """1. Validates that the Observability subsystem health check responds with all active connectors."""
    resp = client.get("/observability/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "HEALTHY"
    assert data["otel_collector_connected"] is True
    assert data["prometheus_exporter_active"] is True
    assert data["cloudwatch_agent_active"] is True
    assert isinstance(data["slo_compliance_rate"], float)
    assert data["slo_compliance_rate"] >= 0.0


def test_prometheus_metrics_endpoint(client: TestClient):
    """2. Validates that both /metrics and /observability/metrics export standard Prometheus exposition text."""
    # Test root endpoint with standard Prometheus scraper Accept header
    resp_root = client.get("/metrics", headers={"Accept": "text/plain"})
    assert resp_root.status_code == 200
    assert "text/plain" in resp_root.headers["content-type"]
    assert "# HELP http_requests_total" in resp_root.text

    # Test dedicated observability endpoint
    resp_obs = client.get("/observability/metrics")
    assert resp_obs.status_code == 200
    assert "text/plain" in resp_obs.headers["content-type"]
    text = resp_obs.text

    # Verify Prometheus comment headers and metric series
    assert "# HELP http_requests_total" in text
    assert "# TYPE http_requests_total counter"
    assert "http_requests_total" in text
    assert "fraud_scoring_latency_seconds" in text
    assert "finguard_service_up" in text


def test_distributed_tracing_spans(client: TestClient):
    """3. Validates span creation, parent-child hierarchies, W3C traceparent formatting, and trace query API."""
    trace_id = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    root_span = tracer.start_span(
        name="test_checkout_flow",
        trace_id=trace_id,
        kind=SpanKind.SERVER,
        attributes={"customer.tier": "PLATINUM"},
    )
    assert root_span.trace_id == trace_id
    assert root_span.parent_span_id is None

    # Child span
    child_span = tracer.start_span(
        name="test_fraud_check",
        trace_id=trace_id,
        parent_span_id=root_span.span_id,
        kind=SpanKind.INTERNAL,
        attributes={"model": "lightgbm_v3"},
    )
    assert child_span.parent_span_id == root_span.span_id
    tracer.end_span(child_span, StatusCode.OK)
    tracer.end_span(root_span, StatusCode.OK)

    # W3C traceparent generation
    tp = tracer.inject_traceparent(root_span)
    assert tp.startswith(f"00-{trace_id}-")
    assert tp.endswith("-01")

    # W3C traceparent extraction
    parsed = tracer.extract_traceparent(tp)
    assert parsed is not None
    assert parsed["trace_id"] == trace_id

    # Query via API
    resp = client.get(f"/observability/traces/{trace_id}")
    assert resp.status_code == 200
    trace_data = resp.json()
    assert trace_data["trace_id"] == trace_id
    assert trace_data["total_spans"] >= 2
    assert trace_data["has_errors"] is False


def test_slo_and_error_budget(client: TestClient):
    """4. Validates that /slo computes availability compliance, error budgets, and latency percentiles."""
    for endpoint in ["/slo", "/observability/slo"]:
        resp = client.get(endpoint)
        assert resp.status_code == 200
        slos = resp.json()
        assert len(slos) >= 2

        core_slo = next(s for s in slos if s["slo_id"] == "slo-avail-core")
        assert core_slo["target_percentage"] == 99.9
        assert core_slo["error_budget_total_percentage"] == 0.1
        assert 0.0 <= core_slo["error_budget_remaining_percentage"] <= 100.0
        assert core_slo["p50_latency_ms"] <= core_slo["p95_latency_ms"]
        assert core_slo["p95_latency_ms"] <= core_slo["p99_latency_ms"]
        assert core_slo["status"] in ["MET", "AT_RISK", "BREACHED"]


def test_alerting_rules_evaluation(client: TestClient):
    """5. Validates automated evaluation of SRE alerting rules (5xx spike and latency breach)."""
    # Simulate normal conditions
    resp = client.post(
        "/observability/alerts/evaluate",
        json={"error_rate_5xx": 0.001, "p95_latency_ms": 50.0, "burn_rate_1h": 0.3},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    # Simulate 5xx error breach (> 1%)
    resp_5xx = client.post(
        "/observability/alerts/evaluate",
        json={"error_rate_5xx": 0.035, "p95_latency_ms": 60.0, "burn_rate_1h": 1.0},
    )
    assert resp_5xx.status_code == 200
    alerts = resp_5xx.json()
    assert any(a["alert_name"] == "High5xxErrorRate" and a["severity"] == "CRITICAL" for a in alerts)

    # Simulate p95 latency breach (> 200ms)
    resp_lat = client.post(
        "/observability/alerts/evaluate",
        json={"error_rate_5xx": 0.001, "p95_latency_ms": 285.0, "burn_rate_1h": 0.5},
    )
    assert resp_lat.status_code == 200
    alerts_lat = resp_lat.json()
    assert any(a["alert_name"] == "HighFraudScoringLatencyP95" and a["severity"] == "WARNING" for a in alerts_lat)


def test_structured_json_logging():
    """6. Validates that JSONFormatter formats log entries into parseable JSON with contextual correlation IDs."""
    formatter = JSONFormatter(service_name="test-service")
    logger = logging.getLogger("test-logger")

    current_request_id.set("req-test-999")
    current_trace_id.set("trace-test-888")
    current_span_id.set("span-test-777")

    record = logger.makeRecord(
        name="test-logger",
        level=logging.ERROR,
        fn="test_observability_sre.py",
        lno=42,
        msg="Database query timeout occurred",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["service"] == "test-service"
    assert parsed["level"] == "ERROR"
    assert parsed["message"] == "Database query timeout occurred"
    assert parsed["request_id"] == "req-test-999"
    assert parsed["trace_id"] == "trace-test-888"
    assert parsed["span_id"] == "span-test-777"


def test_cloudwatch_and_runbooks(client: TestClient):
    """7. Validates retrieval of operational SRE runbooks with triage steps and rollback commands."""
    resp = client.get("/observability/runbooks")
    assert resp.status_code == 200
    runbooks = resp.json()
    assert len(runbooks) >= 2

    rb_5xx = next(r for r in runbooks if r["id"] == "rb-5xx")
    assert "High 5xx Error Rate" in rb_5xx["title"]
    assert len(rb_5xx["immediate_actions"]) > 0
    assert "kubectl rollout undo" in rb_5xx["rollback_command"]

    # Test single runbook retrieval
    resp_single = client.get("/observability/runbooks/rb-5xx")
    assert resp_single.status_code == 200
    assert resp_single.json()["id"] == "rb-5xx"


def test_end_to_end_request_tracing_middleware(client: TestClient):
    """8. Validates that incoming HTTP requests are automatically traced, returning trace headers and metrics."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    assert "x-trace-id" in resp.headers
    assert "traceparent" in resp.headers

    trace_id = resp.headers["x-trace-id"]
    assert len(trace_id) == 32

    # Verify that the trace was registered in the tracer
    trace = tracer.get_trace(trace_id)
    assert trace is not None
    assert trace.root_span_name == "GET /health"
    assert trace.has_errors is False
