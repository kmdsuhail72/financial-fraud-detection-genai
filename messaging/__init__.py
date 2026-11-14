"""
Phase 40: Enterprise Message Queues, Amazon SQS, SNS, EventBridge, Kafka & Streaming
"""

from messaging.contracts import EventEnvelope
from messaging.dlq import DeadLetterMessage, DeadLetterQueue
from messaging.sqs import SQSMessage, SQSQueueAdapter
from messaging.sns import SNSTopicAdapter, SNSSubscription
from messaging.eventbridge import EventBridgeBusAdapter, EventBridgeRule
from messaging.kafka_adapter import KafkaRecord, KafkaStreamAdapter
from messaging.idempotency import MessageIdempotencyManager
from messaging.service import MessagingService, messaging_service

__all__ = [
    "EventEnvelope",
    "DeadLetterMessage",
    "DeadLetterQueue",
    "SQSMessage",
    "SQSQueueAdapter",
    "SNSTopicAdapter",
    "SNSSubscription",
    "EventBridgeBusAdapter",
    "EventBridgeRule",
    "KafkaRecord",
    "KafkaStreamAdapter",
    "MessageIdempotencyManager",
    "MessagingService",
    "messaging_service",
]
