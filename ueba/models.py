"""Domain models and schemas for FinGuard AI User and Entity Behavior Analytics (UEBA)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PeerGroup(str, Enum):
    RETAIL = "RETAIL"
    HIGH_NET_WORTH = "HIGH_NET_WORTH"
    COMMERCIAL = "COMMERCIAL"
    CORPORATE = "CORPORATE"
    INTERNAL_OPERATIONS = "INTERNAL_OPERATIONS"


class EntityRiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BehavioralBaseline(BaseModel):
    """Historical baseline activity metrics for an entity."""
    avg_amount: float = Field(..., ge=0.0, description="Historical mean transaction amount")
    std_amount: float = Field(..., ge=0.0, description="Standard deviation of amount")
    max_amount_historical: float = Field(..., ge=0.0, description="Highest observed amount")
    active_hours: List[int] = Field(default_factory=list, description="Common active hours [0-23]")
    known_devices: List[str] = Field(default_factory=list, description="Registered device fingerprints")
    known_ips: List[str] = Field(default_factory=list, description="Previously observed IP addresses")
    known_cities: List[str] = Field(default_factory=list, description="Frequent transaction cities")
    daily_velocity_mean: float = Field(1.0, ge=0.0, description="Mean transactions per 24 hours")
    hourly_velocity_mean: float = Field(0.2, ge=0.0, description="Mean transactions per hour")

    model_config = ConfigDict(extra="allow")


class UserEntityProfile(BaseModel):
    """Behavioral profile and risk posture for a user or account entity."""
    entity_id: str = Field(..., description="Entity ID e.g. CUS-100045, ACC-801")
    entity_type: str = Field("CUSTOMER", description="CUSTOMER, ACCOUNT, IAM_USER, DEVICE")
    peer_group: PeerGroup = Field(PeerGroup.RETAIL, description="Peer grouping for cohort analysis")
    baseline: BehavioralBaseline
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_events_observed: int = 0
    current_risk_score: float = Field(10.0, ge=0.0, le=100.0)
    risk_level: EntityRiskLevel = Field(EntityRiskLevel.LOW)
    active_anomalies: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class BehavioralFeatures(BaseModel):
    """Point-in-time engineered behavioral deviation features."""
    amount: float
    amount_deviation_ratio: float = Field(1.0, description="Amount / avg_amount")
    amount_z_score: float = Field(0.0, description="Z-score deviation from baseline amount")
    is_off_hours: bool = False
    is_new_device: bool = False
    is_new_ip: bool = False
    is_new_city: bool = False
    velocity_1h: int = 1
    velocity_24h: int = 1
    velocity_z_score: float = 0.0
    impossible_travel_flag: bool = False

    model_config = ConfigDict(extra="allow")


class BehavioralAnomalyResult(BaseModel):
    """Outcome of ML anomaly scoring and rule evaluation for an event."""
    anomaly_id: str
    entity_id: str
    event_id: str
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Isolation Forest anomaly score")
    is_anomaly: bool = False
    rule_flags: List[str] = Field(default_factory=list)
    features: BehavioralFeatures
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    explanation: str

    model_config = ConfigDict(extra="allow")


class FraudThreatCorrelation(BaseModel):
    """Correlated risk assessment combining UEBA, ML fraud, IOC threat intel, and security findings."""
    correlation_id: str
    entity_id: str
    event_id: str
    ueba_anomaly_score: float = Field(..., ge=0.0, le=1.0)
    fraud_probability: float = Field(0.0, ge=0.0, le=1.0)
    ioc_reputation_score: float = Field(0.0, ge=0.0, le=100.0)
    security_finding_severity: float = Field(0.0, ge=0.0, le=10.0)
    blended_risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: EntityRiskLevel
    correlated_signals: List[str] = Field(default_factory=list)
    investigation_recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="allow")


class ScoreEventRequest(BaseModel):
    """Request schema to evaluate behavioral anomaly on an incoming event."""
    entity_id: str
    event_id: str
    amount: float = 0.0
    hour_of_day: Optional[int] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    city: Optional[str] = None
    velocity_1h: int = 1
    velocity_24h: int = 1


class CorrelateRiskRequest(BaseModel):
    """Request schema to blend behavioral anomaly with fraud and security signals."""
    entity_id: str
    event_id: str
    ueba_anomaly_score: float
    fraud_probability: float = 0.0
    ioc_reputation_score: float = 0.0
    security_finding_severity: float = 0.0
