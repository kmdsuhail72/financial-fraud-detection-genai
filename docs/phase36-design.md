# FinGuard AI — Phase 36 Architecture & Design Specification
## Enterprise Observability, OpenTelemetry, Distributed Tracing, Prometheus, Grafana, CloudWatch & SRE Monitoring

---

## 1. Executive Summary

Phase 36 implements comprehensive enterprise observability across the FinGuard AI ecosystem. It integrates OpenTelemetry (OTel) for distributed tracing and context propagation, Prometheus for metric collection and alerting, Grafana for unified SRE dashboards, AWS CloudWatch for cloud logs and infrastructure alarms in AWS Mumbai (`ap-south-1`), and an automated SLO/Error Budget governance engine with actionable SRE runbooks.

---

## 2. High-Level Observability Architecture

```mermaid
flowchart TD
    subgraph Client & Gateway Tier
        GW["FinGuard API Gateway"]
        UI["React SRE Console"]
    end

    subgraph Microservices Tier on EKS
        TXN["Transaction Service"]
        FRD["Fraud Scoring Service"]
        INV["Investigation Service"]
    end

    subgraph Telemetry Pipeline
        OTEL["OpenTelemetry Collector (OTLP 4317/4318)"]
        PROM["Prometheus Server (:9090)"]
        CW["AWS CloudWatch Logs & Alarms (ap-south-1)"]
    end

    subgraph Visualization & Incident Response
        GRAF["Grafana Dashboards (:3000)"]
        ALRT["Prometheus Alertmanager & SRE Runbooks"]
        SNS["Amazon SNS Alerts"]
    end

    GW -->|W3C Traceparent| TXN
    TXN -->|Trace Spans| FRD
    FRD -->|Trace Spans| INV

    GW -.->|OTLP Traces, Metrics, Logs| OTEL
    TXN -.->|OTLP Traces, Metrics, Logs| OTEL
    FRD -.->|OTLP Traces, Metrics, Logs| OTEL

    OTEL -->|Scrape Endpoint (:8889)| PROM
    OTEL -->|JSON Logs & Metrics| CW
    PROM -->|PromQL| GRAF
    PROM -->|Alert Triggers| ALRT
    ALRT -->|PagerDuty / SNS| SNS
    CW -->|Metric Alarms| SNS
    UI <-->|/observability API| GW
```

---

## 3. Observability Pillars

### 3.1 Distributed Tracing & OpenTelemetry
- **Context Propagation**: Complies with the W3C Trace Context recommendation (`traceparent: 00-{trace_id}-{span_id}-01`).
- **Span Hierarchy**: Gateway HTTP server spans orchestrate child client/internal spans across transaction processing, feature generation, and fraud inference.
- **OTLP Pipeline**: Standard OpenTelemetry Collector buffers, batches, and exports telemetry to Prometheus and AWS X-Ray.

### 3.2 Prometheus Metrics & RED Signals
- **Rate**: `http_requests_total` partitioned by HTTP method, route, and status code.
- **Errors**: `transaction_processing_errors_total` and 5xx response ratios.
- **Duration**: `http_request_duration_seconds` and `fraud_scoring_latency_seconds` exposed as configurable histogram buckets.

### 3.3 Service Level Objectives (SLOs) & Error Budgets
- **Availability Target**: 99.9% over 30 days (0.1% allowable error budget).
- **Latency Target**: p95 fraud scoring latency < 200ms.
- **Multi-Window Burn-Rate Alerting**:
  - 1-hour burn rate > 14.4x triggers immediate SEV-2 warning.
  - 6-hour burn rate > 6.0x triggers proactive capacity review.

### 3.4 SRE Incident Runbooks & Automated Rollbacks
- Linked alerting rules provide one-click access to triage runbooks.
- Pre-scripted rollback commands using `kubectl rollout undo` and `argo rollouts abort` ensure deterministic MTTR reduction under 15 minutes.

