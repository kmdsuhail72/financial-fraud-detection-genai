"""
FinGuard AI — Phase 24 Anti-Money Laundering (AML) Transaction Monitoring & Customer Risk Models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AMLRuleType(str, Enum):
    LARGE_CASH_TRANSACTION = "LARGE_CASH_TRANSACTION"  # >= $10,000 threshold
    POSSIBLE_STRUCTURING = "POSSIBLE_STRUCTURING"      # Smurfing: $8,500 - $9,999 clusters
    RAPID_INFLOW_OUTFLOW = "RAPID_INFLOW_OUTFLOW"      # Layering: large deposit quickly drained (>80%)
    HIGH_VELOCITY = "HIGH_VELOCITY"                    # Burst frequency (e.g. >= 5 txns in 10 mins)


class CustomerRiskTier(str, Enum):
    LOW = "LOW"            # Score 0 - 30
    MEDIUM = "MEDIUM"      # Score 31 - 60
    HIGH = "HIGH"          # Score 61 - 80
    CRITICAL = "CRITICAL"  # Score 81 - 100


class AMLCaseStatus(str, Enum):
    NEW = "NEW"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    ESCALATED = "ESCALATED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"
    REPORT_PREPARED = "REPORT_PREPARED"


class TransactionDirection(str, Enum):
    INFLOW = "INFLOW"
    OUTFLOW = "OUTFLOW"


class AMLTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    direction: TransactionDirection = TransactionDirection.OUTFLOW
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    counterparty: Optional[str] = "UNKNOWN"
    payment_method: str = "WIRE"
    channel: str = "ONLINE"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AMLAlert(BaseModel):
    model_config = ConfigDict(extra="ignore")
    alert_id: str = Field(default_factory=lambda: f"AML-ALT-{uuid.uuid4().hex[:8].upper()}")
    rule_type: AMLRuleType
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    trigger_amount: float
    trigger_transaction_ids: List[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CustomerRiskProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: str
    name: str
    risk_tier: CustomerRiskTier = CustomerRiskTier.LOW
    risk_score: int = 15  # 0 to 100
    account_type: str = "INDIVIDUAL_CHECKING"
    country: str = "US"
    pep_flag: bool = False  # Politically Exposed Person
    risk_factors: List[str] = Field(default_factory=list)
    total_transaction_volume: float = 0.0
    lifetime_aml_alerts_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Alias for backward compatibility
CustomerProfile = CustomerRiskProfile


class CaseActivityEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    activity_id: str = Field(default_factory=lambda: f"ACT-{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)


class CaseNote(BaseModel):
    model_config = ConfigDict(extra="ignore")
    note_id: str = Field(default_factory=lambda: f"NOTE-{uuid.uuid4().hex[:8].upper()}")
    author: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: str


class AMLInvestigationCase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    case_id: str = Field(default_factory=lambda: f"AML-CASE-{uuid.uuid4().hex[:8].upper()}")
    customer_id: str
    status: AMLCaseStatus = AMLCaseStatus.NEW
    alerts: List[AMLAlert] = Field(default_factory=list)
    risk_score: int
    risk_tier: CustomerRiskTier
    assigned_to: Optional[str] = None
    notes: List[CaseNote] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: List[CaseActivityEntry] = Field(default_factory=list)


class SARInvestigationDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    draft_id: str = Field(default_factory=lambda: f"SAR-{uuid.uuid4().hex[:8].upper()}")
    case_id: str
    customer_id: str
    prepared_by: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    suspicious_activity_summary: str
    violating_patterns: List[str]
    total_suspicious_amount: float
    evidence_citations: List[str]
    recommended_disposition: str
    report_markdown: str


class AMLMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total_monitored_transactions: int
    total_alerts_detected: int
    active_investigation_cases: int
    customer_risk_distribution: Dict[str, int]
    alerts_by_rule_type: Dict[str, int]
    avg_case_resolution_time_hours: float

