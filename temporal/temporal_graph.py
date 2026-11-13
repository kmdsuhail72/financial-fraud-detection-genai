"""In-Memory Temporal Graph with Bounded Sliding History and Edge Traversal."""

from __future__ import annotations

import bisect
import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from temporal.models import TemporalTransactionEvent

logger = logging.getLogger("finguard-temporal-graph")


class TemporalEdge:
    __slots__ = ("source", "target", "edge_type", "timestamp", "amount", "properties")

    def __init__(
        self,
        source: str,
        target: str,
        edge_type: str,
        timestamp: float,
        amount: float = 0.0,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.source = source
        self.target = target
        self.edge_type = edge_type
        self.timestamp = timestamp
        self.amount = amount
        self.properties = properties or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "timestamp": self.timestamp,
            "amount": self.amount,
            "properties": self.properties,
        }


class TemporalGraph:
    """
    Maintains time-ordered relationship interactions with a bounded sliding window.
    Ensures memory efficiency while preserving chronological causality.
    """

    def __init__(self, max_history_per_entity: int = 500, default_window_seconds: int = 604800):
        self.max_history_per_entity = max_history_per_entity
        self.default_window_seconds = default_window_seconds

        # Entity index to chronological deque of events
        self._entity_events: Dict[str, deque[TemporalTransactionEvent]] = defaultdict(
            lambda: deque(maxlen=self.max_history_per_entity)
        )
        # Entity device history: entity -> set of known devices
        self._entity_known_devices: Dict[str, Set[str]] = defaultdict(set)
        # Entity IP history: entity -> set of known IPs
        self._entity_known_ips: Dict[str, Set[str]] = defaultdict(set)
        # Chronological global temporal edge list
        self._global_edges: List[TemporalEdge] = []

    def add_event(self, event: TemporalTransactionEvent) -> None:
        """Appends event into source and target entity historical deques."""
        # 1. Update source entity
        if event.source_account:
            self._entity_events[event.source_account].append(event)
            if event.device_id:
                self._entity_known_devices[event.source_account].add(event.device_id)
            if event.ip_address:
                self._entity_known_ips[event.source_account].add(event.ip_address)

        # 2. Update target entity
        if event.target_account:
            self._entity_events[event.target_account].append(event)

        # 3. Add to global edges
        edge = TemporalEdge(
            source=event.source_account,
            target=event.target_account or event.merchant_id or "UNKNOWN",
            edge_type=event.event_type,
            timestamp=event.timestamp,
            amount=event.amount,
            properties={"currency": event.currency, "channel": event.channel},
        )
        self._global_edges.append(edge)
        if len(self._global_edges) > 20000:
            self._global_edges.pop(0)

    def get_entity_events(
        self,
        entity_id: str,
        as_of: Optional[float] = None,
        window_seconds: Optional[float] = None,
        limit: int = 50,
    ) -> List[TemporalTransactionEvent]:
        """
        Retrieves chronological events strictly prior to or equal to `as_of`.
        Prevents lookahead data leakage.
        """
        events = list(self._entity_events.get(entity_id, []))
        if not events:
            return []

        if as_of is not None:
            events = [e for e in events if e.timestamp <= as_of]

        if window_seconds is not None and as_of is not None:
            min_ts = as_of - window_seconds
            events = [e for e in events if e.timestamp >= min_ts]

        events.sort(key=lambda e: e.timestamp)
        return events[-limit:]

    def is_new_device_for_entity(self, entity_id: str, device_id: Optional[str]) -> bool:
        if not device_id:
            return False
        known = self._entity_known_devices.get(entity_id, set())
        return device_id not in known

    def is_new_ip_for_entity(self, entity_id: str, ip_address: Optional[str]) -> bool:
        if not ip_address:
            return False
        known = self._entity_known_ips.get(entity_id, set())
        return ip_address not in known

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entities_tracked": len(self._entity_events),
            "total_global_edges": len(self._global_edges),
            "window_seconds": self.default_window_seconds,
        }

    def clear(self) -> None:
        self._entity_events.clear()
        self._entity_known_devices.clear()
        self._entity_known_ips.clear()
        self._global_edges.clear()
