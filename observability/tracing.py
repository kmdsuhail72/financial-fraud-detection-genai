"""
FinGuard AI — OpenTelemetry Compatible Distributed Tracing
Supports W3C traceparent parsing/generation, context propagation,
in-memory span buffer, and span tree composition.
"""
from __future__ import annotations

import functools
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from observability.logging import current_request_id, current_span_id, current_trace_id
from observability.models import SpanKind, SpanRecord, StatusCode, TraceRecord


TRACEPARENT_REGEX = re.compile(r"^00-([0-9a-fA-F]{32})-([0-9a-fA-F]{16})-([0-9a-fA-F]{2})$")


class DistributedTracer:
    """Manages spans, distributed trace contexts, and span tree assembly."""

    def __init__(self, service_name: str = "finguard-service", max_retained_traces: int = 500) -> None:
        self.service_name = service_name
        self.max_retained_traces = max_retained_traces
        self._spans: Dict[str, List[SpanRecord]] = {}  # trace_id -> list of spans

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.SERVER,
        attributes: Optional[Dict[str, Any]] = None,
        service_name: Optional[str] = None,
    ) -> SpanRecord:
        """Starts a new span and attaches it to the current context."""
        active_trace_id = trace_id or current_trace_id.get() or uuid.uuid4().hex
        if parent_span_id is not None:
            active_parent_id = parent_span_id
        elif trace_id is not None and trace_id != current_trace_id.get():
            active_parent_id = None
        elif kind == SpanKind.SERVER and trace_id is None:
            active_parent_id = None
        else:
            active_parent_id = current_span_id.get()
        new_span_id = uuid.uuid4().hex[:16]

        span = SpanRecord(
            trace_id=active_trace_id,
            span_id=new_span_id,
            parent_span_id=active_parent_id,
            name=name,
            service_name=service_name or self.service_name,
            kind=kind,
            start_time_ns=int(time.time() * 1e9),
            attributes=attributes or {},
        )

        current_trace_id.set(active_trace_id)
        current_span_id.set(new_span_id)

        if active_trace_id not in self._spans:
            if len(self._spans) >= self.max_retained_traces:
                # Evict oldest trace
                oldest_key = next(iter(self._spans))
                del self._spans[oldest_key]
            self._spans[active_trace_id] = []

        self._spans[active_trace_id].append(span)
        return span

    def end_span(
        self,
        span: SpanRecord,
        status_code: StatusCode = StatusCode.OK,
        status_message: Optional[str] = None,
    ) -> None:
        """Marks a span as complete and calculates duration."""
        span.end_time_ns = int(time.time() * 1e9)
        span.duration_ms = round((span.end_time_ns - span.start_time_ns) / 1e6, 3)
        span.status_code = status_code
        span.status_message = status_message

    def trace(
        self,
        name: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Decorator to trace a function execution."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                span_name = name or func.__name__
                span = self.start_span(name=span_name, kind=kind, attributes=attributes)
                try:
                    result = func(*args, **kwargs)
                    self.end_span(span, StatusCode.OK)
                    return result
                except Exception as exc:
                    self.end_span(span, StatusCode.ERROR, status_message=str(exc))
                    raise
            return wrapper
        return decorator

    def extract_traceparent(self, header_value: Optional[str]) -> Optional[Dict[str, str]]:
        """Parses W3C traceparent header '00-<trace_id>-<span_id>-<flags>'."""
        if not header_value:
            return None
        match = TRACEPARENT_REGEX.match(header_value.strip())
        if match:
            return {
                "version": "00",
                "trace_id": match.group(1),
                "parent_id": match.group(2),
                "trace_flags": match.group(3),
            }
        return None

    def inject_traceparent(self, span: SpanRecord) -> str:
        """Generates W3C traceparent header value."""
        return f"00-{span.trace_id}-{span.span_id}-01"

    def get_trace(self, trace_id: str) -> Optional[TraceRecord]:
        """Assembles a full TraceRecord from stored spans."""
        spans = self._spans.get(trace_id)
        if not spans:
            return None

        root_span = next((s for s in spans if s.parent_span_id is None), spans[0])
        total_duration = max((s.duration_ms or 0.0) for s in spans)
        has_errors = any(s.status_code == StatusCode.ERROR for s in spans)

        return TraceRecord(
            trace_id=trace_id,
            root_span_name=root_span.name,
            service_name=root_span.service_name,
            total_spans=len(spans),
            duration_ms=total_duration,
            has_errors=has_errors,
            spans=spans,
        )

    def list_traces(self, limit: int = 50) -> List[TraceRecord]:
        """Lists recent traces."""
        traces = []
        for trace_id in list(self._spans.keys())[-limit:]:
            trace = self.get_trace(trace_id)
            if trace:
                traces.append(trace)
        traces.reverse()
        return traces


# Global singleton tracer
tracer = DistributedTracer(service_name="finguard-core")
