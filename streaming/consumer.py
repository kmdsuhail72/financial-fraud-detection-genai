"""
Kinesis stream shard consumer for real-time transaction processing.
"""
import time
import logging
from typing import Any, Callable, Dict, List, Optional
from streaming.config import KinesisStreamConfig
from streaming.serializer import TransactionSerializer
from streaming.checkpoint import ShardCheckpointManager

logger = logging.getLogger(__name__)


class KinesisShardConsumer:
    """Reads transaction events from Kinesis shards and updates processing checkpoints."""

    def __init__(
        self,
        kinesis_client: Any,
        config: KinesisStreamConfig,
        checkpoint_manager: Optional[ShardCheckpointManager] = None,
    ):
        self.client = kinesis_client
        self.config = config
        self.checkpoint_manager = checkpoint_manager or ShardCheckpointManager(config.checkpoint_file)

    def list_shards(self) -> List[str]:
        """Discovers active shards in the configured Kinesis stream."""
        try:
            response = self.client.list_shards(StreamName=self.config.stream_name)
            return [s["ShardId"] for s in response.get("Shards", [])]
        except Exception as exc:
            logger.error(f"Failed to list shards for stream {self.config.stream_name}: {str(exc)}")
            return []

    def get_shard_iterator(self, shard_id: str, default_type: str = "TRIM_HORIZON") -> Optional[str]:
        """Gets shard iterator, honoring saved checkpoint if present."""
        last_seq = self.checkpoint_manager.get_checkpoint(shard_id)
        if last_seq:
            params = {
                "StreamName": self.config.stream_name,
                "ShardId": shard_id,
                "ShardIteratorType": "AFTER_SEQUENCE_NUMBER",
                "StartingSequenceNumber": last_seq
            }
        else:
            params = {
                "StreamName": self.config.stream_name,
                "ShardId": shard_id,
                "ShardIteratorType": default_type
            }

        try:
            resp = self.client.get_shard_iterator(**params)
            return resp.get("ShardIterator")
        except Exception as exc:
            logger.error(f"Error obtaining shard iterator for {shard_id}: {str(exc)}")
            return None

    def poll_shard(
        self,
        shard_id: str,
        record_handler: Callable[[Dict[str, Any]], None],
        max_batches: int = 10,
        batch_limit: int = 100,
    ) -> int:
        """
        Polls records from a shard, invokes record_handler, and updates checkpoints.
        Returns total records successfully consumed.
        """
        iterator = self.get_shard_iterator(shard_id)
        if not iterator:
            return 0

        batches_processed = 0
        total_consumed = 0

        while iterator and batches_processed < max_batches:
            batches_processed += 1
            try:
                response = self.client.get_records(
                    ShardIterator=iterator,
                    Limit=batch_limit
                )

                records = response.get("Records", [])
                last_sequence_num = None

                for rec in records:
                    raw_data = rec["Data"]
                    seq_num = rec["SequenceNumber"]

                    is_valid, txn, error = TransactionSerializer.deserialize(raw_data)
                    if is_valid:
                        record_handler(txn)
                        total_consumed += 1
                        last_sequence_num = seq_num
                    else:
                        logger.warning(f"Consumer could not deserialize record {seq_num}: {error}")

                if last_sequence_num:
                    self.checkpoint_manager.save_checkpoint(shard_id, last_sequence_num)

                iterator = response.get("NextShardIterator")

                # Respect Kinesis 5 read transactions per second per shard limit
                if not records:
                    time.sleep(0.5)

            except Exception as exc:
                logger.error(f"Error polling records from shard {shard_id}: {str(exc)}")
                break

        return total_consumed
