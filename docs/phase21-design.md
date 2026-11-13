# Phase 21 — Enterprise Operations Queue, Alert Ingestion, Tenant-Scoped Idempotency, SLA Management & Analyst Workflow

## 1. Executive Summary

Phase 21 introduces the operational command center into FinGuard AI: the **Enterprise Operations Queue, Real-Time Alert Ingestion & SLA Management Engine**.

While Phase 20 fusions multi-signal detection into a scored and prioritized fraud decision, financial institutions and enterprise fintechs require a robust operational workflow to process high-volume alerts across multiple business units or enterprise tenants. 

Phase 21 establishes:
- **FastAPI Alert Intake:** High-throughput alert ingestion accepting inputs from upstream decision engines or streaming fraud triggers.
- **Tenant-Scoped Idempotency:** Multi-tenant deduplication preventing duplicate case creation on network retries while preserving cross-tenant tenant isolation.
- **Priority-Driven SLA Management:** Deterministic SLA deadlines tied to priority tiers (`P0`, `P1`, `P2`, `P3`) with automated breach detection and countdown tracking.
- **Case Routing & Analyst Workflow:** Comprehensive assignment, investigation notes, state transitions (`OPEN` $\rightarrow$ `IN_REVIEW` $\rightarrow$ `ESCALATED` $\rightarrow$ `RESOLVED`), and tamper-evident activity timelines.
- **Operations Monitoring:** Queue health, SLA breach rates, impending deadline warnings, and analyst workload distributions.
- **Production DynamoDB Foundation:** Terraform infrastructure defining AWS DynamoDB tables with secondary indexes optimized for urgent queue queries.

> [!IMPORTANT]
> **Advisory Standard & Operational Governance:**
> All priority tiers and SLA countdowns are operational triage mechanisms designed to prioritize investigator cognitive bandwidth. Case resolution and account interventions remain strictly governed by authorized fraud analysts.

---

## 2. Architecture & Operational Flow

```mermaid
flowchart TD
    subgraph Upstream Ingestion
        DE[Phase 20 Decision Engine]
        STREAM[Streaming Transaction Kinesis / Kafka]
        EXT[Third-Party Banking Webhooks]
        DE & STREAM & EXT --> INGEST[POST /alerts]
    end

    subgraph Deduplication & Tenant Isolation
        IDEMP{Tenant-Scoped<br/>Idempotency Key?}
        CACHE[(Idempotency Cache<br/>DynamoDB / In-Memory)]
        INGEST --> IDEMP
        IDEMP -- Duplicate Found --> RET_DUP[Return Existing Case ID & Status<br/>is_duplicate = true]
        IDEMP -- New Key --> CREATE_CASE[Instantiate OperationalCase<br/>Status: OPEN]
        CACHE <--> IDEMP
    end

    subgraph Priority & SLA Engine
        RISK_MAP[Priority Assignment: P0, P1, P2, P3]
        SLA_CALC[SLA Deadline Calculator<br/>P0: 30m | P1: 2h | P2: 8h | P3: 24h]
        CREATE_CASE --> RISK_MAP --> SLA_CALC
    end

    subgraph Operations Case Store
        STORE[(Operations Case Store<br/>DynamoDB Table)]
        SLA_CALC --> STORE
    end

    subgraph Analyst Workflow & Lifecycle
        QUEUE[GET /operations/queue<br/>Sorted by Urgency & SLA]
        ASSIGN[POST /cases/:id/assign<br/>Route to Analyst]
        REVIEW[POST /cases/:id/status<br/>OPEN -> IN_REVIEW]
        NOTE[POST /cases/:id/notes<br/>Log Evidence & Notes]
        ESC[POST /cases/:id/escalate<br/>Senior Review Escalation]
        RESOLVE[POST /cases/:id/resolve<br/>Confirmed Fraud / False Positive]
        STORE <--> QUEUE
        STORE <--> ASSIGN
        STORE <--> REVIEW
        STORE <--> NOTE
        STORE <--> ESC
        STORE <--> RESOLVE
    end

    subgraph Operations Metrics
        METRICS[GET /operations/metrics<br/>SLA Breach Rate | Workloads | Triage Volume]
        STORE --> METRICS
    end
```

