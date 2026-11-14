# Phase 33 — Enterprise Microservices & Event-Driven Architecture

## 1. Overview
Phase 33 establishes an event-driven microservices architecture for FinGuard AI, introducing decoupled domain boundaries, transactional outbox consistency, bounded retries with Dead-Letter Queues (DLQ), distributed Saga orchestration with reverse-order compensation, idempotency safeguards, and correlation/causation distributed tracing.

---

## 2. Core Architecture & Patterns

```
[ Client / Channel Ingress ]
            │
            ▼
┌───────────────────────────────┐
│     Transaction Service       │
│  - Idempotency Check          │
│  - Local DB State Update      │
│  - Transactional Outbox Write │
└───────────────┬───────────────┘
                │
                │ (Atomic Outbox Flush)
                ▼
┌───────────────────────────────┐
│     EventBridge Event Bus     │ ──► [ Dead-Letter Queue (DLQ) ]
│  - Topic / Pattern Filtering  │     (After 3 Exhausted Retries)
│  - At-Least-Once Delivery     │
└───────────────┬───────────────┘
                │
                ├──► Fraud-Scoring Service (Evaluates risk signals)
                ├──► Ledger Service (Balances & settlements)
                └──► Notification Service (Alerts & audit events)
```

### 2.1 Transactional Outbox Pattern
Prevents dual-write inconsistencies between the local transaction database and the event messaging bus. Domain events are persisted with `status=PENDING` within the local transaction, then picked up and published asynchronously, guaranteeing at-least-once delivery.

### 2.2 Saga Orchestration & Reverse-Order Compensation
Multi-service distributed transactions avoid blocking two-phase commits (2PC) by using an orchestrator:
1. `AuthorizeHold` (Transaction Service)
2. `EvaluateFraudRisk` (Fraud-Scoring Service)
3. `SettleTransaction` (Ledger Service)
4. `SendNotification` (Notification Service)

If any forward step fails (e.g. high-risk fraud block or service timeout), the Saga enters `COMPENSATING` mode and executes compensating actions in **strict reverse order** of the successfully executed steps:
- `ledger.debit.reversed`
- `fraud.reservation.cancelled`
- `account.hold.released`

### 2.3 Dead-Letter Queue (DLQ)
Events failing consumption undergo up to 3 bounded retries. If failures persist, the event is diverted to the Dead-Letter Queue with complete failure context, allowing manual inspection and replay without stalling normal traffic.

---

## 3. Implemented API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/microservices/health` | Service boundaries, bus capabilities, and architecture patterns |
| POST | `/microservices/transactions` | Outbox-backed transaction initiation with Saga execution |
| POST | `/microservices/saga/execute` | Direct Saga execution with optional simulated step failure |
| GET | `/microservices/saga/{saga_id}` | Detailed Saga execution state and compensation logs |
| GET | `/microservices/sagas` | List all recorded Saga instances |
| GET | `/microservices/outbox` | Query outbox events filtered by PENDING, PUBLISHED, or FAILED |
| POST | `/microservices/outbox/flush` | Flush pending outbox records to Event Bus |
| GET | `/microservices/dlq` | List failed messages in Dead-Letter Queue |
| POST | `/microservices/dlq/replay/{dlq_id}` | Replay DLQ message |
| GET | `/microservices/events` | Audit event bus log with correlation and causation IDs |
| GET | `/microservices/metrics` | Operational metrics (events, sagas, outbox backlog, DLQ depth) |

---

## 4. Production Caveat & Notice
> [!NOTE]
> FinGuard AI uses an in-memory Event Bus, Outbox, and Saga coordinator for local validation and demonstration. Production deployments utilize AWS EventBridge, Amazon SQS with redrive DLQs, Amazon SNS for alerts, DynamoDB/RDS for persistent transactional outbox records, and AWS Step Functions for distributed Saga orchestration.
