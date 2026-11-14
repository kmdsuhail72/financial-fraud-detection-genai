"""
Phase 40: Amazon EventBridge Bus & Content-Based Routing Adapter
Routes transaction events based on JSON detail payload content patterns.
"""

import threading
import uuid
from typing import Any, Dict, List, Optional
from messaging.contracts import EventEnvelope
from messaging.sqs import SQSQueueAdapter


class EventBridgeRule:
    """EventBridge rule with content pattern matching."""

    def __init__(self, name: str, event_pattern: Dict[str, Any], target_queue: SQSQueueAdapter):
        self.name = name
        self.event_pattern = event_pattern
        self.target_queue = target_queue

    def evaluate(self, event_data: Dict[str, Any]) -> bool:
        """
        Evaluate EventBridge event pattern syntax.
        Supports exact string match, array match, and numeric range rules.
        """
        return self._match_dict(self.event_pattern, event_data)

    def _match_dict(self, pattern: Dict[str, Any], data: Dict[str, Any]) -> bool:
        for k, expected in pattern.items():
            if k not in data:
                return False
            val = data[k]

            if isinstance(expected, dict) and isinstance(val, dict):
                if not self._match_dict(expected, val):
                    return False
            elif isinstance(expected, list):
                # Pattern list can contain literal values or filter rules
                matched = False
                for exp_item in expected:
                    if isinstance(exp_item, dict) and "numeric" in exp_item:
                        # Numeric filter: e.g. [">=", 100000]
                        op, threshold = exp_item["numeric"]
                        if op == ">=" and isinstance(val, (int, float)) and val >= threshold:
                            matched = True
                            break
                        elif op == ">" and isinstance(val, (int, float)) and val > threshold:
                            matched = True
                            break
                        elif op == "<=" and isinstance(val, (int, float)) and val <= threshold:
                            matched = True
                            break
                        elif op == "<" and isinstance(val, (int, float)) and val < threshold:
                            matched = True
                            break
                    elif exp_item == val:
                        matched = True
                        break
                if not matched:
                    return False
            else:
                if val != expected:
                    return False
        return True


class EventBridgeBusAdapter:
    """Manages custom EventBridge bus and content-based event routing."""

    def __init__(self, bus_name: str = "finguard-enterprise-bus"):
        self.bus_name = bus_name
        self._rules: List[EventBridgeRule] = []
        self._lock = threading.Lock()
        self.routed_count = 0

    def add_rule(self, name: str, event_pattern: Dict[str, Any], target_queue: SQSQueueAdapter) -> None:
        """Register a content-based rule with an SQS target queue."""
        with self._lock:
            rule = EventBridgeRule(name=name, event_pattern=event_pattern, target_queue=target_queue)
            self._rules.append(rule)

    def put_events(self, events: List[Any]) -> Dict[str, Any]:
        """Put events onto bus and route to matching target queues."""
        entries = []
        matched_count = 0

        with self._lock:
            for ev in events:
                data = ev.model_dump() if isinstance(ev, EventEnvelope) else dict(ev)
                event_id = data.get("event_id", f"eb-{uuid.uuid4().hex[:10]}")

                # Format in EventBridge format
                eb_event = {
                    "source": data.get("producer", "finguard.transactions"),
                    "detail-type": data.get("event_type", "TransactionEvent"),
                    "detail": data.get("payload", {}),
                    "tenant_id": data.get("tenant_id"),
                }

                for rule in self._rules:
                    if rule.evaluate(eb_event):
                        rule.target_queue.send_message(data)
                        matched_count += 1
                        self.routed_count += 1

                entries.append({"EventId": event_id, "ErrorCode": None})

        return {
            "FailedEntryCount": 0,
            "Entries": entries,
            "MatchedRulesCount": matched_count,
        }

    def get_rule_count(self) -> int:
        with self._lock:
            return len(self._rules)
