"""Pluggable Threat Intelligence Provider Adapters and Fixture Repositories."""

from __future__ import annotations

import abc
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from threat_intel.ioc_extractor import IOCExtractor
from threat_intel.mitre_mapper import MITREMapper
from threat_intel.models import (
    IOCRecord,
    IOCSeverity,
    IOCStatus,
    IOCType,
)
from threat_intel.risk_engine import IOCRiskEngine


class ThreatIntelProvider(abc.ABC):
    """Abstract interface for threat intelligence provider adapters."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier name."""
        pass

    @abc.abstractmethod
    def enrich(self, value: str, ioc_type: IOCType) -> Optional[IOCRecord]:
        """Queries intelligence provider for reputation and context on an indicator."""
        pass


class OfflineFixtureProvider(ThreatIntelProvider):
    """High-fidelity offline threat intelligence fixture adapter."""

    @property
    def name(self) -> str:
        return "OfflineFixtureProvider"

    def __init__(self):
        # Known threat fixtures
        now = datetime.now(timezone.utc)
        self.fixtures: Dict[str, Dict[str, Any]] = {
            "198.51.100.42": {
                "type": IOCType.IPV4,
                "threat_types": ["c2", "proxy"],
                "reputation_score": 88.0,
                "confidence": 0.95,
                "source_feeds": ["FinGuard-Global-Feed", "AbuseIPDB-Sim", "AlienVault-OTX-Sim"],
                "tags": ["apt29", "tor-exit", "bulletproof-host"],
                "metadata": {"asn": "AS40065", "country": "SE", "org": "Mullvad Exit Node"},
            },
            "192.0.2.10": {
                "type": IOCType.IPV4,
                "threat_types": ["c2", "botnet"],
                "reputation_score": 92.0,
                "confidence": 0.90,
                "source_feeds": ["Banking-ISAC-Feed", "Shadowserver-Sim"],
                "tags": ["dridex-c2", "financial-crime"],
                "metadata": {"asn": "AS12345", "country": "RU", "org": "Malicious Hosting"},
            },
            "evil-bank-login.com": {
                "type": IOCType.DOMAIN,
                "threat_types": ["phishing", "credential_theft"],
                "reputation_score": 96.0,
                "confidence": 0.98,
                "source_feeds": ["PhishTank-Sim", "OpenPhish-Sim"],
                "tags": ["credential-harvester", "synthetic-kyc"],
                "metadata": {"registrar": "NameCheap-Proxy", "created_date": "2026-11-01"},
            },
            "https://secure-update-verify.net/auth": {
                "type": IOCType.URL,
                "threat_types": ["phishing", "account_takeover"],
                "reputation_score": 90.0,
                "confidence": 0.92,
                "source_feeds": ["FinGuard-URLhaus-Sim"],
                "tags": ["mfa-bypass-kit", "adversary-in-the-middle"],
                "metadata": {"status_code": 200, "content_type": "text/html"},
            },
            "44d88612fea8a8f36de82e1278abb02f": {
                "type": IOCType.MD5,
                "threat_types": ["ransomware", "c2"],
                "reputation_score": 95.0,
                "confidence": 0.99,
                "source_feeds": ["VirusTotal-Sim", "MalwareBazaar-Sim"],
                "tags": ["trojan.banker.dridex", "stealer"],
                "metadata": {"file_type": "PE32 Executable", "file_size": 245760},
            },
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": {
                "type": IOCType.SHA256,
                "threat_types": ["ransomware", "command_and_control"],
                "reputation_score": 94.0,
                "confidence": 0.97,
                "source_feeds": ["VirusTotal-Sim", "ThreatConnect-Sim"],
                "tags": ["lockbit-loader", "evasion"],
                "metadata": {"signature": "Trojan.GenericKD.654321", "file_size": 512000},
            },
        }

    def enrich(self, value: str, ioc_type: IOCType) -> Optional[IOCRecord]:
        norm = IOCExtractor.normalize_ioc(ioc_type, value)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)

        if norm in self.fixtures:
            data = self.fixtures[norm]
            threat_types = data["threat_types"]
            mitre_techs = MITREMapper.map_threat_types_to_techniques(threat_types)
            score, conf, sev, stat, _ = IOCRiskEngine.evaluate_risk(
                base_reputation=data["reputation_score"],
                base_confidence=data["confidence"],
                threat_types=threat_types,
                source_feeds=data["source_feeds"],
                analyst_verdicts=[],
                expires_at=expires_at,
            )
            # Deterministic hash ID
            ioc_id = f"ioc-{ioc_type.value}-{hashlib.sha256(norm.encode()).hexdigest()[:12]}"
            return IOCRecord(
                ioc_id=ioc_id,
                type=ioc_type,
                value=norm,
                threat_types=threat_types,
                reputation_score=score,
                confidence=conf,
                severity=sev,
                status=stat,
                mitre_attack=mitre_techs,
                first_seen=now - timedelta(days=7),
                last_seen=now,
                expires_at=expires_at,
                source_feeds=data["source_feeds"],
                tags=data.get("tags", []),
                metadata=data.get("metadata", {}),
            )

        # Dynamic heuristic fallback for unlisted indicators
        # Benign baseline / low risk heuristic
        ioc_id = f"ioc-{ioc_type.value}-{hashlib.sha256(norm.encode()).hexdigest()[:12]}"
        return IOCRecord(
            ioc_id=ioc_id,
            type=ioc_type,
            value=norm,
            threat_types=["unclassified"],
            reputation_score=10.0,
            confidence=0.50,
            severity=IOCSeverity.INFO,
            status=IOCStatus.ACTIVE,
            mitre_attack=[],
            first_seen=now,
            last_seen=now,
            expires_at=expires_at,
            source_feeds=["FinGuard-Heuristic-Baseline"],
            tags=["unclassified-lead"],
            metadata={"enriched_by": self.name, "heuristic": True},
        )


class CompositeThreatIntelAdapter:
    """Manages provider routing, fallback chaining, and multi-source aggregation."""

    def __init__(self, providers: Optional[List[ThreatIntelProvider]] = None):
        self.providers = providers or [OfflineFixtureProvider()]

    def enrich(self, value: str, ioc_type: Optional[IOCType] = None) -> Optional[IOCRecord]:
        """Classifies indicator and queries available providers."""
        if ioc_type is None:
            detected = IOCExtractor.classify_and_validate(value)
            if not detected:
                return None
            ioc_type = detected

        for prov in self.providers:
            record = prov.enrich(value, ioc_type)
            if record:
                return record
        return None