---

## 3. Priority Tiers & SLA Deadlines

Every ingested alert is assigned a priority tier based on its composite risk score or explicit upstream severity. Deadlines are calculated from the ingestion timestamp ($t_{\text{ingest}}$):

| Priority Tier | Classification | SLA Window | Target Resolution Time | Action Required |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | Critical | **30 minutes** | $t_{\text{ingest}} + 30\text{m}$ | Immediate SOC dispatch; automated paging |
| **P1** | High | **2 hours** | $t_{\text{ingest}} + 120\text{m}$ | Rapid triage; phone/SMS step-up verification |
| **P2** | Medium | **8 hours** | $t_{\text{ingest}} + 480\text{m}$ | Standard queue review within shift |
| **P3** | Low | **24 hours** | $t_{\text{ingest}} + 1440\text{m}$ | Ambient review; batch reconciliation |

$$\text{SLA Breached} \iff (t_{\text{now}} > t_{\text{deadline}}) \land (\text{Status} \notin \{\text{RESOLVED}, \text{CLOSED}\})$$
$$\text{Impending Breach} \iff (t_{\text{deadline}} - t_{\text{now}} \le 30\text{m}) \land (\text{Status} \notin \{\text{RESOLVED}, \text{CLOSED}\})$$

---

## 4. Tenant-Scoped Idempotency

In multi-tenant banking platforms (e.g. enterprise SaaS, multi-subsidiary retail banking), alert payloads frequently contain duplicate transaction IDs across network retries. Crucially, two distinct tenants may legitimately generate overlapping transaction IDs.

FinGuard AI scopes idempotency tuples:

$$\text{Key}_{\text{idempotency}} = (\text{tenant\_id}, \text{idempotency\_key})$$

- **Duplicate Submission (Same Tenant):** Returns HTTP 201 with `is_duplicate: true` and the original `case_id`. No duplicate operational cases or alerts are spawned.
- **Cross-Tenant Collision (Different Tenant):** Independently creates a separate case for Tenant B, preserving strict tenant boundary isolation.

---

## 5. Analyst Workflow & Lifecycle API Reference

The service exposes high-throughput operational REST endpoints:

### Endpoints:
- `POST /alerts`: Ingests alert and generates operational case.
- `GET /alerts`: Lists operational cases with optional filtering by tenant, priority, status, and assigned analyst.
- `GET /cases/{case_id}`: Retrieves comprehensive case details, SLA status, notes, and activity timeline.
- `POST /cases/{case_id}/assign`: Assigns analyst to case and records assignment audit.
- `POST /cases/{case_id}/status`: Transitions state (`OPEN` $\rightarrow$ `IN_REVIEW` $\rightarrow$ `ESCALATED`).
- `POST /cases/{case_id}/notes`: Adds an investigation note to the immutable case timeline.
- `POST /cases/{case_id}/resolve`: Resolves case with disposition (`CONFIRMED_FRAUD`, `FALSE_POSITIVE`, `DISMISSED`).
- `POST /cases/{case_id}/escalate`: Escalates case to senior fraud investigator team.
- `GET /operations/metrics`: Aggregates real-time SLA breach rates, open counts, and analyst workload distribution.
- `GET /operations/queue`: Retrieves urgent pending queue ordered by nearest SLA deadline.
- `GET /operations/health`: Operational readiness health check.

