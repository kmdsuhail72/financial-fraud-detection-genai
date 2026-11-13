"""Domain and API Schemas for Phase 19 Temporal Graph Learning & Streaming Ingestion."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TemporalRiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TemporalTransactionEvent(BaseModel):
    """Normalized temporal financial event with precise epoch seconds timestamp."""
    transaction_id: str = Field(..., description="Unique event identifier")
    timestamp: float = Field(..., description="Unix epoch timestamp in seconds")
    source_account: str
    target_account: Optional[str] = None
    customer_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    merchant_id: Optional[str] = None
    amount: float = Field(..., ge=0.0)
    currency: str = "USD"
    channel: str = "mobile"
    event_type: str = "TRANSFER"
    is_fraud: Optional[bool] = None

    model_config = ConfigDict(extra="allow")


class TemporalEntityFeatures(BaseModel):
    """Rolling as-of temporal features computed strictly without future lookahead."""
    entity_id: str
    as_of_timestamp: float
    tx_count_5m: int = 0
    tx_count_1h: int = 0
    tx_count_24h: int = 0
    amount_sum_1h: float = 0.0
    amount_avg_24h: float = 0.0
    amount_std_24h: float = 0.0
    velocity_burst_ratio: float = 0.0
    distinct_counterparties_1h: int = 0
    distinct_devices_24h: int = 0
    distinct_ips_24h: int = 0
    is_new_device: bool = False
    is_new_ip: bool = False
    time_since_prior_tx_sec: float = 0.0

    def to_feature_vector(self) -> List[float]:
        """Maps temporal features to normalized 12-dimensional vector for GRU sequence model."""
        return [
            min(1.0, self.tx_count_5m / 10.0),
            min(1.0, self.tx_count_1h / 30.0),
            min(1.0, self.tx_count_24h / 100.0),
            min(1.0, self.amount_sum_1h / 50000.0),
            min(1.0, self.amount_avg_24h / 10000.0),
            min(1.0, self.amount_std_24h / 5000.0),
            min(1.0, self.velocity_burst_ratio / 5.0),
            min(1.0, self.distinct_counterparties_1h / 10.0),
            min(1.0, self.distinct_devices_24h / 5.0),
            1.0 if self.is_new_device else 0.0,
            1.0 if self.is_new_ip else 0.0,
            min(1.0, 1.0 / (self.time_since_prior_tx_sec + 1.0)),
        ]


class TemporalScoreRequest(BaseModel):
    entity_id: str = Field(..., description="Entity ID to evaluate (e.g. ACC-TEMP-01)")
    current_event: Optional[TemporalTransactionEvent] = Field(None, description="Optional incoming event to score")
    sequence_length: int = Field(5, ge=1, le=20, description="Number of historical time-steps to feed into GRU")


class TemporalScoreResponse(BaseModel):
    entity_id: str
    sequence_fraud_probability: float = Field(..., ge=0.0, le=1.0)
    advisory_risk_level: TemporalRiskLevel
    velocity_burst_detected: bool
    features_summary: Dict[str, Any]
    recommendation: str
    timeline_indicators: List[str] = Field(default_factory=list)
    is_advisory: bool = True

    model_config = ConfigDict(extra="allow")


class EntityTimelineResponse(BaseModel):
    entity_id: str
    total_events: int
    events: List[Dict[str, Any]]
    oldest_timestamp: Optional[float] = None
    newest_timestamp: Optional[float] = None


class TemporalIngestRequest(BaseModel):
    events: Optional[List[TemporalTransactionEvent]] = None
    kinesis_record: Optional[Dict[str, Any]] = None


class TemporalIngestResponse(BaseModel):
    status: str
    ingested_count: int
    duplicate_count: int
    error_count: int
    latest_timestamp: Optional[float] = None


class TemporalModelInfoResponse(BaseModel):
    model_name: str
    architecture: str
    input_dim: int
    hidden_dim: int
    num_layers: int
    is_loaded: bool
    device: str
    metrics: Dict[str, float]


class TemporalMetricsResponse(BaseModel):
    total_events_in_history: int
    unique_entities_tracked: int
    high_risk_bursts_detected: int
    sliding_window_seconds: int

