"""
Unit and integration tests for Kinesis batch publisher and producer.
"""
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock
from streaming.config import KinesisStreamConfig
from streaming.batch_publisher import KinesisBatchPublisher
from streaming.dlq import FailedRecordQuarantine
from streaming.metrics import StreamingMetricsTracker
from streaming.producer import TransactionStreamProducer


def test_batch_publisher_all_success():
    mock_client = MagicMock()
    mock_client.put_records.return_value = {
        "FailedRecordCount": 0,
        "Records": [
            {"SequenceNumber": "seq-1", "ShardId": "shardId-000000000000"},
            {"SequenceNumber": "seq-2", "ShardId": "shardId-000000000000"},
        ]
    }

    config = KinesisStreamConfig(stream_name="test-stream", max_attempts=3)
    metrics = StreamingMetricsTracker()
    quarantine = FailedRecordQuarantine(dlq_path=tempfile.mktemp())

    publisher = KinesisBatchPublisher(mock_client, config, metrics, quarantine)

    records = [
        {"Data": b"txn1", "PartitionKey": "ACC-1", "_origin_id": "TXN-1"},
        {"Data": b"txn2", "PartitionKey": "ACC-2", "_origin_id": "TXN-2"}
    ]

    success, failed = publisher.publish_batch(records)
    assert success == 2
    assert failed == 0
    assert metrics.total_records == 2
    assert metrics.failed_records == 0


def test_batch_publisher_partial_failure_retry():
    mock_client = MagicMock()
    # First attempt: 1 success, 1 failure
    # Second attempt: remaining 1 succeeds
    mock_client.put_records.side_effect = [
        {
            "FailedRecordCount": 1,
            "Records": [
                {"SequenceNumber": "seq-1", "ShardId": "shardId-000000000000"},
                {"ErrorCode": "ProvisionedThroughputExceededException", "ErrorMessage": "Throttled"}
            ]
        },
        {
            "FailedRecordCount": 0,
            "Records": [
                {"SequenceNumber": "seq-2", "ShardId": "shardId-000000000000"}
            ]
        }
    ]

    config = KinesisStreamConfig(stream_name="test-stream", max_attempts=3, base_backoff_sec=0.01)
    metrics = StreamingMetricsTracker()
    quarantine = FailedRecordQuarantine(dlq_path=tempfile.mktemp())

    publisher = KinesisBatchPublisher(mock_client, config, metrics, quarantine)

    records = [
        {"Data": b"txn1", "PartitionKey": "ACC-1", "_origin_id": "TXN-1"},
        {"Data": b"txn2", "PartitionKey": "ACC-2", "_origin_id": "TXN-2"}
    ]

    success, failed = publisher.publish_batch(records)
    assert success == 2
    assert failed == 0
    assert mock_client.put_records.call_count == 2


def test_stream_producer_dry_run():
    temp_dir = tempfile.mkdtemp()
    try:
        sample_file = os.path.join(temp_dir, "sample.jsonl")
        txns = [
            {
                "transaction_id": f"TXN-20261112-{i:06d}",
                "account_id": "ACC-100045",
                "customer_id": "CUS-200045",
                "amount": 1000.0 * i,
                "currency": "INR",
                "channel": "MOBILE",
                "transaction_timestamp": "2026-11-12T10:00:00Z"
            }
            for i in range(1, 15)
        ]

        with open(sample_file, "w", encoding="utf-8") as f:
            for t in txns:
                f.write(json.dumps(t) + "\n")

        config = KinesisStreamConfig(
            stream_name="test-stream",
            batch_size=5,
            dlq_path=os.path.join(temp_dir, "dlq.jsonl")
        )

        producer = TransactionStreamProducer(config=config, dry_run=True)
        summary = producer.stream_jsonl_file(sample_file)

        assert summary["total_records"] == 14
        assert summary["successful_records"] == 14
        assert summary["failed_records"] == 0
        assert summary["total_batches"] == 3  # 5 + 5 + 4
    finally:
        shutil.rmtree(temp_dir)

