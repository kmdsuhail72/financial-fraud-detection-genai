"""
FinGuard AI — Phase 40 Test Suite: Enterprise Message Queues, SQS, SNS, EventBridge, Kafka & Streaming
Verifies:
1. Event envelope serialization and semver version checks
2. SNS topic fan-out across multiple consumer queues
3. SQS Standard vs FIFO deduplication and message ordering
4. Bounded retries and automatic quarantine into Dead-Letter Queue (DLQ)
5. Dead-letter queue inspection and controlled replay to active queue
6. Tenant-scoped idempotency duplicate message suppression
7. EventBridge content-based rule evaluation & routing
8. Kafka stream partitioning, consumer groups, and Terraform validation
"""

import json
from pathlib import Path
import pytest

from messaging.contracts import EventEnvelope
from messaging.dlq import DeadLetterQueue
from messaging.sqs import SQSQueueAdapter
from messaging.sns import SNSTopicAdapter
from messaging.eventbridge import EventBridgeBusAdapter
from messaging.kafka_adapter import KafkaStreamAdapter
from messaging.idempotency import MessageIdempotencyManager
from messaging.service import messaging_service


def test_event_envelope_serialization_and_version_checks():
    """1. Test versioned event envelope, semver major compatibility, and JSON serialization."""
    evt = EventEnvelope(
        event_type="transaction.scored",
        version="1.2.0",
        tenant_id="tenant-icici",
        producer="fraud-engine",
        payload={"score": 0.88, "decision": "FLAGGED"},
    )
    serialized = evt.serialize()
    assert isinstance(serialized, str)
    assert "transaction.scored" in serialized

    # Deserialize
    deserialized = EventEnvelope.deserialize(serialized)
    assert deserialized.event_id == evt.event_id
    assert deserialized.payload["decision"] == "FLAGGED"

    # Semver checks
    assert deserialized.get_major_version() == 1
    assert deserialized.is_compatible_with(expected_major=1)
    assert not deserialized.is_compatible_with(expected_major=2)


def test_sns_topic_fanout_to_multiple_queues():
    """2. Test SNS 1-to-N fan-out delivering independent message copies to all subscriber queues."""
    topic = SNSTopicAdapter(name="test-fanout-topic")
    q1 = SQSQueueAdapter(name="queue-fraud")
    q2 = SQSQueueAdapter(name="queue-audit")
    q3 = SQSQueueAdapter(name="queue-analytics")

    topic.subscribe_queue(q1)
    topic.subscribe_queue(q2)
    topic.subscribe_queue(q3)

    event = EventEnvelope(
        event_type="payment.initiated",
        version="1.0.0",
        payload={"amount": 1500.0, "currency": "INR"},
    )

    pub_res = topic.publish(event)
    assert pub_res["deliveries"] == 3
    assert q1.approximate_number_of_messages() == 1
    assert q2.approximate_number_of_messages() == 1
    assert q3.approximate_number_of_messages() == 1

    # Verify message content preserved in queue 1
    msgs = q1.receive_messages(max_number=1)
    assert len(msgs) == 1
    assert msgs[0].body["payload"]["amount"] == 1500.0


def test_sqs_standard_vs_fifo_deduplication():
    """3. Test SQS FIFO deduplication within 5-minute deduplication window vs Standard behavior."""
    fifo_queue = SQSQueueAdapter(name="test-ledger.fifo", is_fifo=True)
    std_queue = SQSQueueAdapter(name="test-std-queue", is_fifo=False)

    payload = {"account": "ACC-9988", "delta": -500}
    dedup_id = "idem-key-batch-001"

    # FIFO Queue: First delivery accepted, duplicate dropped silently
    m1 = fifo_queue.send_message(payload, message_group_id="ACC-9988", message_deduplication_id=dedup_id)
    m2 = fifo_queue.send_message(payload, message_group_id="ACC-9988", message_deduplication_id=dedup_id)
    assert m1 is not None
    assert m2 is None
    assert fifo_queue.approximate_number_of_messages() == 1

    # Standard Queue: Duplicate messages are both accepted (at-least-once)
    s1 = std_queue.send_message(payload)
    s2 = std_queue.send_message(payload)
    assert s1 is not None
    assert s2 is not None
    assert std_queue.approximate_number_of_messages() == 2


def test_sqs_retry_policy_and_redrive_to_dlq():
    """4. Test bounded receive count and automatic quarantine into Dead-Letter Queue."""
    dlq = DeadLetterQueue(name="test-dlq")
    queue = SQSQueueAdapter(name="worker-queue", max_receive_count=2, dlq=dlq)

    queue.send_message({"tx_data": "MALFORMED_JSON_PAYLOAD"})
    assert queue.approximate_number_of_messages() == 1

    # Receive 1: fails
    p1 = queue.receive_messages(max_number=1)
    assert len(p1) == 1
    assert p1[0].approximate_receive_count == 1
    queue.nack_message(p1[0].receipt_handle, failure_reason="Parser crash 1")

    # Receive 2: fails (reaches max_receive_count = 2)
    p2 = queue.receive_messages(max_number=1)
    assert len(p2) == 1
    assert p2[0].approximate_receive_count == 2
    queue.nack_message(p2[0].receipt_handle, failure_reason="Parser crash 2")

    # Queue should now be empty because message is redriven to DLQ
    assert queue.approximate_number_of_messages() == 0
    assert dlq.count() == 1

    quarantined = dlq.list_messages()[0]
    assert quarantined.original_queue == "worker-queue"
    assert "Parser crash 2" in quarantined.failure_reason


