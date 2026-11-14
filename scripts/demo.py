#!/usr/bin/env python3
"""
Phase 40: Enterprise Message Queues & Streaming Demo Script
Demonstrates end-to-end event lifecycle:
1. Versioned Event Envelope serialization & schema check
2. SNS 1-to-N fan-out to Fraud Scoring & Notifications queues
3. EventBridge content-based routing (high-value threshold)
4. SQS FIFO deduplication & message ordering
5. Poison pill retry loop, quarantine to Dead-Letter Queue (DLQ)
6. Controlled DLQ inspection and replay back to primary queue
7. Tenant-scoped idempotency duplicate prevention
"""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from messaging.contracts import EventEnvelope
from messaging.service import messaging_service


def run_messaging_demo():
    print("========================================================================")
    print(" FinGuard AI — Phase 40 Enterprise Message Queues & Event Streaming Demo")
    print("========================================================================")

    # 1. Event Envelope Creation
    print("\n[1/6] Creating versioned event envelope...")
    event = EventEnvelope(
        event_type="transaction.created",
        version="1.0.0",
        tenant_id="tenant-axis-bank",
        producer="payment-gateway",
        payload={
            "transaction_id": "TX-MESSAGING-DEMO-01",
            "customer_id": "CUST-9021",
            "amount": 250000.0,
            "currency": "INR",
            "rail": "RTGS",
        },
    )
    print(f"  ✓ Envelope generated: ID={event.event_id}, Version={event.version}")
    assert event.is_compatible_with(expected_major=1)

    # 2. Publish & Fan-Out
    print("\n[2/6] Publishing event through SNS Fan-Out & EventBridge...")
    pub_res = messaging_service.publish_transaction_event(event)
    print(f"  ✓ Status: {pub_res['status']}")
    print(f"  ✓ SNS Deliveries: {pub_res['sns']['deliveries']} subscribers")
    print(f"  ✓ Kafka Partition: {pub_res['kafka']['partition']} (Offset {pub_res['kafka']['offset']})")
    print(f"  ✓ EventBridge Matched Rules: {pub_res['eventbridge']['MatchedRulesCount']}")

    # 3. Queue Inspection
    print("\n[3/6] Inspecting consumer queues...")
    fraud_msgs = messaging_service.fraud_queue.receive_messages(max_number=1)
    notif_msgs = messaging_service.notifications_queue.receive_messages(max_number=1)
    comp_msgs = messaging_service.compliance_queue.receive_messages(max_number=1)

    assert len(fraud_msgs) == 1, "Fraud queue should receive fanned-out copy"
    assert len(notif_msgs) == 1, "Notifications queue should receive fanned-out copy"
    assert len(comp_msgs) == 1, "Compliance queue should receive high-value routed copy"
    print(f"  ✓ Fraud Queue: Received msg {fraud_msgs[0].message_id}")
    print(f"  ✓ Notifications Queue: Received msg {notif_msgs[0].message_id}")
    print(f"  ✓ High-Value Compliance Queue: Received msg {comp_msgs[0].message_id}")

    # Acknowledge messages
    messaging_service.fraud_queue.delete_message(fraud_msgs[0].receipt_handle)
    messaging_service.notifications_queue.delete_message(notif_msgs[0].receipt_handle)
    messaging_service.compliance_queue.delete_message(comp_msgs[0].receipt_handle)

    # 4. SQS FIFO Deduplication & Ordering
    print("\n[4/6] Testing SQS FIFO deduplication & group ordering...")
    fifo = messaging_service.audit_fifo_queue
    fifo.purge()
    m1 = fifo.send_message({"action": "DEBIT"}, message_group_id="ACC-1", message_deduplication_id="DEDUP-001")
    # Duplicate with same deduplication ID must be silently dropped
    m2 = fifo.send_message({"action": "DEBIT"}, message_group_id="ACC-1", message_deduplication_id="DEDUP-001")
    assert m1 is not None
    assert m2 is None, "FIFO queue must suppress duplicate message_deduplication_id"
    print("  ✓ FIFO Deduplication: 1st accepted, duplicate silently suppressed.")

    # 5. Poison Pill, Redrive to DLQ & Replay
    print("\n[5/6] Testing Retry exhaustion, DLQ quarantine, and controlled replay...")
    test_queue = messaging_service.fraud_queue
    test_queue.purge()
    messaging_service.dlq.purge()

    test_queue.send_message({"corrupted_tx": "BAD_DATA_POISON_PILL"})

    # Fail 3 times (max_receive_count = 3)
    for attempt in range(1, 4):
        poll = test_queue.receive_messages(max_number=1)
        assert len(poll) == 1
        msg = poll[0]
        test_queue.nack_message(msg.receipt_handle, failure_reason=f"Attempt {attempt} failed")

    # 4th receive should quarantine directly into DLQ
    poll_after = test_queue.receive_messages(max_number=1)
    assert len(poll_after) == 0, "Poison message should be evicted from primary queue"
    assert messaging_service.dlq.count() == 1, "DLQ should capture quarantined message"

    dlq_msg = messaging_service.dlq.list_messages()[0]
    print(f"  ✓ Poison pill quarantined in DLQ: {dlq_msg.message_id} (Reason: {dlq_msg.failure_reason})")

    # Controlled Replay
    replay_success = messaging_service.replay_from_dlq(dlq_msg.message_id, "fraud")
    assert replay_success
    assert messaging_service.dlq.count() == 0
    replayed_msgs = test_queue.receive_messages(max_number=1)
    assert len(replayed_msgs) == 1
    print(f"  ✓ Controlled replay successful: Message restored to {test_queue.name}")
    test_queue.delete_message(replayed_msgs[0].receipt_handle)

    # 6. Tenant-Scoped Idempotency
    print("\n[6/6] Testing Tenant-Scoped Idempotency...")
    duplicate_res = messaging_service.publish_transaction_event(event)
    assert duplicate_res["status"] == "DUPLICATE_SUPPRESSED"
    print(f"  ✓ Duplicate event suppressed for tenant: {duplicate_res['tenant_id']}")

    print("\n========================================================================")
    print(" All Phase 40 Messaging & Event Streaming Scenarios Verified! (6/6)     ")
    print("========================================================================")


if __name__ == "__main__":
    run_messaging_demo()
