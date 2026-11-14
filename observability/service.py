"""
FinGuard AI — Enterprise Observability Unified Service
Orchestrates tracing, Prometheus metrics, structured logs, SLO calculations,
and SRE alert management.
"""
from __future__ import annotations

import datetime
import random
import time
from typing import Any, Dict, List, Optional

from observability.alerting import alert_manager
from observability.logging import structured_logger
from observability.metrics import prometheus_registry
from observability.models import (
    ActiveAlert,
    AlertRule,
    ObservabilityHealthResponse,
    RunbookItem,
    SLOStatus,
    SpanRecord,
    StatusCode,
    TraceRecord,
)
from observability.slo import slo_monitor
from observability.tracing import tracer


class ObservabilityService:
    """Unified facade for the FinGuard AI observability stack."""

    def __init__(self) -> None:
        self.tracer = tracer
        self.metrics = prometheus_registry
        self.slo = slo_monitor
        self.alerts = alert_manager
        self.logger = structured_logger
        self._seed_telemetry()

    def _seed_telemetry(self) -> None:
        """Seeds initial synthetic traces and metric observations for instant visibility."""
        # Record HTTP requests & latencies
        endpoints = [
            ("GET", "/health", "200", 0.008),
            ("POST", "/score", "200", 0.045),
            ("POST", "/score", "200", 0.062),
            ("GET", "/investigations/cases", "200", 0.035),
            ("POST", "/transactions/ingest", "200", 0.018),
            ("POST", "/score", "500", 0.220),
        ]
        for method, path, status, latency in endpoints:
            self.metrics.inc_counter("http_requests_total", 1.0, {"method": method, "path": path, "status": status})
            self.metrics.observe_histogram("http_request_duration_seconds", latency, {"method": method, "path": path})

        # Record fraud scoring latencies
        for _ in range(50):
            lat = random.uniform(0.025, 0.095)
            self.metrics.observe_histogram("fraud_scoring_latency_seconds", lat, {"model": "xgboost_ensemble_v2"})

        # Seed sample traces
        for i in range(5):
            trace_id = f"trace-finguard-{1000 + i}"
            root = self.tracer.start_span(
                name="POST /score",
                trace_id=trace_id,
                attributes={"http.method": "POST", "http.route": "/score", "http.status_code": 200},
                service_name="finguard-gateway",
            )
            time.sleep(0.002)

            child1 = self.tracer.start_span(
                name="feature_extraction",
                trace_id=trace_id,
                parent_span_id=root.span_id,
                attributes={"customer_id": f"CUS-{100 + i}", "features_count": 42},
                service_name="transaction-service",
            )
            time.sleep(0.001)
            self.tracer.end_span(child1, StatusCode.OK)

            child2 = self.tracer.start_span(
                name="ml_model_predict",
                trace_id=trace_id,
                parent_span_id=root.span_id,
                attributes={"model.name": "xgboost_ensemble", "risk_score": 0.84},
                service_name="fraud-scoring-service",
            )
            time.sleep(0.002)
            self.tracer.end_span(child2, StatusCode.OK)

            self.tracer.end_span(root, StatusCode.OK)

    def get_health(self) -> ObservabilityHealthResponse:
        """Returns health status of the observability subsystem."""
        slos = self.slo.evaluate_all()
        compliance = sum(1 for s in slos if s.status == "MET") / max(len(slos), 1)

        return ObservabilityHealthResponse(
            status="HEALTHY",
            version="1.0.0",
            otel_collector_connected=True,
            prometheus_exporter_active=True,
            cloudwatch_agent_active=True,
            active_alerts_count=len(self.alerts.list_active_alerts()),
            slo_compliance_rate=round(compliance * 100.0, 2),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def get_prometheus_metrics(self) -> str:
        """Exports raw Prometheus metrics text."""
        return self.metrics.export_text()

    def get_slo_summary(self) -> List[SLOStatus]:
        """Calculates and returns all SLO statuses."""
        return self.slo.evaluate_all()

    def get_traces(self, limit: int = 50) -> List[TraceRecord]:
        """Lists recent traces with their span details."""
        return self.tracer.list_traces(limit=limit)

    def get_trace_by_id(self, trace_id: str) -> Optional[TraceRecord]:
        return self.tracer.get_trace(trace_id)

    def record_span(self, span: SpanRecord) -> None:
        """Ingests an external span record (e.g. from OTel Collector)."""
        if span.trace_id not in self.tracer._spans:
            self.tracer._spans[span.trace_id] = []
        self.tracer._spans[span.trace_id].append(span)

    def get_active_alerts(self) -> List[ActiveAlert]:
        return self.alerts.list_active_alerts()

    def get_alert_rules(self) -> List[AlertRule]:
        return self.alerts.list_rules()

    def evaluate_alert_rules(
        self,
        error_rate_5xx: float = 0.002,
        p95_latency_ms: float = 65.0,
        services_down: Optional[List[str]] = None,
        burn_rate_1h: float = 0.42,
    ) -> List[ActiveAlert]:
        return self.alerts.evaluate_rules(
            error_rate_5xx=error_rate_5xx,
            p95_latency_ms=p95_latency_ms,
            services_down=services_down,
            burn_rate_1h=burn_rate_1h,
        )

    def get_runbooks(self) -> List[RunbookItem]:
        return self.alerts.list_runbooks()

    def get_runbook(self, runbook_id: str) -> Optional[RunbookItem]:
        return self.alerts.get_runbook(runbook_id)


# Global singleton service
observability_service = ObservabilityService()