### Example Workflow Execution:
```bash
# 1. Ingest Alert
curl -X POST http://127.0.0.1:8011/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-acme-bank",
    "transaction_id": "TXN-90812-BURST",
    "amount": 8500.0,
    "risk_score": 0.95,
    "source": "TEMPORAL_GRU_STREAM"
  }'

# Response provides: { "case_id": "CASE-XXXX", "priority": "P0", "sla_deadline": "..." }

# 2. Assign Analyst
curl -X POST http://127.0.0.1:8011/cases/CASE-XXXX/assign \
  -H "Content-Type: application/json" \
  -d '{"analyst_id": "sarah.connor@finguard.internal", "assigned_by": "supervisor.john"}'

# 3. Move Case to IN_REVIEW
curl -X POST http://127.0.0.1:8011/cases/CASE-XXXX/status \
  -H "Content-Type: application/json" \
  -d '{"status": "IN_REVIEW", "updated_by": "sarah.connor@finguard.internal"}'

# 4. Add Investigation Notes
curl -X POST http://127.0.0.1:8011/cases/CASE-XXXX/notes \
  -H "Content-Type: application/json" \
  -d '{"author": "sarah.connor@finguard.internal", "content": "Customer confirmed unapproved overseas transfer attempt."}'

# 5. Resolve Case
curl -X POST http://127.0.0.1:8011/cases/CASE-XXXX/resolve \
  -H "Content-Type: application/json" \
  -d '{"resolution": "CONFIRMED_FRAUD", "resolved_by": "sarah.connor@finguard.internal", "notes": "Account restricted."}'

# 6. Check Operations Metrics
curl -X GET http://127.0.0.1:8011/operations/metrics
```

---

## 6. AWS DynamoDB Infrastructure (Terraform)

Located in `infrastructure/terraform/phase21/`:
- **`finguard-operations-cases-${var.environment}`**:
  - Hash Key: `case_id` (String)
  - GSI `tenant-sla-index`: Partition Key `tenant_id`, Sort Key `sla_deadline` (Urgent queue sorting)
  - GSI `tenant-status-index`: Partition Key `tenant_id`, Sort Key `status`
  - GSI `analyst-workload-index`: Partition Key `assigned_to`, Sort Key `sla_deadline`
  - Server-Side Encryption (SSE-KMS) & Point-in-Time Recovery (PITR) enabled.
- **`finguard-alert-idempotency-${var.environment}`**:
  - Hash Key: `tenant_id` (String), Range Key: `idempotency_key` (String)
  - Automated Time-to-Live (TTL) on `expires_at` attribute to expire old deduplication keys.

---

## 7. Validation & Benchmark Results

| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_operations_health_endpoints` | Verifies `/operations/health` and `/alerts/health` return 200 OK | **PASSED** |
| `test_alert_ingestion_and_priority_mapping` | Verifies P0, P1, P2, P3 auto-assignment and SLA windows | **PASSED** |
| `test_tenant_scoped_idempotency` | Validates deduplication within tenant and independence across tenants | **PASSED** |
| `test_case_routing_and_assignment` | Verifies assignment updates case and activity history | **PASSED** |
| `test_case_status_lifecycle` | Validates OPEN -> IN_REVIEW -> ESCALATED state transitions | **PASSED** |
| `test_analyst_notes_workflow` | Verifies notes appended to case timeline and detail endpoint | **PASSED** |
| `test_case_resolution` | Verifies case resolution stamps resolution status and timestamp | **PASSED** |
| `test_operations_metrics_and_sla_tracking` | Validates priority breakdown, SLA breach rates, and workload metrics | **PASSED** |

**Summary: 8/8 Tests Passed (100% Success Rate)**

---

## 8. Production Limitations Notice

> [!NOTE]
> **Production Deployment Limitations:**
> The case store currently operates on an in-memory reference store for local testing and developer velocity. The Terraform configuration in `infrastructure/terraform/phase21/` defines the DynamoDB foundation, not the complete distributed AWS event pipeline. SQS / EventBridge asynchronous event buffers, Cognito user pool group mappings, durable DynamoDB document client persistence, and multi-region failover remain targeted for production cloud staging. The API is intended for authenticated local/staging networks and must not be exposed to the public internet without strict network firewalls and Cognito JWT authentication.

