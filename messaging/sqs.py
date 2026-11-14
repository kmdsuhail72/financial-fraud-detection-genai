"""
Phase 40: Amazon SQS Queue Adapter Foundation
Implements Standard and FIFO queue semantics, visibility timeouts, deduplication, and redrive to DLQ.
"""

import collections
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from messaging.dlq import DeadLetterQueue


class SQSMessage(BaseModel):
    """Represents a message in an SQS Queue."""
    message_id: str = Field(default_factory=lambda: f"sqs-msg-{uuid.uuid4().hex[:10]}")
    body: Dict[str, Any]
    receipt_handle: str = Field(default_factory=lambda: f"rcpt-{uuid.uuid4().hex[:14]}")
    approximate_receive_count: int = Field(default=0)
    message_group_id: Optional[str] = None
    message_deduplication_id: Optional[str] = None
    sent_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(extra="allow")


class SQSQueueAdapter:
    """
    Thread-safe SQS Queue Adapter supporting Standard and FIFO configurations,
    deduplication windows, and automatic Dead-Letter Queue (DLQ) redrive.
    """

    def __init__(
        self,
        name: str,
        is_fifo: bool = False,
        max_receive_count: int = 3,
        dlq: Optional[DeadLetterQueue] = None,
    ):
        self.name = name
        self.is_fifo = is_fifo
        self.max_receive_count = max_receive_count
        self.dlq = dlq

        # Queue storage: list of SQSMessage
        self._messages: List[SQSMessage] = []
        # In-flight map: receipt_handle -> (message, invisible_until)
        self._in_flight: Dict[str, tuple[SQSMessage, float]] = {}
        # FIFO Deduplication map: dedup_id -> expiry_epoch (5-minute window)
        self._dedup_history: Dict[str, float] = {}
        self._lock = threading.Lock()

    def send_message(
        self,
        body: Dict[str, Any],
        message_group_id: Optional[str] = None,
        message_deduplication_id: Optional[str] = None,
    ) -> Optional[SQSMessage]:
        """Send message into queue. Enforces FIFO deduplication if applicable."""
        now = time.time()
        with self._lock:
            # FIFO Deduplication Check
            if self.is_fifo and message_deduplication_id:
                if message_deduplication_id in self._dedup_history:
                    if self._dedup_history[message_deduplication_id] > now:
                        # Duplicate within 5-minute deduplication window; dropped silently
                        return None
                # Register deduplication ID for 5 minutes (300s)
                self._dedup_history[message_deduplication_id] = now + 300.0

            msg = SQSMessage(
                body=body,
                message_group_id=message_group_id,
                message_deduplication_id=message_deduplication_id,
            )
            self._messages.append(msg)
            return msg

    def receive_messages(self, max_number: int = 1, visibility_timeout: int = 30) -> List[SQSMessage]:
        """
        Poll available messages. Increments receive count and enforces DLQ redrive
        if receive count breaches max_receive_count.
        """
        now = time.time()
        delivered: List[SQSMessage] = []

        with self._lock:
            # Reclaim expired in-flight messages
            expired_handles = [h for h, (_, exp) in self._in_flight.items() if exp <= now]
            for h in expired_handles:
                msg, _ = self._in_flight.pop(h)
                self._messages.append(msg)

            # Process candidates
            remaining_messages: List[SQSMessage] = []
            for msg in self._messages:
                if len(delivered) >= max_number:
                    remaining_messages.append(msg)
                    continue

                msg.approximate_receive_count += 1
                msg.receipt_handle = f"rcpt-{uuid.uuid4().hex[:14]}"

                # Redrive check
                if msg.approximate_receive_count > self.max_receive_count and self.dlq is not None:
                    # Quarantine to DLQ
                    self.dlq.store_failed_message(
                        original_queue=self.name,
                        payload=msg.body,
                        failure_reason=f"Exceeded max receive count ({self.max_receive_count})",
                        receive_count=msg.approximate_receive_count,
                        message_id=msg.message_id,
                    )
                    # Dropped from active queue
                    continue

                self._in_flight[msg.receipt_handle] = (msg, now + visibility_timeout)
                delivered.append(msg)

            self._messages = remaining_messages
            return delivered

    def delete_message(self, receipt_handle: str) -> bool:
        """Acknowledge message processing and delete from in-flight storage."""
        with self._lock:
            if receipt_handle in self._in_flight:
                del self._in_flight[receipt_handle]
                return True
            return False

    def nack_message(self, receipt_handle: str, failure_reason: str = "Processing error") -> bool:
        """
        Negative acknowledge: Re-queues the message or routes to DLQ
        if max_receive_count is exceeded.
        """
        with self._lock:
            if receipt_handle in self._in_flight:
                msg, _ = self._in_flight.pop(receipt_handle)
                if msg.approximate_receive_count >= self.max_receive_count and self.dlq is not None:
                    self.dlq.store_failed_message(
                        original_queue=self.name,
                        payload=msg.body,
                        failure_reason=failure_reason,
                        receive_count=msg.approximate_receive_count,
                        message_id=msg.message_id,
                    )
                    return True
                else:
                    self._messages.append(msg)
                    return True
            return False

    def approximate_number_of_messages(self) -> int:
        """Return total pending messages in the queue."""
        with self._lock:
            return len(self._messages)

    def approximate_number_of_messages_not_visible(self) -> int:
        """Return total in-flight messages."""
        with self._lock:
            return len(self._in_flight)

    def purge(self) -> None:
        """Purge all queue messages."""
        with self._lock:
            self._messages.clear()
            self._in_flight.clear()
            self._dedup_history.clear()
