# FinGuard AI — SRE Incident Triage, Alerting & Rollback Runbook

This runbook establishes Standard Operating Procedures (SOPs) for the FinGuard AI Site Reliability Engineering (SRE) and Operations teams.

---

## 1. Incident Severity Definitions & Response Times

| Severity | Definition | Target MTTA | Target MTTR | Escalation Lead |
| :--- | :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Core API down, 5xx error rate > 1%, data loss risk, or complete fraud scoring failure. | < 5 mins | < 30 mins | Principal SRE + Engineering VP |
| **SEV-2 (High)** | p95 latency breach (> 200ms), single canary instance failure, error budget fast burn. | < 15 mins | < 2 hours | Primary SRE on-call |
| **SEV-3 (Medium)** | Non-blocking metric ingestion failure, minor UI lag, single pod restart. | < 1 hour | < 8 hours | Secondary on-call |

---

## 2. High 5xx Error Rate Triage (`High5xxErrorRate`)

### Symptoms
- Prometheus alert `High5xxErrorRate` firing.
- CloudWatch metric alarm `FinGuard-production-High5xxErrorRate` in `ALARM` state.
- Influx of HTTP 500/502/503 responses returned to banking upstream clients.

### Step-by-Step Triage Workflow
1. **Verify Live Pod Status**:
   ```bash
   kubectl get pods -n finguard -l app.kubernetes.io/part-of=finguard-ai
   kubectl describe pods -n finguard | grep -A 5 -B 5 "Exit Code"
   ```
2. **Inspect OpenTelemetry Trace Errors**:
   - Navigate to the SRE Console at `/observability-sre` -> **Distributed Tracing**.
   - Filter by status `ERROR` to identify failing microservice and root span.
3. **Query CloudWatch Logs**:
   - Log group: `/aws/eks/finguard/services`
   - Filter query:
     ```
     fields @timestamp, service, message, exception
     | filter level = "ERROR" or status >= 500
     | sort @timestamp desc
     | limit 50
     ```
4. **Automated Mitigation**:
   - If error rate spike coincides with a new deployment, initiate immediate Argo Rollout rollback:
     ```bash
     kubectl argo rollouts abort transaction-service -n finguard
     kubectl rollout undo deployment/transaction-service -n finguard
     ```

---

## 3. High Fraud Scoring Latency Triage (`HighFraudScoringLatencyP95`)

### Symptoms
- `HighFraudScoringLatencyP95` alert firing (> 200ms p95 latency).
- Real-time payment evaluation queues backing up.

### Step-by-Step Triage Workflow
1. **Inspect ML Model Inference Times**:
   - Query histogram quantile: `histogram_quantile(0.95, sum(rate(fraud_scoring_latency_seconds_bucket[5m])) by (le))`
   - Verify if latency is originating from feature engineering, XGBoost/LightGBM model inference, or Bedrock GenAI assistant.
2. **Scale Pod Replicas**:
   - Check HPA status:
     ```bash
     kubectl get hpa -n finguard
     kubectl scale deployment fraud-service -n finguard --replicas=8
     ```
3. **Verify Downstream Caching**:
   - Confirm Redis feature cache hit ratio > 92%.
   - In case of cache outage, switch fallback predictor to lightweight offline model.

---

## 4. Error Budget Fast Burn (`ErrorBudgetFastBurn`)

### Symptoms
- 1-hour error budget burn rate exceeds 14.4x (2% budget consumed in 1 hour).
- 30-day availability SLO is at severe risk of breach.

### Mitigation Policy
1. **Freeze Non-Critical Deployments**: Halve continuous deployments until burn rate drops below 1.0x.
2. **Reroute Non-Critical Traffic**: Shed low-priority batch asynchronous queries.
3. **Engage Post-Incident Review**: Record incident timeline, root cause, and corrective action items in the post-mortem repository.
