"""
Phase 40: Enterprise Message Queues & Event Streaming API Router
Mounted at /messaging and /api/v1/messaging
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from messaging.contracts import EventEnvelope
from messaging.service import messaging_service

messaging_router = APIRouter(prefix="/messaging", tags=["Enterprise Message Queues & Event Streaming"])


class TransactionPublishRequest(BaseModel):
    """Payload for publishing a transaction event."""
    transaction_id: str = Field(..., description="Unique transaction ID")
    tenant_id: str = Field(default="tenant-hdfc-01", description="Owning tenant")
    customer_id: str = Field(default="CUST-1001", description="Customer ID")
    amount: float = Field(default=50000.0, description="Transaction amount in INR")
    currency: str = Field(default="INR", description="Currency code")
    payment_rail: str = Field(default="UPI", description="Payment rail (UPI, IMPS, RTGS)")
    risk_score: float = Field(default=0.15, description="Initial risk score")


class ReplayDLQRequest(BaseModel):
    """Payload to replay a dead-letter message back to active queue."""
    message_id: str
    target_queue_key: str = Field(default="fraud", description="Target queue (fraud, notifications, compliance)")


@messaging_router.get("/health")
def get_messaging_health() -> Dict[str, Any]:
    """Return health status of messaging queues, brokers, and event streams."""
    return messaging_service.get_health()


@messaging_router.get("/metrics")
def get_messaging_metrics() -> Dict[str, Any]:
    """Return operational metrics across SQS queues, SNS fanout, EventBridge, and Kafka."""
    return messaging_service.get_metrics()


@messaging_router.post("/publish/transaction")
def publish_transaction_event(req: TransactionPublishRequest) -> Dict[str, Any]:
    """
    Publish transaction event across the enterprise event streaming topology:
    - SNS Fanout (Fraud Scoring Queue + Notifications Queue)
    - EventBridge Content-Based Routing (High Value Queue if amount >= 100,000)
    - Apache Kafka / Amazon MSK Partitioned Stream
    - Tenant Idempotency Duplicate Detection
    """
    envelope = EventEnvelope(
        event_type="transaction.created",
        version="1.0.0",
        tenant_id=req.tenant_id,
        producer="finguard-gateway",
        payload={
            "transaction_id": req.transaction_id,
            "customer_id": req.customer_id,
            "amount": req.amount,
            "currency": req.currency,
            "payment_rail": req.payment_rail,
            "risk_score": req.risk_score,
        },
    )

    return messaging_service.publish_transaction_event(envelope)


@messaging_router.get("/queues/{queue_key}/messages")
def poll_queue_messages(queue_key: str, max_number: int = Query(5, ge=1, le=10)) -> List[Dict[str, Any]]:
    """Poll pending messages from an SQS queue."""
    queue = messaging_service.queues.get(queue_key)
    if not queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Queue key '{queue_key}' not found. Available: {list(messaging_service.queues.keys())}",
        )
    messages = queue.receive_messages(max_number=max_number)
    return [msg.model_dump() for msg in messages]


@messaging_router.post("/queues/{queue_key}/process")
def process_queue_message(
    queue_key: str,
    simulate_failure: bool = Query(False, description="Simulate processing failure to test DLQ redrive"),
) -> Dict[str, Any]:
    """Process next message from queue, with optional failure simulation."""
    res = messaging_service.process_queue_message(queue_key, simulate_failure=simulate_failure)
    return res


@messaging_router.get("/dlq/messages")
def list_dlq_messages() -> List[Dict[str, Any]]:
    """List quarantined messages in the Dead-Letter Queue."""
    messages = messaging_service.dlq.list_messages()
    return [msg.model_dump() for msg in messages]


@messaging_router.post("/dlq/replay")
def replay_dlq_message(req: ReplayDLQRequest) -> Dict[str, Any]:
    """Replay a message from DLQ back into the active queue."""
    success = messaging_service.replay_from_dlq(req.message_id, req.target_queue_key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to replay message '{req.message_id}' to queue '{req.target_queue_key}'",
        )
    return {
        "status": "REPLAYED",
        "message_id": req.message_id,
        "target_queue": req.target_queue_key,
    }


@messaging_router.get("/kafka/records")
def consume_kafka_records(
    consumer_group: str = Query("fraud-scoring-group"),
    max_records: int = Query(10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Consume unread records from Kafka topic across all partitions."""
    records = messaging_service.kafka.consume(consumer_group=consumer_group, max_records=max_records)
    return [r.model_dump() for r in records]
