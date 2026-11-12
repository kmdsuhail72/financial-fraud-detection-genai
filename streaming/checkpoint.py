"""
Consumer Checkpoint Management for Kinesis Shard Iterators.
"""
import json
import os
from typing import Dict, Optional


class ShardCheckpointManager:
    """Manages persistent checkpoints for Kinesis shard consumers."""

    def __init__(self, checkpoint_path: str = "data/checkpoints/kinesis_consumer.json"):
        self.checkpoint_path = checkpoint_path
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        self.checkpoints: Dict[str, str] = self._load()

    def _load(self) -> Dict[str, str]:
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_checkpoint(self, shard_id: str) -> Optional[str]:
        """Returns the last sequence number processed for the given shard."""
        return self.checkpoints.get(shard_id)

    def save_checkpoint(self, shard_id: str, sequence_number: str):
        """Saves current sequence number for a shard."""
        self.checkpoints[shard_id] = sequence_number
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(self.checkpoints, f, indent=2)
