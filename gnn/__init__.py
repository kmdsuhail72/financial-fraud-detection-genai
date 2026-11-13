"""Phase 18 — Enterprise Graph Neural Networks, Deep Learning & Predictive Fraud Detection."""

from gnn.dataset import GraphDataset, generate_phase18_graph
from gnn.graphsage import ExplainabilityEngine, GraphSAGE, SAGEConv
from gnn.models import (
    BatchNodePredictionRequest,
    BatchNodePredictionResponse,
    EmbeddingExtractionRequest,
    EmbeddingExtractionResponse,
    ExplainableIndicator,
    GNNRiskLevel,
    LinkPredictionRequest,
    LinkPredictionResponse,
    ModelInfoResponse,
    ModelLoadResponse,
    NodePredictionRequest,
    NodePredictionResponse,
)
from gnn.service import GNNModelService, get_gnn_service

__all__ = [
    "GraphDataset",
    "generate_phase18_graph",
    "GraphSAGE",
    "SAGEConv",
    "ExplainabilityEngine",
    "GNNModelService",
    "get_gnn_service",
    "GNNRiskLevel",
    "ExplainableIndicator",
    "NodePredictionRequest",
    "NodePredictionResponse",
    "BatchNodePredictionRequest",
    "BatchNodePredictionResponse",
    "LinkPredictionRequest",
    "LinkPredictionResponse",
    "EmbeddingExtractionRequest",
    "EmbeddingExtractionResponse",
    "ModelInfoResponse",
    "ModelLoadResponse",
]
