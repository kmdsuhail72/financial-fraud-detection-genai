"""Unit and Integration Tests for Phase 13 Enterprise Threat Intelligence & MITRE ATT&CK Mapping."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Prevent AWS metadata queries during testing
os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

from api.app import app
from security.auth import create_test_token
from threat_intel.adapters import OfflineFixtureProvider
from threat_intel.ioc_extractor import IOCExtractor
from threat_intel.mitre_mapper import MITREMapper
from threat_intel.models import (
    AnalystFeedback,
    AnalystVerdict,
    IOCRecord,
    IOCSeverity,
    IOCStatus,
    IOCType,
    ThreatHuntingRule,
)
from threat_intel.reputation_cache import SQLiteReputationCache
from threat_intel.risk_engine import IOCRiskEngine
from threat_intel.store import ThreatIntelStore
from threat_intel.threat_hunter import ThreatHunter


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_cache():
    """Provides an isolated SQLite cache in the local data directory."""
    db_file = Path("data/test_fixture_cache.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass
    cache = SQLiteReputationCache(db_path=str(db_file))
    yield cache
    cache.clear()
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass


# ========================================================
# 1. IOC Extraction & Classification Test
# ========================================================
def test_ioc_extraction_and_classification():
    """Verify syntax classification across all 6 supported IOC types."""
    assert IOCExtractor.classify_and_validate("198.51.100.42") == IOCType.IPV4
    assert IOCExtractor.classify_and_validate("evil-bank-login.com") == IOCType.DOMAIN
    assert IOCExtractor.classify_and_validate("https://secure-update-verify.net/auth") == IOCType.URL
    assert IOCExtractor.classify_and_validate("44d88612fea8a8f36de82e1278abb02f") == IOCType.MD5
    assert IOCExtractor.classify_and_validate("da39a3ee5e6b4b0d3255bfef95601890afd80709") == IOCType.SHA1
    assert IOCExtractor.classify_and_validate("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") == IOCType.SHA256

    # Invalid patterns
    assert IOCExtractor.classify_and_validate("999.999.999.999") is None
    assert IOCExtractor.classify_and_validate("not_an_ioc") is None
    assert IOCExtractor.classify_and_validate("") is None


# ========================================================
# 2. Unstructured Text IOC Extraction Test
# ========================================================
def test_ioc_unstructured_text_extraction():
    """Verify regex extraction of multiple indicators embedded in free text."""
    sample_text = """
    Alert from SOC: Inbound phishing from https://phish-site.org/login
    C2 beacon detected to 198.51.100.42 and domain malicious-api.net.
    File dropped with MD5 44d88612fea8a8f36de82e1278abb02f.
    """
    extracted = IOCExtractor.extract_from_text(sample_text)

    assert "198.51.100.42" in extracted[IOCType.IPV4]
    assert "https://phish-site.org/login" in extracted[IOCType.URL]
    assert "malicious-api.net" in extracted[IOCType.DOMAIN]
    assert "44d88612fea8a8f36de82e1278abb02f" in extracted[IOCType.MD5]


# ========================================================
# 3. MITRE ATT&CK Mapping Test
# ========================================================
def test_mitre_attack_mapping():
    """Verify ATT&CK technique retrieval and threat taxonomy mapping."""
    tech = MITREMapper.get_technique("T1071")
    assert tech is not None
    assert tech.technique_id == "T1071"
    assert tech.name == "Application Layer Protocol"
    assert tech.tactic == "Command and Control"

    mapped = MITREMapper.map_threat_types_to_techniques(["c2", "phishing", "credential_stuffing"])
    mapped_ids = [m.technique_id for m in mapped]
    assert "T1071" in mapped_ids
    assert "T1566" in mapped_ids
    assert "T1110" in mapped_ids


# ========================================================
# 4. Explainable IOC Risk Scoring Test
# ========================================================
def test_explainable_risk_scoring():
    """Verify risk calculation formula, multi-feed corroboration, and severity mapping."""
    score, conf, sev, stat, explanations = IOCRiskEngine.evaluate_risk(
        base_reputation=80.0,
        base_confidence=0.85,
        threat_types=["c2", "ransomware"],
        source_feeds=["Feed1", "Feed2", "Feed3"],
        analyst_verdicts=[],
    )
    assert score >= 85.0
    assert conf >= 0.90
    assert sev == IOCSeverity.CRITICAL
    assert stat == IOCStatus.ACTIVE
    assert any("critical threat categories" in exp.lower() for exp in explanations)


# ========================================================
# 5. Analyst Feedback Overrides Test
# ========================================================
def test_analyst_feedback_overrides():
    """Verify false positive feedback dampens risk to 0 and revokes indicator."""
    now = datetime.now(timezone.utc)
    fp_feedback = AnalystFeedback(
        feedback_id="fb-test-01",
        ioc_id="ioc-1",
        analyst_id="lead.analyst@finguard.internal",
        verdict=AnalystVerdict.FALSE_POSITIVE,
        notes="Internal authorized penetration testing IP.",
        timestamp=now,
    )

    score, conf, sev, stat, explanations = IOCRiskEngine.evaluate_risk(
        base_reputation=95.0,
        base_confidence=0.90,
        threat_types=["c2"],
        source_feeds=["Feed1"],
        analyst_verdicts=[fp_feedback],
    )
    assert score == 0.0
    assert stat == IOCStatus.REVOKED
    assert any("false_positive" in exp.lower() for exp in explanations)


# ========================================================
# 6. SQLite Reputation Cache with TTL Test
# ========================================================
def test_sqlite_reputation_cache_ttl(temp_cache):
    """Verify SQLite indicator storage, retrieval, and TTL purge."""
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(hours=1)

    rec = IOCRecord(
        ioc_id="ioc-test-exp",
        type=IOCType.IPV4,
        value="203.0.113.99",
        threat_types=["scanner"],
        reputation_score=60.0,
        confidence=0.80,
        severity=IOCSeverity.MEDIUM,
        status=IOCStatus.ACTIVE,
        first_seen=now,
        last_seen=now,
        expires_at=expired_time,
        source_feeds=["TestFeed"],
    )

    temp_cache.set_ioc(rec)

    # Expired indicator should not be returned by get_ioc
    assert temp_cache.get_ioc("203.0.113.99") is None

    # Purge should clean it up
    purged = temp_cache.purge_expired()
    assert purged == 1


# ========================================================
# 7. Offline Fixture Provider Test
# ========================================================
def test_offline_fixture_provider():
    """Verify high-fidelity offline fixtures for known banking threats."""
    provider = OfflineFixtureProvider()

    record_ip = provider.enrich("198.51.100.42", IOCType.IPV4)
    assert record_ip is not None
    assert record_ip.reputation_score >= 85.0
    assert "c2" in record_ip.threat_types
    assert any(m.technique_id == "T1071" for m in record_ip.mitre_attack)

    record_hash = provider.enrich("44d88612fea8a8f36de82e1278abb02f", IOCType.MD5)
    assert record_hash is not None
    assert record_hash.severity == IOCSeverity.CRITICAL


# ========================================================
# 8. Threat Hunting Rule Evaluation Test
# ========================================================
def test_threat_hunting_rule_evaluation(temp_cache):
    """Verify rule evaluation against security events and indicator correlation."""
    # Seed cache with known malicious IP
    now = datetime.now(timezone.utc)
    temp_cache.set_ioc(
        IOCRecord(
            ioc_id="ioc-c2-test",
            type=IOCType.IPV4,
            value="198.51.100.42",
            threat_types=["c2"],
            reputation_score=95.0,
            confidence=0.95,
            severity=IOCSeverity.CRITICAL,
            status=IOCStatus.ACTIVE,
            first_seen=now,
            last_seen=now,
            source_feeds=["TestFeed"],
        )
    )

    hunter = ThreatHunter(cache=temp_cache)
    rule = ThreatHuntingRule(
        rule_id="HUNT-TEST-001",
        name="C2 Outbound Traffic",
        description="Matches outbound network calls to known C2 node.",
        severity="HIGH",
        mitre_technique_id="T1071",
        conditions={
            "logic": "OR",
            "conditions": [
                {"field": "source_ip", "operator": "matches_ioc"},
            ],
        },
        enabled=True,
    )

    events = [
        {"event_id": "e1", "source_ip": "198.51.100.42", "source": "CloudTrail"},
        {"event_id": "e2", "source_ip": "10.0.0.1", "source": "VPCFlow"},
    ]

    result = hunter.evaluate_rule(rule, events)
    assert result is not None
    assert len(result.matched_events) == 1
    assert result.matched_events[0]["event_id"] == "e1"
    assert "198.51.100.42" in result.matched_iocs


# ========================================================
# 9. API List IOCs & Detail (Authorized) Test
# ========================================================
def test_api_list_iocs_and_detail_authorized(client):
    """Verify authenticated analyst can list and inspect indicators."""
    token = create_test_token(roles=["Analyst"], email="analyst@finguard.internal")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/threat-intel/iocs", headers=headers)
    assert resp.status_code == 200
    iocs = resp.json()
    assert isinstance(iocs, list)
    assert len(iocs) >= 1

    first_id = iocs[0]["ioc_id"]
    resp_detail = client.get(f"/threat-intel/iocs/{first_id}", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["ioc_id"] == first_id


# ========================================================
# 10. API Indicator Enrichment & Hunting Endpoints Test
# ========================================================
def test_api_enrich_and_hunt_endpoints(client):
    """Verify batch indicator enrichment and event hunting execution via API."""
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    headers = {"Authorization": f"Bearer {token}"}

    # Enrichment API
    enrich_payload = {
        "indicators": ["198.51.100.42", "evil-bank-login.com"],
        "force_refresh": False,
    }
    resp_enrich = client.post("/threat-intel/enrich", json=enrich_payload, headers=headers)
    assert resp_enrich.status_code == 200
    enrich_data = resp_enrich.json()
    assert enrich_data["total_processed"] == 2
    assert len(enrich_data["enriched"]) == 2

    # Threat Hunting API
    hunt_payload = {
        "events": [
            {"event_id": "evt-hunt-1", "source_ip": "198.51.100.42", "source": "CloudTrail", "event_type": "NetworkConnection"}
        ]
    }
    resp_hunt = client.post("/threat-intel/hunt", json=hunt_payload, headers=headers)
    assert resp_hunt.status_code == 200
    hunt_results = resp_hunt.json()
    assert isinstance(hunt_results, list)
    assert len(hunt_results) >= 1


# ========================================================
# 11. API Analyst Feedback & MITRE Taxonomy Catalog Test
# ========================================================
def test_api_analyst_feedback_and_mitre(client):
    """Verify submitting analyst adjudication adjusts reputation and MITRE catalog returns."""
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch an indicator ID
    resp_list = client.get("/threat-intel/iocs", headers=headers)
    iocs = resp_list.json()
    target_ioc = iocs[0]

    # Submit feedback (True Positive)
    fb_payload = {
        "ioc_id": target_ioc["ioc_id"],
        "verdict": "TRUE_POSITIVE",
        "notes": "Verified malicious proxy connection in SOC incident #402.",
    }
    resp_fb = client.post("/threat-intel/feedback", json=fb_payload, headers=headers)
    assert resp_fb.status_code == 200
    updated_data = resp_fb.json()
    assert updated_data["confidence"] == 1.0
    assert updated_data["status"] == "ACTIVE"

    # MITRE Taxonomy API
    resp_mitre = client.get("/threat-intel/mitre", headers=headers)
    assert resp_mitre.status_code == 200
    mitre_list = resp_mitre.json()
    assert len(mitre_list) >= 5
    assert any(m["technique_id"] == "T1071" for m in mitre_list)
