"""
Unit tests for Kinesis Shard Consumer and Checkpoint Manager.
"""
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock
from streaming.config import KinesisStreamConfig
from streaming.consumer import KinesisShardConsumer
from streaming.checkpoint import ShardCheckpointManager


def test_checkpoint_persistence():
    temp_dir = tempfile.mkdtemp()
    cp_file = os.path.join(temp_dir, "checkpoint.json")

    try:
        manager = ShardCheckpointManager(checkpoint_path=cp_file)
        assert manager.get_checkpoint("shardId-000000000000") is None

        manager.save_checkpoint("shardId-000000000000", "seq-123456")
        assert manager.get_checkpoint("shardId-000000000000") == "seq-123456"

        # Reload manager to verify disk persistence
        manager_reloaded = ShardCheckpointManager(checkpoint_path=cp_file)
        assert manager_reloaded.get_checkpoint("shardId-000000000000") == "seq-123456"
    finally:
        shutil.rmtree(temp_dir)


def test_consumer_poll_shard():
    temp_dir = tempfile.mkdtemp()
    cp_file = os.path.join(temp_dir, "checkpoint.json")

    try:
        mock_client = MagicMock()
        mock_client.list_shards.return_value = {
            "Shards": [{"ShardId": "shardId-000000000000"}]
        }
        mock_client.get_shard_iterator.return_value = {
            "ShardIterator": "iterator-abc"
        }

        # Mock GetRecords returning 2 transactions
        txn1 = {"transaction_id": "TXN-1", "amount": 100}
        txn2 = {"transaction_id": "TXN-2", "amount": 200}
        mock_client.get_records.return_value = {
            "Records": [
                {
                    "Data": json.dumps(txn1).encode("utf-8"),
                    "SequenceNumber": "seq-001"
                },
                {
                    "Data": json.dumps(txn2).encode("utf-8"),
                    "SequenceNumber": "seq-002"
                }
            ],
            "NextShardIterator": None
        }

        config = KinesisStreamConfig(stream_name="finguard-transactions-dev")
        cp_manager = ShardCheckpointManager(checkpoint_path=cp_file)
        consumer = KinesisShardConsumer(
            kinesis_client=mock_client,
            config=config,
            checkpoint_manager=cp_manager
        )

        consumed_records = []

        def sample_handler(record):
            consumed_records.append(record)

        total = consumer.poll_shard(
            shard_id="shardId-000000000000",
            record_handler=sample_handler,
            max_batches=1
        )

        assert total == 2
        assert len(consumed_records) == 2
        assert consumed_records[0]["transaction_id"] == "TXN-1"
        assert cp_manager.get_checkpoint("shardId-000000000000") == "seq-002"
    finally:
        shutil.rmtree(temp_dir)
