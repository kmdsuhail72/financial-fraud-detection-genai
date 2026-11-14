"""
FinGuard AI — Structured JSON Logging
Provides RFC-compliant structured JSON logging with correlation IDs,
trace/span context injection, and CloudWatch Logs compatibility.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Context variables for distributed request and trace tracking
current_trace_id: ContextVar[Optional[str]] = ContextVar("current_trace_id", default=None)
current_span_id: ContextVar[Optional[str]] = ContextVar("current_span_id", default=None)
current_request_id: ContextVar[Optional[str]] = ContextVar("current_request_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects, incorporating
    trace IDs, span IDs, service names, and custom attributes.
    """

    def __init__(self, service_name: str = "finguard-observability", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt) if self.datefmt else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": getattr(record, "service", self.service_name),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", current_request_id.get()),
            "trace_id": getattr(record, "trace_id", current_trace_id.get()),
            "span_id": getattr(record, "span_id", current_span_id.get()),
        }

        # Include exception info if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Include any extra structured attributes
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_payload.update(record.extra_fields)

        return json.dumps(log_payload)


def configure_structured_logging(
    service_name: str = "finguard-observability",
    level: int = logging.INFO,
) -> logging.Logger:
    """Configures the root or application logger with JSON formatting."""
    logger = logging.getLogger(service_name)
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name=service_name))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


# Default logger instance
structured_logger = configure_structured_logging()

