"""
FinGuard AI — Phase 29: Payment Fraud Intelligence Models.
Defines schemas for payment events, rails, signals, assessments, and aggregations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PaymentRail(str, Enum):
    UPI = "UPI"
    IMPS = "IMPS"
    NEFT = "NEFT"
    RTGS = "RTGS"
    CARD = "CARD"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AlertAction(str, Enum):
    MONITOR = "MONITOR"
    REVIEW = "REVIEW"
    PRIORITY_REVIEW = "PRIORITY_REVIEW"


class PaymentDeviceContext(BaseModel):
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class PaymentEvent(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction reference ID")
    customer_id: str = Field(..., description="Originating customer ID")
    amount: float = Field(..., gt=0, description="Transaction amount (e.g. in INR)")
    currency: str = Field(default="INR", description="Three-letter currency code")
    payment_rail: PaymentRail = Field(default=PaymentRail.UPI, description="Payment rail used")
    sender_account: Optional[str] = Field(default=None, description="Source account or VPA")
    beneficiary_account: str = Field(..., description="Destination account or VPA")
    beneficiary_name: Optional[str] = Field(default=None, description="Beneficiary registered name")
    is_new_beneficiary: bool = Field(default=False, description="Flag indicating first-time transfer to payee")
    customer_home_city: Optional[str] = Field(default=None, description="Customer registered home city")
    transaction_city: Optional[str] = Field(default=None, description="Geographic origin city of transaction")
    is_international: bool = Field(default=False, description="Flag indicating international cross-border flow")
    device_context: Optional[PaymentDeviceContext] = Field(default=None, description="Device and client telemetry")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Transaction timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom operational metadata")

    model_config = ConfigDict(extra="allow")


class PaymentRiskSignal(BaseModel):
    signal_name: str
    points: int
    category: str
    description: str

    model_config = ConfigDict(extra="allow")


class PaymentAssessmentResponse(BaseModel):
    assessment_id: str
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    payment_rail: PaymentRail
    risk_score: int = Field(..., ge=0, le=100, description="Payment risk score (0-100)")
    risk_level: RiskLevel
    action: AlertAction
    signals: List[PaymentRiskSignal]
    summary: str
    assessed_at: datetime
    disclaimer: str = Field(
        default="Illustrative operational risk indicators for analyst prioritization. "
                "No automated payment rejection, reversal, or account freezing is implemented."
    )

    model_config = ConfigDict(extra="allow")


class PaymentMetrics(BaseModel):
    total_assessed: int
    monitor_count: int
    review_count: int
    priority_review_count: int
    avg_risk_score: float
    high_value_count: int
    new_beneficiary_count: int
    city_mismatch_count: int
    velocity_flagged_count: int
    international_count: int

    model_config = ConfigDict(extra="allow")
