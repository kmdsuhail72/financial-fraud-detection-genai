# Phase 40 — Enterprise Message Queues, Amazon SQS, SNS, EventBridge, Kafka & Advanced Event Streaming

## 1. Executive Summary

Phase 40 establishes a highly scalable, asynchronous, distributed messaging and event-streaming backbone for **FinGuard AI**. Built around **at-least-once** delivery guarantees and strictly idempotent consumer patterns, the architecture reliably delivers financial transaction events, fans out copies to downstream scoring and alerting systems, executes content-based routing via Amazon EventBridge, partitions high-throughput telemetry across Kafka logs, and isolates poison messages inside Dead-Letter Queues (DLQ) with controlled manual and automated replay.

---

## 2. Event Processing Architecture

```
                                +-----------------------------+
                                | Transaction Ingestion Layer |
                                +--------------+--------------+
                                               |
                   +---------------------------+---------------------------+
                   |                                                       |
                   v                                                       v
        +--------------------+                                  +--------------------+
        |   Amazon SNS       |                                  | Amazon EventBridge |
        | (1-to-N Fan-Out)   |                                  | (Content Routing)  |
        +----+----------+----+                                  +---------+----------+
             |          |                                                 |
             |          |                                                 | (amount >= 100k)
             v          v                                                 v
    +-------------+ +-------------+                             +--------------------+
    | SQS Queue   | | SQS Queue   |                             | SQS High-Value     |
    | Fraud Score | | Alerts/SMS  |                             | Compliance Queue   |
    +------+------+ +------+------+                             +---------+----------+
           |               |                                              |
           +---------------+----------------------------------------------+
                                           |
                                  (At-Least-Once Pull)
                                           v
                        +-------------------------------------+
                        |     Idempotent Event Consumers      |
                        | (Tenant-Scoped Deduplication Engine)|
                        +------------------+------------------+
                                           |
                                 (Max Retries Exceeded)
                                           v
                        +-------------------------------------+
                        |       Dead-Letter Queue (DLQ)       |
                        |   (Quarantine & Controlled Replay)  |
                        +-------------------------------------+
```

---

## 3. Core Enterprise Messaging Primitives

### 3.1. Versioned Event Envelope
All inter-service events adhere to a standardized JSON schema contract with semantic versioning:
- **Major Version Compatibility**: Enforces backward compatibility (`is_compatible_with(expected_major=1)`).
- **Distributed Traceability**: Carries `correlation_id` and `causation_id` across microservice boundaries.
- **Multi-Tenant Isolation**: Scoped by `tenant_id`.

### 3.2. Amazon SQS Standard vs FIFO Queues
- **SQS Standard**: Unbounded throughput, at-least-once delivery, best-effort message ordering.
- **SQS FIFO**: Strict ordered delivery per `message_group_id`, with automatic content-based deduplication window of 5 minutes ($300\text{s}$) via `message_deduplication_id`.

### 3.3. Amazon SNS Topic Fan-Out
- Subscribes multiple independent consumer queues (Fraud Engine, Notifications Service) to a single publishing point (`finguard-transactions-fanout`), ensuring loose coupling.

### 3.4. Amazon EventBridge Content-Based Routing
- Evaluates JSON event detail payloads in real time. Transactions with $\ge 100,000\text{ INR}$ are automatically routed to a dedicated compliance audit queue without code changes in the publisher.

### 3.5. Apache Kafka / Amazon MSK Partitioning
- Partitions streaming events by customer or tenant key:
  $$\text{Partition ID} = \text{MD5}(\text{Key}) \pmod{\text{NumPartitions}}$$
- Consumer groups maintain independent committed offsets and support historical event replay via offset rewind.

### 3.6. Bounded Retries & DLQ Replay
- When a consumer repeatedly fails on a poisoned message, the queue tracks `approximate_receive_count`.
- Upon exceeding `max_receive_count = 3`, the message is evicted from the active queue and quarantined into the Dead-Letter Queue.
- Operators can inspect the failure reason and trigger a controlled replay back into the active processing queue.

---

## 4. Verification & Testing

- **Demo Script**: Validated via `python scripts/demo.py` (6/6 scenarios passed).
- **Test Suite**: 8/8 comprehensive pytest test cases covering schema versioning, SNS fan-out, FIFO deduplication, DLQ redrive, controlled replay, tenant idempotency, EventBridge content matching, and Kafka stream partitioning.
