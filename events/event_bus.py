"""
FinGuard AI — Phase 33: In-Memory Event Bus & Pub/Sub Dispatcher.
Implements topic routing, subscriber registration, bounded retries, and DLQ routing.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, List, Optional
from events.models import DeadLetterRecord, EventContract

logger = logging.getLogger("finguard-event-bus")


class EventBus:
    def __init__(self, max_retries: int = 3):
        self._lock = threading.RLock()
        self.max_retries = max_retries
        self._subscribers: Dict[str, List[Callable[[EventContract], None]]] = {}
        self._event_log: List[EventContract] = []
        self._dlq: List[DeadLetterRecord] = []

    def subscribe(self, event_type: str, handler: Callable[[EventContract], None]):
        """Registers a microservice subscriber handler for a specific event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)
            logger.info("Subscribed handler %s to event_type %s", handler.__name__, event_type)

    def publish(self, event: EventContract) -> bool:
        """
        Publishes an event to all matching subscribers.
        Executes bounded retries on handler failure and diverts to DLQ on exhaustion.
        """
        with self._lock:
            self._event_log.append(event)

        handlers = []
        with self._lock:
            handlers.extend(self._subscribers.get(event.event_type, []))
            handlers.extend(self._subscribers.get("*", []))

        success = True
        for handler in handlers:
            attempts = 0
            handler_success = False
            last_err = None

            while attempts < self.max_retries and not handler_success:
                attempts += 1
                try:
                    handler(event)
                    handler_success = True
                except Exception as exc:
                    last_err = exc
                    logger.warning(
                        "Handler %s failed on event %s (attempt %d/%d): %s",
                        handler.__name__,
                        event.event_id,
                        attempts,
                        self.max_retries,
                        exc,
                    )

            if not handler_success:
                success = False
                self._route_to_dlq(event, str(last_err), attempts)

        return success

    def _route_to_dlq(self, event: EventContract, reason: str, attempts: int):
        with self._lock:
            dlq_entry = DeadLetterRecord(
                original_event=event,
                failure_reason=reason,
                retry_attempts=attempts,
            )
            self._dlq.append(dlq_entry)
            logger.error("Event %s diverted to DLQ: %s", event.event_id, reason)

    def get_event_log(self, correlation_id: Optional[str] = None) -> List[EventContract]:
        with self._lock:
            if correlation_id:
                return [e for e in self._event_log if e.correlation_id == correlation_id]
            return list(self._event_log)

    def get_dlq_records(self) -> List[DeadLetterRecord]:
        with self._lock:
            return list(self._dlq)

    def replay_dlq(self, dlq_id: str) -> bool:
        """Attempts to reprocess a dead-letter message."""
        with self._lock:
            record = next((r for r in self._dlq if r.dlq_id == dlq_id), None)
            if not record or record.replayed:
                return False

            # Attempt replay
            replayed_ok = self.publish(record.original_event)
            if replayed_ok:
                record.replayed = True
                return True
            return False

    def clear(self):
        with self._lock:
            self._event_log.clear()
            self._dlq.clear()


# Global singleton event bus
event_bus = EventBus(max_retries=3)
