"""Rule-Based Threat Hunting and Security Event Correlation Engine for FinGuard AI."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from threat_intel.models import (
    ThreatHuntingRule,
    ThreatHuntResult,
)
from threat_intel.reputation_cache import SQLiteReputationCache

logger = logging.getLogger("finguard-threat-intel")


class ThreatHunter:
    """Evaluates hypothesis-driven threat hunting rules across security events and indicator telemetry."""

    def __init__(self, cache: SQLiteReputationCache):
        self.cache = cache

    def _get_nested_field(self, obj: Dict[str, Any], path: str) -> Any:
        """Retrieves dotted nested dictionary field, e.g. 'details.source_ip'."""
        parts = path.split(".")
        curr: Any = obj
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return None
        return curr

    def evaluate_condition(self, event: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """Evaluates a single condition against an event dictionary."""
        field = condition.get("field")
        op = condition.get("operator", "equals").lower()
        expected = condition.get("value")

        actual = self._get_nested_field(event, field) if field else None

        if op == "equals":
            return str(actual).lower() == str(expected).lower() if actual is not None else False
        elif op == "not_equals":
            return str(actual).lower() != str(expected).lower() if actual is not None else True
        elif op == "contains":
            return str(expected).lower() in str(actual).lower() if actual is not None else False
        elif op == "in":
            if isinstance(expected, list):
                return actual in expected or str(actual).lower() in [str(x).lower() for x in expected]
            return False
        elif op == "regex":
            if actual is None:
                return False
            return bool(re.search(str(expected), str(actual), re.IGNORECASE))
        elif op == "gte":
            try:
                return float(actual) >= float(expected)
            except (ValueError, TypeError):
                return False
        elif op == "lte":
            try:
                return float(actual) <= float(expected)
            except (ValueError, TypeError):
                return False
        elif op == "matches_ioc":
            # Checks if actual value matches a known cached malicious IOC
            if not actual:
                return False
            cached = self.cache.get_ioc(str(actual))
            if cached and cached.status.value in ("ACTIVE", "UNDER_REVIEW") and cached.reputation_score >= 50.0:
                return True
            return False

        return False

    def evaluate_rule(
        self,
        rule: ThreatHuntingRule,
        events: List[Dict[str, Any]],
    ) -> Optional[ThreatHuntResult]:
        """Runs a hunting rule against a sequence of security events."""
        if not rule.enabled:
            return None

        conditions = rule.conditions.get("conditions", [rule.conditions])
        operator = rule.conditions.get("logic", "AND").upper()

        matched_events: List[Dict[str, Any]] = []
        matched_iocs: List[str] = []

        for evt in events:
            # Flatten or check event
            match_flags = [self.evaluate_condition(evt, cond) for cond in conditions]
            is_match = all(match_flags) if operator == "AND" else any(match_flags)

            if is_match:
                matched_events.append(evt)
                # Check if event contains any known IOC
                for k in ("source_ip", "ip_address", "domain", "url", "hash", "file_hash"):
                    v = self._get_nested_field(evt, k) or self._get_nested_field(evt, f"details.{k}")
                    if v and str(v) not in matched_iocs:
                        matched_iocs.append(str(v))

        if not matched_events:
            return None

        hunt_id = f"hunt-{uuid.uuid4().hex[:8]}"
        summary = (
            f"Hunting rule '{rule.name}' triggered on {len(matched_events)} event(s) "
            f"associated with MITRE technique {rule.mitre_technique_id}."
        )

        return ThreatHuntResult(
            hunt_id=hunt_id,
            rule_id=rule.rule_id,
            rule_name=rule.name,
            mitre_technique_id=rule.mitre_technique_id,
            matched_events=matched_events,
            matched_iocs=matched_iocs,
            timestamp=datetime.now(timezone.utc),
            summary=summary,
        )

    def hunt(
        self,
        rules: List[ThreatHuntingRule],
        events: List[Dict[str, Any]],
    ) -> List[ThreatHuntResult]:
        """Executes a hunting campaign across all enabled rules."""
        results: List[ThreatHuntResult] = []
        for r in rules:
            res = self.evaluate_rule(r, events)
            if res:
                results.append(res)
        logger.info("Threat hunt execution completed: %d finding(s) discovered across %d events", len(results), len(events))
        return results
