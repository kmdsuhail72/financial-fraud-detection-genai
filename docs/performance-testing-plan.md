# FinGuard AI — Performance, Load, Stress, Spike & Soak Testing Plan

This document details the performance testing methodology, workload modeling, and automated quality gates for FinGuard AI microservices.

---

## 1. Performance Testing Types & Workload Profiles

| Test Type | Objective | Duration | Target Concurrency | Target Throughput | Success Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Load Test** | Validate system behavior under expected normal peak load. | 30 mins | 100 users | 100 – 500 RPS | p95 latency < 150ms, Error rate < 0.05% |
| **Stress Test** | Identify breaking points and system behavior beyond peak. | 60 mins | 500 users | 1,000 – 2,500 RPS | Graceful degradation, 0 memory leaks |
| **Spike Test** | Measure resilience to sudden traffic bursts (e.g. flash sales). | 10 mins | 0 -> 1,000 -> 50 users | Instant 3,000 RPS burst | HPA scales up < 45s, Error rate < 0.5% |
| **Soak Test** | Verify stability, memory retention, and GC behavior over time. | 12 hours | 50 users (sustained) | 250 RPS continuous | Flat memory consumption, 0 connection leaks |

---

## 2. Capacity Calculation Standard

FinGuard utilizes the industry-standard capacity formula:
$$Replicas = \lceil \frac{Peak\_RPS \times (1 + Headroom)}{Pod\_Capacity\_RPS \times (Target\_Utilization)} \rceil$$

### Baseline Example (100 RPS Workload):
- **Expected Peak Traffic:** 100 RPS
- **Headroom Buffer:** 30% ($100 \times 1.30 = 130$ RPS total)
- **Per-Pod Assumed Capacity:** 25 RPS
- **Target Utilization:** 65% ($25 \times 0.65 = 16.25$ effective RPS/pod)
- **Calculation:** $\lceil \frac{130}{16.25} \rceil = 8$ pod replicas.

---

## 3. Test Execution Commands

### Running Locust Headless in CI/CD:
```bash
locust -f locust/locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --host http://127.0.0.1:8000 \
  --html artifacts/locust-report.html
```

### Running the API Benchmark Tool:
```bash
python scripts/benchmark_api.py \
  --url http://127.0.0.1:8000/health \
  --requests 200 \
  --json
```

### Running Apache JMeter via CLI:
```bash
jmeter -n \
  -t jmeter/finguard_performance_plan.jmx \
  -l artifacts/jmeter_results.jtl \
  -e -o artifacts/jmeter_dashboard/
```

---

## 4. Performance Quality Gates & Regression Criteria

A pull request or deployment is automatically blocked in the CI/CD pipeline if:
1. **p95 Latency Regression:** Fraud scoring p95 latency increases by $> 15\%$ compared to baseline.
2. **Error Rate Spike:** HTTP 5xx errors exceed $0.1\%$ under load.
3. **Throughput Degradation:** Maximum sustainable throughput drops by $> 10\%$.
