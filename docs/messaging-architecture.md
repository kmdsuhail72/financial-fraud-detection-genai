# FinGuard AI — Messaging & Event Streaming Operations Runbook

## 1. Delivery Guarantees & Consumer Rules

> [!IMPORTANT]
> **At-Least-Once Delivery**: No distributed queue guarantees exactly-once physical delivery across network partitions. All FinGuard event consumers must enforce **tenant-scoped idempotency** before committing state mutations.

### Idempotency Consumer Pattern
```python
if idempotency_manager.is_duplicate(tenant_id, message_id):
    logger.info("Duplicate message %s suppressed", message_id)
    queue.delete_message(receipt_handle)
    return
# Process business transaction
...
idempotency_manager.record_processed(tenant_id, message_id)
queue.delete_message(receipt_handle)
```

---

## 2. Dead-Letter Queue (DLQ) Operational Runbook

### Quarantine Diagnosis Checklist
1. **Query DLQ Messages**:
   ```bash
   curl -X GET http://localhost:8000/api/v1/messaging/dlq/messages
   ```
2. **Review Failure Reasons**:
   - Schema validation failure (bad payload)
   - Downstream timeout (circuit breaker triggered)
   - Database constraint violation
3. **Controlled Replay to Active Queue**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/messaging/dlq/replay \
     -H "Content-Type: application/json" \
     -d '{"message_id": "msg-poison-01", "target_queue_key": "fraud"}'
   ```

---

## 3. Kafka Stream Operations

### Offset Rewind (Historical Replay)
To replay all transactions from the last 24 hours for a specific consumer group:
```python
kafka_adapter.rewind_offset(consumer_group="fraud-scoring-group", partition=0, target_offset=0)
```
The consumer group will re-ingest all partition events from offset 0, safely handled by the idempotent consumers.

---

## 4. Key Metrics & SRE Alerts

- `finguard_sqs_approximate_number_of_messages`: Alert if pending backlog > 10,000 for $> 5$ minutes.
- `finguard_sqs_approximate_number_of_messages_not_visible`: High in-flight indicates slow consumer processing or hanging threads.
- `finguard_dlq_message_count`: Alert on $> 0$ messages in DLQ (requires immediate engineering triage).
