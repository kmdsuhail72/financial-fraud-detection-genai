"""Domain and API Schemas for Phase 18 Graph Neural Network (GraphSAGE) Fraud Detection."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GNNRiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExplainableIndicator(BaseModel):
    """Explainable risk attribution indicator derived from GNN neighborhood & feature weights."""
    feature_name: str
    attribution_score: float = Field(..., description="Relative contribution weight [-1.0, 1.0]")
    description: str


class NodePredictionRequest(BaseModel):
    entity_id: str = Field(..., description="Target node identifier, e.g. ACC-GNN-01")
    include_embeddings: bool = Field(False, description="Whether to include latent embedding vector")
    include_explainability: bool = Field(True, description="Whether to generate explainability indicators")


class NodePredictionResponse(BaseModel):
    entity_id: str
    entity_type: str
    fraud_probability: float = Field(..., ge=0.0, le=1.0)
    advisory_risk_level: GNNRiskLevel
    predicted_label: int = Field(..., description="0 for Benign, 1 for Fraudulent")
    embedding: Optional[List[float]] = None
    explainable_indicators: List[ExplainableIndicator] = Field(default_factory=list)
    recommendation: str
    is_advisory: bool = True

    model_config = ConfigDict(extra="allow")


class BatchNodePredictionRequest(BaseModel):
    entity_ids: List[str] = Field(..., min_length=1, description="List of entity IDs to evaluate")


class BatchNodePredictionResponse(BaseModel):
    predictions: List[NodePredictionResponse]
    total_evaluated: int
    high_risk_count: int


class LinkPredictionRequest(BaseModel):
    source_id: str = Field(..., description="Origin node identifier")
    target_id: str = Field(..., description="Destination node identifier")


class LinkPredictionResponse(BaseModel):
    source_id: str
    target_id: str
    link_score: float = Field(..., ge=0.0, le=1.0, description="Predicted probability or similarity of association")
    is_suspicious_link: bool
    advisory_assessment: str

    model_config = ConfigDict(extra="allow")


class EmbeddingExtractionRequest(BaseModel):
    entity_ids: Optional[List[str]] = Field(None, description="Optional subset of entity IDs; if omitted, returns all")


class EmbeddingExtractionResponse(BaseModel):
    embeddings: Dict[str, List[float]]
    dimension: int
    total_entities: int


class ModelInfoResponse(BaseModel):
    model_name: str
    architecture: str
    input_dim: int
    hidden_dim: int
    output_dim: int
    num_parameters: int
    is_loaded: bool
    metrics: Dict[str, float]
    device: str
    checkpoint_path: Optional[str] = None


class ModelLoadResponse(BaseModel):
    status: str
    message: str
    model_path: str
    parameters_loaded: int
    architecture: str

