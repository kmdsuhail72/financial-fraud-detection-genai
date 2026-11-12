"""
Pydantic Schema for Amazon Bedrock Generative AI Investigation Reports.
Ensures strict type-safety and structured validation of AI outputs.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BedrockInvestigationReport(BaseModel):
    """Structured response schema expected from Amazon Bedrock investigation assistant."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "case_id": "CASE-20261112-00001",
                "risk_level": "CRITICAL",
                "executive_summary": "Transaction flagged due to sudden 7x amount surge above customer 24h baseline combined with new device registration and 4 transactions within 5 minutes.",
                "key_evidence": [
                    "Transaction amount (₹87,500) is 7.0x the customer's 24h average of ₹12,500",
                    "Unrecognized device DEV-45002 observed for the first time",
                    "High velocity burst: 4 transactions in 5 minutes"
                ],
                "recommended_actions": [
                    "Contact customer via registered mobile number for two-factor verification",
                    "Temporarily restrict outbound transfers from account ACC-100045",
                    "Review correlated IP 192.0.2.10 against threat intelligence lists"
                ],
                "confidence_rationale": "High confidence based on substantial deviations from 90-day baseline."
            }
        }
    )

    case_id: str = Field(description="Unique investigation case ID")
    risk_level: RiskLevelEnum = Field(description="Assessed risk tier based on evidence")
    executive_summary: str = Field(
        min_length=20,
        max_length=1000,
        description="Concise plain-language explanation of why the transaction was flagged"
    )
    key_evidence: List[str] = Field(
        min_length=1,
        max_length=10,
        description="Factual, verifiable evidence statements grounded in the feature data"
    )
    recommended_actions: List[str] = Field(
        min_length=1,
        max_length=8,
        description="Standard operating procedure actions suggested for the human investigator"
    )
    confidence_rationale: Optional[str] = Field(
        default=None,
        description="Brief note on data quality or limitations in historical baseline"
    )
