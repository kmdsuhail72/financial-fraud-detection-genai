"""
Phase 40: Unified Messaging & Event Streaming Service
Orchestrates SQS Queues, SNS Fan-Out, EventBridge Content Routing, Kafka Streams, and DLQ Replay.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from messaging.contracts import EventEnvelope
from messaging.dlq import DeadLetterQueue
from messaging.sqs import SQSQueueAdapter, SQSMessage
from messaging.sns import SNSTopicAdapter
from messaging.eventbridge import EventBridgeBusAdapter
from messaging.kafka_adapter import KafkaStreamAdapter
from messaging.idempotency import MessageIdempotencyManager


class MessagingService:
    """Central orchestration service for FinGuard enterprise event streaming."""

    def __init__(self):
        # 1. Quarantining & Dead-Letter Queue
        self.dlq = DeadLetterQueue(name="finguard-main-dlq")

        # 2. SQS Queues (Standard & FIFO)
        self.fraud_queue = SQSQueueAdapter(
            name="finguard-fraud-scoring-queue",
            is_fifo=False,
            max_receive_count=3,
            dlq=self.dlq,
        )
        self.notifications_queue = SQSQueueAdapter(
            name="finguard-notifications-queue",
            is_fifo=False,
            max_receive_count=3,
            dlq=self.dlq,
        )
        self.compliance_queue = SQSQueueAdapter(
            name="finguard-high-value-compliance-queue",
            is_fifo=False,
            max_receive_count=3,
            dlq=self.dlq,
        )
        self.audit_fifo_queue = SQSQueueAdapter(
            name="finguard-audit-ledger.fifo",
            is_fifo=True,
            max_receive_count=3,
            dlq=self.dlq,
        )

        self.queues: Dict[str, SQSQueueAdapter] = {
            "fraud": self.fraud_queue,
            "notifications": self.notifications_queue,
            "compliance": self.compliance_queue,
            "audit_fifo": self.audit_fifo_queue,
        }

        # 3. Amazon SNS Topic (1-to-N Fan-Out)
        self.sns_topic = SNSTopicAdapter(name="finguard-transactions-fanout")
        # Fan out to fraud scoring and notifications queues
        self.sns_topic.subscribe_queue(self.fraud_queue)
        self.sns_topic.subscribe_queue(self.notifications_queue)

        # 4. Amazon EventBridge Custom Bus & Content-Based Routing
        self.eventbridge = EventBridgeBusAdapter(bus_name="finguard-enterprise-bus")
        # Rule: Route High-Value Transactions (amount >= 100,000) to Compliance Queue
        self.eventbridge.add_rule(
            name="HighValueTransactionRule",
            event_pattern={
                "detail": {
                    "amount": [{"numeric": [">=", 100000]}],
                }
            },
            target_queue=self.compliance_queue,
        )

        # 5. Apache Kafka / Amazon MSK Partitioned Stream
        self.kafka = KafkaStreamAdapter(topic="finguard.transactions.stream", num_partitions=3)

        # 6. Tenant-Scoped Idempotency Layer
        self.idempotency = MessageIdempotencyManager(ttl_seconds=86400)

        # Metrics Counters
        self.total_published = 0
        self.total_processed = 0
        self.total_retried = 0

    def publish_transaction_event(self, event: EventEnvelope) -> Dict[str, Any]:
        """
        End-to-End Event Ingestion:
        1. Checks tenant idempotency
        2. Fans out via SNS to Fraud & Notification Queues
        3. Evaluates EventBridge content routing rules
        4. Produces into partitioned Kafka Stream
        """
        dedup_id = event.event_id
        if self.idempotency.is_duplicate(event.tenant_id, dedup_id):
            return {
                "status": "DUPLICATE_SUPPRESSED",
                "event_id": event.event_id,
                "tenant_id": event.tenant_id,
                "message": "Duplicate event detected and suppressed by tenant idempotency manager",
            }

        # 1. SNS Fanout
        sns_res = self.sns_topic.publish(event)

        # 2. EventBridge Routing
        eb_res = self.eventbridge.put_events([event])

        # 3. Kafka Stream Partitioning
        partition_key = event.payload.get("customer_id") or event.tenant_id
        kafka_rec = self.kafka.produce(key=partition_key, value=event.model_dump())

        # 4. Record Idempotency
        self.idempotency.record_processed(
            event.tenant_id,
            dedup_id,
            result={"status": "PUBLISHED", "timestamp": event.timestamp},
        )
        self.total_published += 1

        return {
            "status": "SUCCESS",
            "event_id": event.event_id,
            "version": event.version,
            "sns": sns_res,
            "eventbridge": eb_res,
            "kafka": {
                "topic": kafka_rec.topic,
                "partition": kafka_rec.partition,
                "offset": kafka_rec.offset,
            },
        }

    def process_queue_message(
        self,
        queue_key: str,
        simulate_failure: bool = False,
        failure_reason: str = "Simulated downstream scoring timeout",
    ) -> Dict[str, Any]:
        """
        Consume and process next message from an SQS queue.
        Supports simulating worker failure to demonstrate redrive to DLQ.
        """
        queue = self.queues.get(queue_key)
        if not queue:
            return {"status": "ERROR", "message": f"Queue '{queue_key}' not found"}

        messages = queue.receive_messages(max_number=1, visibility_timeout=30)
        if not messages:
            return {"status": "NO_MESSAGES", "queue": queue.name}

        msg = messages[0]

        if simulate_failure:
            self.total_retried += 1
            queue.nack_message(msg.receipt_handle, failure_reason=failure_reason)
            return {
                "status": "FAILED_AND_NACKED",
                "message_id": msg.message_id,
                "receive_count": msg.approximate_receive_count,
                "max_retries": queue.max_receive_count,
                "quarantined_to_dlq": bool(msg.approximate_receive_count >= queue.max_receive_count),
                "reason": failure_reason,
            }

        # Successful processing
        queue.delete_message(msg.receipt_handle)
        self.total_processed += 1
        return {
            "status": "PROCESSED",
            "message_id": msg.message_id,
            "receive_count": msg.approximate_receive_count,
            "body": msg.body,
        }

    def replay_from_dlq(self, message_id: str, target_queue_key: str) -> bool:
        """Replay a quarantined message from DLQ into an active queue."""
        queue = self.queues.get(target_queue_key)
        if not queue:
            return False
        return self.dlq.replay_message(message_id, queue)

    def get_metrics(self) -> Dict[str, Any]:
        """Return comprehensive operational metrics across queues, bus, and Kafka."""
        return {
            "total_published": self.total_published,
            "total_processed": self.total_processed,
            "total_retried": self.total_retried,
            "dlq_count": self.dlq.count(),
            "queues": {
                k: {
                    "pending": q.approximate_number_of_messages(),
                    "in_flight": q.approximate_number_of_messages_not_visible(),
                    "is_fifo": q.is_fifo,
                }
                for k, q in self.queues.items()
            },
            "sns": {
                "topic_name": self.sns_topic.name,
                "subscribers": self.sns_topic.get_subscriber_count(),
                "published_count": self.sns_topic.published_count,
            },
            "eventbridge": {
                "bus_name": self.eventbridge.bus_name,
                "rules_count": self.eventbridge.get_rule_count(),
                "routed_count": self.eventbridge.routed_count,
            },
            "kafka": self.kafka.get_metrics(),
        }

    def get_health(self) -> Dict[str, Any]:
        """Return health status of the messaging layer."""
        return {
            "status": "healthy",
            "tier": "enterprise_messaging_and_streaming",
            "adapters": {
                "sqs": "active",
                "sns": "active",
                "eventbridge": "active",
                "kafka": "active",
                "dlq": "active",
                "idempotency": "active",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global singleton instance
messaging_service = MessagingService()
