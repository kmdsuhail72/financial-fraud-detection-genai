"""Domain and API Schemas for Phase 20 Enterprise Fraud Decision Engine & Risk Fusion."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskPriority(str, Enum):
    P0 = "P0"  # Critical Risk (Escalate to Senior Fraud Specialist immediately)
    P1 = "P1"  # High Risk (Queue for Urgent Analyst Investigation)
    P2 = "P2"  # Medium Risk (Step-Up 2FA / Behavioral Monitoring)
    P3 = "P3"  # Low Risk (Standard Transaction Approval)


class DecisionAction(str, Enum):
    APPROVE = "APPROVE"
    MONITOR = "MONITOR"
    CHALLENGE = "CHALLENGE"
    ESCALATE = "ESCALATE"


class FraudClassification(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalPayload(BaseModel):
    """Multi-signal risk inputs across specialized FinGuard AI detection pillars."""
    ml_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Phase 7 Ensemble ML fraud probability")
    ueba_anomaly_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Phase 14 Behavioral UEBA deviation score")
    graph_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Phase 16-18 Graph / GNN relationship risk score")
    temporal_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Phase 19 Temporal sequence & velocity burst risk")
    threat_intel_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Phase 13 Threat intelligence IOC reputation risk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual flags, IP, Device, Merchant info")

    model_config = ConfigDict(extra="allow")


class DecisionRequest(BaseModel):
    """Incoming transaction decision request with multi-signal telemetry."""
    transaction_id: str = Field(..., description="Unique transaction identifier, e.g. TXN-20261113-0091")
    account_id: str = Field(..., description="Account entity ID")
    customer_id: Optional[str] = Field(None, description="Customer entity ID")
    amount: float = Field(..., ge=0.0, description="Transaction payment amount")
    currency: str = Field("USD", description="ISO currency code")
    signals: SignalPayload = Field(..., description="Multi-signal scores across 5 risk pillars")
    custom_policy_id: Optional[str] = Field(None, description="Optional custom risk policy override")

    model_config = ConfigDict(extra="allow")


class SignalContribution(BaseModel):
    """Detailed attribution of a single risk signal in composite decision score."""
    signal_name: str
    raw_score: float
    effective_weight: float
    weighted_score: float
    percentage_contribution: float


class RiskPolicyConfig(BaseModel):
    """Configurable risk policy with threshold boundaries and normalized signal weights."""
    policy_id: str = Field("POL-DEFAULT-V1", description="Policy identifier")
    policy_version: str = Field("2026.11-v1", description="Semantic policy version")
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "ml": 0.35,
            "ueba": 0.20,
            "graph": 0.20,
            "temporal": 0.15,
            "threat_intel": 0.10,
        },
        description="Base signal weights summing to 1.0",
    )
    thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "low_max": 0.35,      # 0.00 <= score <= 0.35 -> LOW / P3
            "medium_max": 0.70,   # 0.35 < score <= 0.70 -> MEDIUM / P2
            "high_max": 0.90,     # 0.70 < score <= 0.90 -> HIGH / P1
                                  # 0.90 < score <= 1.00 -> CRITICAL / P0
        },
        description="Classification score boundary thresholds",
    )
    description: str = "Default enterprise multi-signal fraud risk orchestration policy."

    model_config = ConfigDict(extra="allow")


class FraudDecisionResponse(BaseModel):
    """Comprehensive orchestrated fraud decision output with explainability and priority."""
    decision_id: str = Field(..., description="Unique generated decision reference, e.g. DEC-20261113-ABC123")
    transaction_id: str
    account_id: str
    timestamp: float
    composite_risk_score: float = Field(..., ge=0.0, le=1.0)
    classification: FraudClassification
    priority: RiskPriority
    recommended_action: DecisionAction
    signal_coverage_pct: float = Field(..., ge=0.0, le=100.0)
    signals_evaluated: int
    signal_contributions: List[SignalContribution]
    risk_reasons: List[str]
    policy_version: str
    is_advisory: bool = True

    model_config = ConfigDict(extra="allow")

