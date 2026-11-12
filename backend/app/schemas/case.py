"""
Pydantic Schemas for Investigation Cases and Decisions.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CaseAssignRequest(BaseModel):
    assigned_to: UUID = Field(description="UUID of the investigator")


class InvestigatorDecisionRequest(BaseModel):
    decision: str = Field(json_schema_extra={"example": "CONFIRMED_FRAUD"})
    action_taken: str = Field(json_schema_extra={"example": "ACCOUNT_FROZEN"})
    notes: str = Field(min_length=10, json_schema_extra={"example": "Confirmed unauthorized takeover with account holder."})


class CaseEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    case_id: str
    evidence_type: str
    description: str
    source: str
    confidence_score: Optional[float] = None
    created_at: datetime


class CaseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    transaction_id: str
    risk_score: float
    risk_level: str
    status: str
    priority: str
    assigned_to: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    evidence: List[CaseEvidenceResponse] = []
