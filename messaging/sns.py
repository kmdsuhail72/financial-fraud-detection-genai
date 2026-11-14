"""
Phase 40: Amazon SNS Topic & Fan-Out Adapter
Publishes domain events and fans out copies to all subscribed SQS queues with filter policy support.
"""

import threading
import uuid
from typing import Any, Callable, Dict, List, Optional
from messaging.contracts import EventEnvelope
from messaging.sqs import SQSQueueAdapter


class SNSSubscription:
    """Represents a subscriber endpoint to an SNS Topic."""
    def __init__(
        self,
        subscription_arn: str,
        target_queue: Optional[SQSQueueAdapter] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        filter_policy: Optional[Dict[str, List[Any]]] = None,
    ):
        self.subscription_arn = subscription_arn
        self.target_queue = target_queue
        self.callback = callback
        self.filter_policy = filter_policy or {}

    def matches(self, event_data: Dict[str, Any]) -> bool:
        """Evaluate attribute filter policy."""
        if not self.filter_policy:
            return True
        for key, allowed_vals in self.filter_policy.items():
            val = event_data.get(key)
            if val not in allowed_vals:
                return False
        return True


class SNSTopicAdapter:
    """Publishes messages to multiple subscriber queues via 1-to-N fan-out."""

    def __init__(self, name: str = "finguard-transactions-fanout"):
        self.name = name
        self.topic_arn = f"arn:aws:sns:ap-south-1:123456789012:{name}"
        self._subscriptions: List[SNSSubscription] = []
        self._lock = threading.Lock()
        self.published_count = 0

    def subscribe_queue(
        self,
        queue: SQSQueueAdapter,
        filter_policy: Optional[Dict[str, List[Any]]] = None,
    ) -> str:
        """Subscribe an SQS queue to receive fanned-out messages."""
        sub_arn = f"{self.topic_arn}:{uuid.uuid4().hex[:8]}"
        with self._lock:
            sub = SNSSubscription(
                subscription_arn=sub_arn,
                target_queue=queue,
                filter_policy=filter_policy,
            )
            self._subscriptions.append(sub)
        return sub_arn

    def subscribe_callback(
        self,
        callback: Callable[[Dict[str, Any]], None],
        filter_policy: Optional[Dict[str, List[Any]]] = None,
    ) -> str:
        """Subscribe an in-process consumer callback."""
        sub_arn = f"{self.topic_arn}:{uuid.uuid4().hex[:8]}"
        with self._lock:
            sub = SNSSubscription(
                subscription_arn=sub_arn,
                callback=callback,
                filter_policy=filter_policy,
            )
            self._subscriptions.append(sub)
        return sub_arn

    def publish(self, event: Any) -> Dict[str, Any]:
        """Publish event and deliver to all active matching subscribers."""
        event_dict = event.model_dump() if isinstance(event, EventEnvelope) else dict(event)
        msg_id = f"sns-msg-{uuid.uuid4().hex[:12]}"
        deliveries = 0

        with self._lock:
            self.published_count += 1
            for sub in self._subscriptions:
                if sub.matches(event_dict):
                    if sub.target_queue:
                        sub.target_queue.send_message(event_dict)
                        deliveries += 1
                    elif sub.callback:
                        sub.callback(event_dict)
                        deliveries += 1

        return {
            "message_id": msg_id,
            "topic_arn": self.topic_arn,
            "deliveries": deliveries,
            "event_type": event_dict.get("event_type", "unknown"),
        }

    def get_subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)
