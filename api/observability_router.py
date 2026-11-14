"""
FinGuard AI — Enterprise Observability & SRE FastAPI Router
Exposes endpoints for Prometheus scraping, SLO status, distributed traces,
SRE alerts, and operational runbooks.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from observability.models import (
    ActiveAlert,
    AlertRule,
    ObservabilityHealthResponse,
    RunbookItem,
    SLOStatus,
    SpanRecord,
    TraceRecord,
)
from observability.service import observability_service

observability_router = APIRouter(prefix="/observability", tags=["Observability & SRE"])


class EvaluateAlertsRequest(BaseModel):
    error_rate_5xx: float = Field(0.002, description="Simulated 5xx error rate ratio (e.g. 0.015 for 1.5%)")
    p95_latency_ms: float = Field(65.0, description="Simulated p95 latency in milliseconds")
    services_down: Optional[List[str]] = Field(default=None, description="List of services to simulate DOWN")
    burn_rate_1h: float = Field(0.42, description="Simulated 1h error budget burn rate")

    model_config = ConfigDict(extra="allow")


@observability_router.get("/health", response_model=ObservabilityHealthResponse)
def get_observability_health():
    """Health check for the FinGuard Observability subsystem."""
    return observability_service.get_health()


@observability_router.get("/metrics")
def get_prometheus_metrics():
    """
    Exposes all registered FinGuard AI metrics in standard Prometheus
    exposition text format for Prometheus scraping.
    """
    text_data = observability_service.get_prometheus_metrics()
    return Response(content=text_data, media_type="text/plain; version=0.0.4; charset=utf-8")


@observability_router.get("/slo", response_model=List[SLOStatus])
def get_slo_status():
    """Retrieves current SLO compliance, error budgets, and latency percentiles."""
    return observability_service.get_slo_summary()


@observability_router.get("/traces", response_model=List[TraceRecord])
def list_traces(limit: int = Query(50, ge=1, le=200)):
    """Lists recent distributed traces with span hierarchies."""
    return observability_service.get_traces(limit=limit)


@observability_router.get("/traces/{trace_id}", response_model=TraceRecord)
def get_trace(trace_id: str):
    """Retrieves a specific trace by its 128-bit trace ID."""
    trace = observability_service.get_trace_by_id(trace_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with ID '{trace_id}' not found.",
        )
    return trace


@observability_router.post("/traces/spans", status_code=status.HTTP_201_CREATED)
def record_span(span: SpanRecord):
    """Ingests an external span record from an OTel instrumented microservice."""
    observability_service.record_span(span)
    return {"status": "RECORDED", "trace_id": span.trace_id, "span_id": span.span_id}


@observability_router.get("/alerts", response_model=List[ActiveAlert])
def get_active_alerts():
    """Returns currently firing SRE incident alerts."""
    return observability_service.get_active_alerts()


@observability_router.get("/alerts/rules", response_model=List[AlertRule])
def get_alert_rules():
    """Returns all configured Prometheus alerting rules."""
    return observability_service.get_alert_rules()


@observability_router.post("/alerts/evaluate", response_model=List[ActiveAlert])
def evaluate_alert_rules(payload: EvaluateAlertsRequest):
    """Evaluates alerting rules against provided or current telemetry conditions."""
    return observability_service.evaluate_alert_rules(
        error_rate_5xx=payload.error_rate_5xx,
        p95_latency_ms=payload.p95_latency_ms,
        services_down=payload.services_down,
        burn_rate_1h=payload.burn_rate_1h,
    )


@observability_router.get("/runbooks", response_model=List[RunbookItem])
def get_runbooks():
    """Lists all operational SRE runbooks."""
    return observability_service.get_runbooks()


@observability_router.get("/runbooks/{runbook_id}", response_model=RunbookItem)
def get_runbook(runbook_id: str):
    """Retrieves an operational SRE runbook by ID."""
    rb = observability_service.get_runbook(runbook_id)
    if not rb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Runbook with ID '{runbook_id}' not found.",
        )
    return rb
