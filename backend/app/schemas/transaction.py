"""
Pydantic Schemas for Transaction Processing & Fraud Scoring.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LocationSchema(BaseModel):
    country: str = Field(min_length=2, max_length=2, json_schema_extra={"example": "IN"})
    city: str = Field(json_schema_extra={"example": "Kolkata"})


class TransactionCreate(BaseModel):
    transaction_id: str = Field(pattern=r"^TXN-[0-9]{8}-[0-9]{6}$", json_schema_extra={"example": "TXN-20261112-000001"})
    account_id: str = Field(pattern=r"^ACC-[0-9]{6}$", json_schema_extra={"example": "ACC-100045"})
    customer_id: str = Field(pattern=r"^CUS-[0-9]{6}$", json_schema_extra={"example": "CUS-200045"})
    transaction_type: str = Field(json_schema_extra={"example": "CARD_PAYMENT"})
    amount: float = Field(gt=0, json_schema_extra={"example": 87500.00})
    currency: str = Field(default="INR", min_length=3, max_length=3)
    merchant_id: str = Field(json_schema_extra={"example": "MER-90012"})
    merchant_category: str = Field(json_schema_extra={"example": "ELECTRONICS"})
    transaction_timestamp: datetime
    channel: str = Field(json_schema_extra={"example": "MOBILE"})
    location: LocationSchema
    device_id: str = Field(json_schema_extra={"example": "DEV-45002"})
    ip_address: str = Field(json_schema_extra={"example": "192.0.2.10"})
    is_international: bool = False


class TransactionResponse(TransactionCreate):
    model_config = ConfigDict(from_attributes=True)
    status: str
    created_at: datetime


class FraudScoreRequest(BaseModel):
    transaction_id: str
    amount: float
    avg_amount_24h: float
    transaction_count_5m: int
    transaction_count_1h: int
    amount_deviation: float
    new_device: bool
    location_change: bool
    is_international: bool
    merchant_risk: float
    account_age_days: int


class FraudScoreResponse(BaseModel):
    transaction_id: str
    xgboost_probability: float
    isoforest_anomaly_score: float
    unified_risk_score: float
    risk_level: str
    recommended_action: str
    latency_ms: float
