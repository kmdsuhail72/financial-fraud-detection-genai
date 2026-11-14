"""
Phase 40: Dead-Letter Queue (DLQ) & Quarantine Management
Provides message quarantine, failure tracking, inspection, and controlled replay.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DeadLetterMessage(BaseModel):
    """Quarantined message captured by a Dead-Letter Queue."""
    message_id: str = Field(default_factory=lambda: f"dlq-msg-{uuid.uuid4().hex[:8]}")
    original_queue: str
    payload: Dict[str, Any]
    failure_reason: str
    receive_count: int
    quarantined_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(extra="allow")


class DeadLetterQueue:
    """Thread-safe Dead-Letter Queue with controlled message replay."""

    def __init__(self, name: str = "finguard-main-dlq"):
        self.name = name
        self._messages: Dict[str, DeadLetterMessage] = {}
        self._lock = threading.Lock()

    def store_failed_message(
        self,
        original_queue: str,
        payload: Dict[str, Any],
        failure_reason: str,
        receive_count: int,
        message_id: Optional[str] = None,
    ) -> DeadLetterMessage:
        """Quarantine a poisoned or failed message after retries are exhausted."""
        with self._lock:
            msg_id = message_id or f"dlq-{uuid.uuid4().hex[:8]}"
            dlq_msg = DeadLetterMessage(
                message_id=msg_id,
                original_queue=original_queue,
                payload=payload,
                failure_reason=failure_reason,
                receive_count=receive_count,
            )
            self._messages[msg_id] = dlq_msg
            return dlq_msg

    def list_messages(self, limit: int = 50) -> List[DeadLetterMessage]:
        """List quarantined messages in the DLQ."""
        with self._lock:
            return list(self._messages.values())[:limit]

    def get_message(self, message_id: str) -> Optional[DeadLetterMessage]:
        """Fetch a specific dead-letter message by ID."""
        with self._lock:
            return self._messages.get(message_id)

    def replay_message(self, message_id: str, target_queue: Any) -> bool:
        """
        Replay a quarantined message back to the target queue with reset receive count.
        Removes the message from DLQ on successful re-enqueue.
        """
        with self._lock:
            if message_id not in self._messages:
                return False
            dlq_msg = self._messages[message_id]
            # Send back to target queue
            target_queue.send_message(dlq_msg.payload)
            # Remove from quarantine
            del self._messages[message_id]
            return True

    def delete_message(self, message_id: str) -> bool:
        """Discard a poisoned message permanently from the DLQ."""
        with self._lock:
            if message_id in self._messages:
                del self._messages[message_id]
                return True
            return False

    def count(self) -> int:
        """Return total count of quarantined messages."""
        with self._lock:
            return len(self._messages)

    def purge(self) -> int:
        """Purge all messages from the DLQ."""
        with self._lock:
            total = len(self._messages)
            self._messages.clear()
            return total
