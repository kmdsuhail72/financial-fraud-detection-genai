"""Central Threat Intelligence Store & Orchestrator for FinGuard AI."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from threat_intel.adapters import CompositeThreatIntelAdapter, OfflineFixtureProvider
from threat_intel.ioc_extractor import IOCExtractor
from threat_intel.models import (
    AnalystFeedback,
    IOCEnrichmentResponse,
    IOCRecord,
    ThreatHuntingRule,
    ThreatHuntResult,
)
from threat_intel.reputation_cache import SQLiteReputationCache
from threat_intel.threat_hunter import ThreatHunter

logger = logging.getLogger("finguard-threat-intel")


class ThreatIntelStore:
    """Singleton coordinator for IOC caching, multi-provider enrichment, and hunting operations."""

    def __init__(self, db_path: Optional[str] = None):
        self.cache = SQLiteReputationCache(db_path=db_path)
        self.adapter = CompositeThreatIntelAdapter(providers=[OfflineFixtureProvider()])
        self.hunter = ThreatHunter(cache=self.cache)
        self._rules: Dict[str, ThreatHuntingRule] = {}
        self._init_default_rules()
        self._seed_default_iocs()

    def _init_default_rules(self) -> None:
        """Seeds default threat hunting rules mapped to MITRE ATT&CK."""
        r1 = ThreatHuntingRule(
            rule_id="HUNT-RULE-001",
            name="C2 Communication to Known Malicious Exit Nodes & Proxies",
            description="Identifies outbound network sessions or API calls originating from known C2 proxy infrastructure.",
            severity="HIGH",
            mitre_technique_id="T1071",
            conditions={
                "logic": "OR",
                "conditions": [
                    {"field": "source_ip", "operator": "matches_ioc"},
                    {"field": "ip_address", "operator": "matches_ioc"},
                    {"field": "details.ip_address", "operator": "matches_ioc"},
                ],
            },
            enabled=True,
        )

        r2 = ThreatHuntingRule(
            rule_id="HUNT-RULE-002",
            name="Credential Access & High Velocity Authentication Abuse",
            description="Detects anomalous password brute forcing, credential stuffing, and session hijacking.",
            severity="CRITICAL",
            mitre_technique_id="T1110",
            conditions={
                "logic": "OR",
                "conditions": [
                    {"field": "event_type", "operator": "contains", "value": "Credential"},
                    {"field": "event_type", "operator": "contains", "value": "BruteForce"},
                    {"field": "details.type", "operator": "contains", "value": "AnomalousBehavior"},
                ],
            },
            enabled=True,
        )

        r3 = ThreatHuntingRule(
            rule_id="HUNT-RULE-003",
            name="Phishing Infrastructure & Rogue Domain Interaction",
            description="Hunts for web traffic or email leads directed toward deceptive lookalike banking domains.",
            severity="HIGH",
            mitre_technique_id="T1566",
            conditions={
                "logic": "OR",
                "conditions": [
                    {"field": "domain", "operator": "matches_ioc"},
                    {"field": "details.domain", "operator": "matches_ioc"},
                    {"field": "url", "operator": "matches_ioc"},
                ],
            },
            enabled=True,
        )

        self._rules = {r1.rule_id: r1, r2.rule_id: r2, r3.rule_id: r3}

    def _seed_default_iocs(self) -> None:
        """Populates cache with baseline threat indicators."""
        seed_values = [
            "198.51.100.42",
            "192.0.2.10",
            "evil-bank-login.com",
            "https://secure-update-verify.net/auth",
            "44d88612fea8a8f36de82e1278abb02f",
        ]
        for val in seed_values:
            existing = self.cache.get_ioc(val)
            if not existing:
                enriched = self.adapter.enrich(val)
                if enriched:
                    self.cache.set_ioc(enriched)

    def enrich_indicators(
        self,
        indicators: List[str],
        force_refresh: bool = False,
    ) -> IOCEnrichmentResponse:
        """Enriches a batch of raw indicator strings, using cache whenever possible."""
        enriched: List[IOCRecord] = []
        unrecognized: List[str] = []
        cache_hits = 0

        for raw in indicators:
            norm_val = raw.strip()
            ioc_type = IOCExtractor.classify_and_validate(norm_val)
            if not ioc_type:
                unrecognized.append(raw)
                continue

            # Check cache
            if not force_refresh:
                cached = self.cache.get_ioc(norm_val)
                if cached:
                    enriched.append(cached)
                    cache_hits += 1
                    continue

            # Provider query
            record = self.adapter.enrich(norm_val, ioc_type)
            if record:
                self.cache.set_ioc(record)
                enriched.append(record)
            else:
                unrecognized.append(raw)

        return IOCEnrichmentResponse(
            enriched=enriched,
            unrecognized=unrecognized,
            total_processed=len(indicators),
            cache_hits=cache_hits,
        )

    def list_hunting_rules(self) -> List[ThreatHuntingRule]:
        return list(self._rules.values())

    def get_hunting_rule(self, rule_id: str) -> Optional[ThreatHuntingRule]:
        return self._rules.get(rule_id)

    def execute_hunt(
        self,
        events: List[Dict[str, Any]],
        rule_ids: Optional[List[str]] = None,
    ) -> List[ThreatHuntResult]:
        """Runs specified or all active hunting rules across the provided events."""
        target_rules = (
            [self._rules[rid] for rid in rule_ids if rid in self._rules]
            if rule_ids
            else list(self._rules.values())
        )
        return self.hunter.hunt(rules=target_rules, events=events)


# Global singleton instance
threat_intel_store = ThreatIntelStore()