def test_dlq_inspection_and_controlled_replay():
    """5. Test DLQ inspection, message querying, and controlled replay back to target queue."""
    dlq = DeadLetterQueue(name="replay-dlq")
    queue = SQSQueueAdapter(name="recovered-queue", max_receive_count=3, dlq=dlq)

    # Manually quarantine message
    dlq_msg = dlq.store_failed_message(
        original_queue="recovered-queue",
        payload={"tx_id": "TX-POISON-01", "amount": 75000},
        failure_reason="Downstream dependency 504 Gateway Timeout",
        receive_count=3,
        message_id="msg-poison-01",
    )
    assert dlq.count() == 1
    assert dlq.get_message("msg-poison-01") is not None

    # Replay back to target queue
    success = dlq.replay_message("msg-poison-01", queue)
    assert success is True
    # Should be evicted from DLQ
    assert dlq.count() == 0
    # Should now be present in target queue
    assert queue.approximate_number_of_messages() == 1

    replayed = queue.receive_messages(max_number=1)[0]
    assert replayed.body["tx_id"] == "TX-POISON-01"
    assert replayed.approximate_receive_count == 1  # Receive count reset


def test_tenant_scoped_idempotency_duplicate_suppression():
    """6. Test tenant-scoped idempotency duplicate message suppression and cross-tenant isolation."""
    idem = MessageIdempotencyManager(ttl_seconds=3600)
    tenant_1 = "tenant-sbi"
    tenant_2 = "tenant-pnb"
    dedup_id = "msg-batch-990"

    # First check: not duplicate
    assert not idem.is_duplicate(tenant_1, dedup_id)
    idem.record_processed(tenant_1, dedup_id, {"status": "ACK"})

    # Duplicate check for same tenant: must be duplicate
    assert idem.is_duplicate(tenant_1, dedup_id)
    assert idem.get_result(tenant_1, dedup_id)["status"] == "ACK"

    # Check same dedup_id for different tenant: must NOT be duplicate (tenant isolation)
    assert not idem.is_duplicate(tenant_2, dedup_id)


def test_eventbridge_content_based_routing():
    """7. Test EventBridge content-based pattern matching and high-value event routing."""
    bus = EventBridgeBusAdapter(bus_name="compliance-bus")
    high_value_queue = SQSQueueAdapter(name="high-value-queue")
    standard_queue = SQSQueueAdapter(name="standard-queue")

    # Add rule for high value transactions >= 100,000
    bus.add_rule(
        name="HighValueRule",
        event_pattern={"detail": {"amount": [{"numeric": [">=", 100000]}]}},
        target_queue=high_value_queue,
    )

    ev_low = EventEnvelope(
        event_type="payment",
        payload={"amount": 45000, "currency": "INR"},
    )
    ev_high = EventEnvelope(
        event_type="payment",
        payload={"amount": 500000, "currency": "INR"},
    )

    bus.put_events([ev_low, ev_high])

    # Only ev_high matches the rule
    assert high_value_queue.approximate_number_of_messages() == 1
    msgs = high_value_queue.receive_messages(max_number=1)
    assert msgs[0].body["payload"]["amount"] == 500000


def test_kafka_partitioning_and_terraform_manifests():
    """8. Test Kafka key-based partitioning, consumer group offset rewind, and Terraform manifest validation."""
    kafka = KafkaStreamAdapter(topic="test.topic", num_partitions=3)

    # Keyed producing distributes records across partitions
    r1 = kafka.produce(key="cust-1", value={"v": 1})
    r2 = kafka.produce(key="cust-2", value={"v": 2})
    r3 = kafka.produce(key="cust-3", value={"v": 3})

    assert r1.topic == "test.topic"
    assert 0 <= r1.partition < 3

    # Consumer group consumes messages
    records = kafka.consume(consumer_group="scoring-group", max_records=10)
    assert len(records) == 3

    # Consuming again yields 0 (offsets are committed)
    records_again = kafka.consume(consumer_group="scoring-group", max_records=10)
    assert len(records_again) == 0

    # Rewind offset on partition where r1 landed
    assert kafka.rewind_offset(consumer_group="scoring-group", partition=r1.partition, target_offset=0)
    replayed = kafka.consume(consumer_group="scoring-group", max_records=10)
    assert len(replayed) >= 1

    # Validate Terraform Phase 40 files
    base_dir = Path(__file__).resolve().parent.parent.parent
    tf_main = base_dir / "infrastructure" / "terraform" / "phase40" / "main.tf"
    tf_vars = base_dir / "infrastructure" / "terraform" / "phase40" / "variables.tf"
    tf_outs = base_dir / "infrastructure" / "terraform" / "phase40" / "outputs.tf"

    assert tf_main.exists()
    assert tf_vars.exists()
    assert tf_outs.exists()

    content = tf_main.read_text(encoding="utf-8")
    assert "aws_sqs_queue" in content
    assert "aws_sns_topic" in content
    assert "aws_sns_topic_subscription" in content
    assert "aws_cloudwatch_event_bus" in content
    assert "aws_cloudwatch_event_rule" in content
    assert "redrive_policy" in content
    assert "fifo_queue" in content
