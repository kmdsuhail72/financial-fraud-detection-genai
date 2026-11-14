"""
Phase 40: Apache Kafka & Amazon MSK Stream Adapter Foundation
Implements partitioned event logs, deterministic key-based partitioning,
consumer groups with committed offsets, and offset rewind for historical replay.
"""

import hashlib
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class KafkaRecord(BaseModel):
    """Represents a record stored in a Kafka partition log."""
    topic: str
    partition: int
    offset: int
    key: Optional[str]
    value: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)

    model_config = ConfigDict(extra="allow")


class KafkaStreamAdapter:
    """
    In-memory partition log providing the exact developer semantics of
    Apache Kafka / Amazon MSK (partitioning, consumer groups, offset tracking, replay).
    """

    def __init__(self, topic: str = "finguard.transactions.stream", num_partitions: int = 3):
        self.topic = topic
        self.num_partitions = num_partitions
        # topic -> partition_id -> list of KafkaRecord
        self._partitions: Dict[int, List[KafkaRecord]] = {i: [] for i in range(num_partitions)}
        # consumer_group -> partition_id -> committed_offset
        self._group_offsets: Dict[str, Dict[int, int]] = {}
        self._lock = threading.Lock()

    def _hash_partition(self, key: Optional[str]) -> int:
        if not key:
            return 0
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(digest, 16) % self.num_partitions

    def produce(self, key: Optional[str], value: Dict[str, Any]) -> KafkaRecord:
        """Produce an event record into a partitioned log based on key hash."""
        partition = self._hash_partition(key)
        with self._lock:
            offset = len(self._partitions[partition])
            record = KafkaRecord(
                topic=self.topic,
                partition=partition,
                offset=offset,
                key=key,
                value=value,
            )
            self._partitions[partition].append(record)
            return record

    def consume(self, consumer_group: str, max_records: int = 10) -> List[KafkaRecord]:
        """Consume unread records for a consumer group across all partitions."""
        consumed: List[KafkaRecord] = []
        with self._lock:
            if consumer_group not in self._group_offsets:
                self._group_offsets[consumer_group] = {i: 0 for i in range(self.num_partitions)}

            offsets = self._group_offsets[consumer_group]
            for partition_id in range(self.num_partitions):
                part_records = self._partitions[partition_id]
                current_off = offsets[partition_id]

                while current_off < len(part_records) and len(consumed) < max_records:
                    consumed.append(part_records[current_off])
                    current_off += 1

                offsets[partition_id] = current_off

        return consumed

    def rewind_offset(self, consumer_group: str, partition: int, target_offset: int) -> bool:
        """Rewind consumer offset for a partition to replay historical events."""
        with self._lock:
            if consumer_group not in self._group_offsets:
                self._group_offsets[consumer_group] = {i: 0 for i in range(self.num_partitions)}
            if partition < 0 or partition >= self.num_partitions:
                return False
            max_avail = len(self._partitions[partition])
            safe_offset = max(0, min(target_offset, max_avail))
            self._group_offsets[consumer_group][partition] = safe_offset
            return True

    def get_metrics(self) -> Dict[str, Any]:
        """Return total records across all partitions and consumer group states."""
        with self._lock:
            total_records = sum(len(p) for p in self._partitions.values())
            part_sizes = {f"partition_{i}": len(p) for i, p in self._partitions.items()}
            return {
                "topic": self.topic,
                "num_partitions": self.num_partitions,
                "total_records": total_records,
                "partition_sizes": part_sizes,
                "active_groups": list(self._group_offsets.keys()),
            }
