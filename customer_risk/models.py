"""
FinGuard AI — Phase 28: Unified Customer Risk Intelligence Models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class RiskDomain(str, Enum):
    KYC = "KYC"
    AML = "AML"
    FRAUD = "FRAUD"
    IDENTITY = "IDENTITY"
    SANCTIONS = "SANCTIONS"
    PEP = "PEP"
    BEHAVIORAL = "BEHAVIORAL"


DEFAULT_DOMAIN_WEIGHTS: Dict[RiskDomain, float] = {
    RiskDomain.KYC: 0.18,
    RiskDomain.AML: 0.22,
    RiskDomain.FRAUD: 0.20,
    RiskDomain.IDENTITY: 0.16,
    RiskDomain.SANCTIONS: 0.14,
    RiskDomain.PEP: 0.05,
    RiskDomain.BEHAVIORAL: 0.05,
}


class CustomerRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DomainSignal(BaseModel):
    domain: RiskDomain
    score: float = Field(..., ge=0.0, le=100.0, description="Raw domain risk score")
    raw_weight: float = Field(..., description="Default domain weight (e.g. 0.18)")
    normalized_weight: float = Field(..., description="Renormalized weight based on active domains")
    weighted_contribution: float = Field(..., description="Contribution to composite score")
    source_reference: str = Field(..., description="Upstream source reference (e.g. Phase 25 CDD, Phase 27 Graph)")
    indicators: List[str] = Field(default_factory=list, description="Key factors driving this domain score")


class PreviousAssessmentComparison(BaseModel):
    previous_assessment_id: str
    previous_score: float
    previous_risk_level: CustomerRiskLevel
    score_delta: float
    direction: str = Field(..., description="INCREASED, DECREASED, STABLE")
    assessed_at: datetime


class CustomerRiskAssessment(BaseModel):
    assessment_id: str
    customer_id: str
    customer_name: str
    composite_risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: CustomerRiskLevel
    signal_coverage_percent: float = Field(..., ge=0.0, le=100.0, description="Cumulative weight of active domains")
    active_domains_count: int
    total_domains_count: int = 7
    domain_signals: Dict[str, DomainSignal]
    primary_risk_drivers: List[str]
    previous_comparison: Optional[PreviousAssessmentComparison] = None
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None


class CustomerAssessmentRequest(BaseModel):
    customer_id: str
    customer_name: str
    kyc_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    aml_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    fraud_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    identity_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    sanctions_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    pep_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    behavioral_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    indicators: Optional[Dict[str, List[str]]] = Field(default_factory=dict)
    sources: Optional[Dict[str, str]] = Field(default_factory=dict)
    notes: Optional[str] = None


class RiskAssessmentHistory(BaseModel):
    customer_id: str
    assessments: List[CustomerRiskAssessment]
