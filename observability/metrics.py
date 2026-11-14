"""
FinGuard AI — Prometheus Metrics Registry and Exporter
Implements in-memory counters, gauges, histograms, and standard
Prometheus text exposition format output.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional, Tuple


class MetricValue:
    def __init__(self, name: str, mtype: str, help_text: str):
        self.name = name
        self.mtype = mtype
        self.help_text = help_text
        self.samples: Dict[Tuple[Tuple[str, str], ...], float] = {}
        self.histograms: Dict[Tuple[Tuple[str, str], ...], List[float]] = {}


class PrometheusRegistry:
    """Thread-safe Prometheus metrics registry supporting standard types."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: Dict[str, MetricValue] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        self.register("http_requests_total", "counter", "Total HTTP requests handled by FinGuard AI.")
        self.register("http_request_duration_seconds", "histogram", "HTTP request execution latency in seconds.")
        self.register("fraud_scoring_latency_seconds", "histogram", "Latency of fraud scoring inference in seconds.")
        self.register("transaction_processing_errors_total", "counter", "Total transaction processing failures.")
        self.register("finguard_active_investigations", "gauge", "Number of currently active investigation cases.")
        self.register("finguard_slo_compliance_ratio", "gauge", "Current ratio of requests compliant with SLO.")
        self.register("finguard_service_up", "gauge", "1 if service instance is healthy and reachable.")

        # Seed initial values
        self.set_gauge("finguard_service_up", 1.0, {"service": "finguard-gateway"})
        self.set_gauge("finguard_service_up", 1.0, {"service": "transaction-service"})
        self.set_gauge("finguard_service_up", 1.0, {"service": "fraud-scoring-service"})
        self.set_gauge("finguard_active_investigations", 14.0)
        self.set_gauge("finguard_slo_compliance_ratio", 0.9992)

    def register(self, name: str, mtype: str, help_text: str) -> None:
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = MetricValue(name, mtype, help_text)

    def _labels_key(self, labels: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            if name not in self._metrics:
                self.register(name, "counter", f"Counter for {name}")
            metric = self._metrics[name]
            key = self._labels_key(labels)
            metric.samples[key] = metric.samples.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            if name not in self._metrics:
                self.register(name, "gauge", f"Gauge for {name}")
            metric = self._metrics[name]
            key = self._labels_key(labels)
            metric.samples[key] = value

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            if name not in self._metrics:
                self.register(name, "histogram", f"Histogram for {name}")
            metric = self._metrics[name]
            key = self._labels_key(labels)
            if key not in metric.histograms:
                metric.histograms[key] = []
            metric.histograms[key].append(value)
            # Track sum and count
            metric.samples[key] = metric.samples.get(key, 0.0) + value

    def get_percentile(self, name: str, percentile: float, labels: Optional[Dict[str, str]] = None) -> float:
        """Calculates percentile (e.g. 0.95 for p95) from observed values."""
        with self._lock:
            metric = self._metrics.get(name)
            if not metric:
                return 0.0
            key = self._labels_key(labels)
            values = metric.histograms.get(key, [])
            if not values:
                return 0.0
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * percentile)
            idx = min(idx, len(sorted_vals) - 1)
            return sorted_vals[idx]

    def export_text(self) -> str:
        """Formats all registered metrics into Prometheus exposition text format."""
        lines: List[str] = []
        with self._lock:
            for name, metric in self._metrics.items():
                lines.append(f"# HELP {name} {metric.help_text}")
                lines.append(f"# TYPE {name} {metric.mtype}")

                if metric.mtype in ("counter", "gauge"):
                    for label_tuple, value in metric.samples.items():
                        if label_tuple:
                            label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                            lines.append(f"{name}{{{label_str}}} {value}")
                        else:
                            lines.append(f"{name} {value}")

                elif metric.mtype == "histogram":
                    buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                    for label_tuple, vals in metric.histograms.items():
                        base_labels = dict(label_tuple)
                        for b in buckets:
                            count = sum(1 for v in vals if v <= b)
                            b_labels = dict(base_labels)
                            b_labels["le"] = str(b)
                            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(b_labels.items()))
                            lines.append(f"{name}_bucket{{{label_str}}} {count}")

                        inf_labels = dict(base_labels)
                        inf_labels["le"] = "+Inf"
                        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(inf_labels.items()))
                        lines.append(f"{name}_bucket{{{label_str}}} {len(vals)}")

                        sum_labels = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                        prefix = f"{{{sum_labels}}}" if sum_labels else ""
                        lines.append(f"{name}_sum{prefix} {sum(vals)}")
                        lines.append(f"{name}_count{prefix} {len(vals)}")

        return "\n".join(lines) + "\n"


# Global singleton registry
prometheus_registry = PrometheusRegistry()

