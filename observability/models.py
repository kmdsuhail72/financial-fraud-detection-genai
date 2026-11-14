"""
FinGuard AI — Enterprise Observability & SRE Data Models
Pydantic schemas for distributed tracing, metrics, SLOs, alerts, and runbooks.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SpanKind(str, Enum):
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


class StatusCode(str, Enum):
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertState(str, Enum):
    PENDING = "PENDING"
    FIRING = "FIRING"
    RESOLVED = "RESOLVED"
    SILENCED = "SILENCED"


class SpanRecord(BaseModel):
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: Optional[str] = None
    name: str
    service_name: str = "finguard-gateway"
    kind: SpanKind = SpanKind.SERVER
    start_time_ns: int = Field(default_factory=lambda: int(time.time() * 1e9))
    end_time_ns: Optional[int] = None
    duration_ms: Optional[float] = None
    status_code: StatusCode = StatusCode.OK
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class TraceRecord(BaseModel):
    trace_id: str
    root_span_name: str
    service_name: str
    total_spans: int
    duration_ms: float
    has_errors: bool
    spans: List[SpanRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class SLODefinition(BaseModel):
    id: str
    name: str
    service: str
    target_percentage: float = 99.9  # e.g., 99.9%
    time_window_days: int = 30
    metric_type: str = "availability"  # availability | latency | error_rate
    threshold_value: Optional[float] = None  # e.g. 200 ms for latency
    description: str

    model_config = ConfigDict(extra="allow")


class SLOStatus(BaseModel):
    slo_id: str
    name: str
    service: str
    target_percentage: float
    current_percentage: float
    status: str  # MET | AT_RISK | BREACHED
    error_budget_total_percentage: float
    error_budget_consumed_percentage: float
    error_budget_remaining_percentage: float
    burn_rate_1h: float
    burn_rate_6h: float
    total_requests: int
    bad_requests: int
    p50_latency_ms: float
    p90_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float

    model_config = ConfigDict(extra="allow")


class AlertRule(BaseModel):
    name: str
    severity: AlertSeverity
    expr: str
    duration_minutes: int
    description: str
    runbook_url: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class ActiveAlert(BaseModel):
    id: str = Field(default_factory=lambda: f"alt-{uuid.uuid4().hex[:8]}")
    alert_name: str
    severity: AlertSeverity
    state: AlertState
    service: str
    summary: str
    started_at: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    runbook_url: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class RunbookItem(BaseModel):
    id: str
    title: str
    severity: AlertSeverity
    trigger_condition: str
    immediate_actions: List[str]
    investigation_steps: List[str]
    mitigation_steps: List[str]
    rollback_command: Optional[str] = None
    escalation_contacts: List[str]

    model_config = ConfigDict(extra="allow")


class ObservabilityHealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    otel_collector_connected: bool
    prometheus_exporter_active: bool
    cloudwatch_agent_active: bool
    active_alerts_count: int
    slo_compliance_rate: float
    timestamp: str

    model_config = ConfigDict(extra="allow")
