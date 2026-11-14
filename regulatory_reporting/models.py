"""
FinGuard AI — Phase 30: Enterprise Regulatory Reporting Models.
Defines schemas for SAR/STR preparation, validation, approval workflows, submission tracking, and audit logging.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReportType(str, Enum):
    SAR = "SAR"  # Suspicious Activity Report
    STR = "STR"  # Suspicious Transaction Report


class ReportStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETURNED_TO_DRAFT = "RETURNED_TO_DRAFT"
    SUBMITTED = "SUBMITTED"


class RegulatoryJurisdiction(str, Enum):
    FIU_IND = "FIU_IND"  # Financial Intelligence Unit - India
    FINCEN = "FINCEN"    # Financial Crimes Enforcement Network (US)
    FCA = "FCA"          # Financial Conduct Authority (UK)
    GLOBAL = "GLOBAL"


class ReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETURN_TO_DRAFT = "RETURN_TO_DRAFT"


class ValidationErrorItem(BaseModel):
    field: str
    message: str
    severity: str = "ERROR"  # "ERROR" or "WARNING"

    model_config = ConfigDict(extra="allow")


class ReportValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="allow")


class ReportAuditEvent(BaseModel):
    event_id: str
    report_id: str
    action: str
    performed_by: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="allow")


class RegulatoryReport(BaseModel):
    report_id: str = Field(..., description="Unique SAR/STR report reference")
    report_type: ReportType = Field(default=ReportType.SAR)
    jurisdiction: RegulatoryJurisdiction = Field(default=RegulatoryJurisdiction.FIU_IND)
    status: ReportStatus = Field(default=ReportStatus.DRAFT)
    case_id: Optional[str] = Field(default=None, description="Linked AML/Fraud Case ID")
    customer_id: str = Field(..., description="Subject customer ID")
    customer_name: str = Field(..., description="Subject customer legal name")
    customer_pan_or_id: Optional[str] = Field(default=None, description="Tax ID / PAN / SSN")
    suspicion_narrative: str = Field(..., description="Comprehensive factual summary of suspicious conduct")
    primary_offense_category: str = Field(..., description="Primary predicate offense (e.g. Structuring, Layering)")
    transaction_ids: List[str] = Field(default_factory=list, description="Linked suspicious transactions")
    evidence_ids: List[str] = Field(default_factory=list, description="Linked digital/documentary evidence IDs")
    total_suspicious_amount: float = Field(..., ge=0, description="Total aggregated suspicious amount")
    currency: str = Field(default="INR")
    created_by: str = Field(default="compliance_analyst@finguard.internal")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filing_deadline: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
        description="Statutory reporting deadline"
    )
    is_overdue: bool = Field(default=False)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    external_filing_reference: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    validation_result: Optional[ReportValidationResult] = None

    model_config = ConfigDict(extra="allow")


class ReportCreateRequest(BaseModel):
    report_type: ReportType = ReportType.SAR
    jurisdiction: RegulatoryJurisdiction = RegulatoryJurisdiction.FIU_IND
    case_id: Optional[str] = None
    customer_id: str
    customer_name: str
    customer_pan_or_id: Optional[str] = None
    suspicion_narrative: str
    primary_offense_category: str
    transaction_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    total_suspicious_amount: float = Field(..., ge=0)
    currency: str = "INR"
    created_by: str = "compliance_analyst@finguard.internal"
    filing_deadline_days: int = 30

    model_config = ConfigDict(extra="allow")


class ReviewReportRequest(BaseModel):
    decision: ReviewDecision
    reviewer: str
    rationale: str

    model_config = ConfigDict(extra="allow")


class SubmitReportRequest(BaseModel):
    external_filing_reference: str = Field(..., description="Official regulator submission/acknowledgment number")
    submitted_by: str
    submission_notes: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class ReportingMetrics(BaseModel):
    total_reports: int
    draft_count: int
    under_review_count: int
    approved_count: int
    submitted_count: int
    rejected_count: int
    returned_to_draft_count: int
    overdue_count: int
    total_suspicious_amount_reported: float

    model_config = ConfigDict(extra="allow")
