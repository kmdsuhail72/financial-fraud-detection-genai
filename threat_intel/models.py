"""Data models and schemas for FinGuard AI Enterprise Threat Intelligence & MITRE ATT&CK Mapping."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IOCType(str, Enum):
    IPV4 = "ipv4"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"


class IOCSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class IOCStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    UNDER_REVIEW = "UNDER_REVIEW"


class AnalystVerdict(str, Enum):
    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    BENIGN = "BENIGN"
    SUSPICIOUS = "SUSPICIOUS"


class MITRETactic(str, Enum):
    INITIAL_ACCESS = "Initial Access"
    EXECUTION = "Execution"
    PERSISTENCE = "Persistence"
    PRIVILEGE_ESCALATION = "Privilege Escalation"
    DEFENSE_EVASION = "Defense Evasion"
    CREDENTIAL_ACCESS = "Credential Access"
    DISCOVERY = "Discovery"
    LATERAL_MOVEMENT = "Lateral Movement"
    COLLECTION = "Collection"
    COMMAND_AND_CONTROL = "Command and Control"
    EXFILTRATION = "Exfiltration"
    IMPACT = "Impact"


class MITRETechnique(BaseModel):
    """Represents a specific technique within the MITRE ATT&CK enterprise matrix."""
    technique_id: str = Field(..., description="e.g. T1078, T1071, T1566")
    name: str = Field(..., description="e.g. Valid Accounts, Application Layer Protocol")
    tactic: str = Field(..., description="e.g. Defense Evasion, Command and Control")
    description: str = Field(..., description="Technique operational summary")
    url: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class AnalystFeedback(BaseModel):
    """Analyst review feedback and adjudication on an enriched indicator."""
    feedback_id: str
    ioc_id: str
    analyst_id: str
    verdict: AnalystVerdict
    notes: Optional[str] = None
    confidence_adjustment: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="allow")


class IOCRecord(BaseModel):
    """Enriched, normalized threat intelligence indicator record."""
    ioc_id: str = Field(..., description="Unique indicator identifier (e.g. ioc-sha256-...)")
    type: IOCType = Field(..., description="Classification (ipv4, domain, url, md5, sha1, sha256)")
    value: str = Field(..., description="The raw indicator string")
    threat_types: List[str] = Field(default_factory=list, description="Threat categories: c2, phishing, ransomware, botnet")
    reputation_score: float = Field(..., ge=0.0, le=100.0, description="Risk score 0-100 (100 = malicious)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in assessment (0.0 to 1.0)")
    severity: IOCSeverity = Field(IOCSeverity.INFO, description="Threat severity level")
    status: IOCStatus = Field(IOCStatus.ACTIVE, description="Lifecycle status")
    mitre_attack: List[MITRETechnique] = Field(default_factory=list, description="Associated ATT&CK techniques")
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    source_feeds: List[str] = Field(default_factory=list, description="Feeds confirming this indicator")
    analyst_verdicts: List[AnalystFeedback] = Field(default_factory=list, description="Human review history")
    tags: List[str] = Field(default_factory=list, description="Tags: e.g. apt29, tor-exit, bulletproof-host")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider metadata: ASN, country, registrar")

    model_config = ConfigDict(extra="allow")


class ThreatHuntingRule(BaseModel):
    """Configurable rule to detect suspicious patterns and IOC matches in security events."""
    rule_id: str = Field(..., description="Unique rule ID e.g. HUNT-RULE-001")
    name: str = Field(..., description="Descriptive hunting rule name")
    description: str = Field(..., description="Hypothesis and target technique")
    severity: str = Field("HIGH", description="Finding severity")
    mitre_technique_id: str = Field(..., description="Associated MITRE technique e.g. T1071")
    conditions: Dict[str, Any] = Field(..., description="Condition tree or field matcher")
    enabled: bool = True

    model_config = ConfigDict(extra="allow")


class ThreatHuntResult(BaseModel):
    """Result of a threat hunting operation across events and indicators."""
    hunt_id: str
    rule_id: str
    rule_name: str
    mitre_technique_id: str
    matched_events: List[Dict[str, Any]] = Field(default_factory=list)
    matched_iocs: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str

    model_config = ConfigDict(extra="allow")


class IOCEnrichmentRequest(BaseModel):
    """Request payload to enrich one or more indicators."""
    indicators: List[str] = Field(..., min_length=1, description="List of raw indicator strings")
    force_refresh: bool = False


class IOCEnrichmentResponse(BaseModel):
    """Response payload containing enriched IOC records and failed extractions."""
    enriched: List[IOCRecord] = Field(default_factory=list)
    unrecognized: List[str] = Field(default_factory=list)
    total_processed: int
    cache_hits: int = 0

