"""Phase 18 — Graph Neural Network (GraphSAGE) REST API Router."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from gnn.models import (
    BatchNodePredictionRequest,
    BatchNodePredictionResponse,
    EmbeddingExtractionRequest,
    EmbeddingExtractionResponse,
    LinkPredictionRequest,
    LinkPredictionResponse,
    ModelInfoResponse,
    ModelLoadResponse,
    NodePredictionRequest,
    NodePredictionResponse,
)
from gnn.service import GNNModelService, get_gnn_service
from security.audit import audit_logger

logger = logging.getLogger("finguard-gnn-api")

model_router = APIRouter(prefix="/model", tags=["Graph Neural Network & Predictive Deep Learning"])


def get_actor_info(request: Request) -> Dict[str, Any]:
    """Extracts actor details if Authorization header present, else defaults to local analyst."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from security.auth import decode_and_validate_token
            token = auth_header.split(" ")[1]
            user = decode_and_validate_token(token)
            return {"sub": user.sub, "email": user.email, "roles": [r.value for r in user.roles]}
        except Exception:
            pass
    return {"sub": "usr-analyst-local", "email": "analyst@finguard.internal", "roles": ["Analyst"]}


@model_router.post("/load", response_model=ModelLoadResponse)
def load_gnn_model(
    request: Request,
    payload: Optional[Dict[str, str]] = None,
    service: GNNModelService = Depends(get_gnn_service),
):
    """
    Loads trained GraphSAGE model weights into active inference runtime.
    Callable via: curl -X POST http://127.0.0.1:8008/model/load
    """
    model_path = payload.get("path") if payload else None
    response = service.load_model(model_path)

    actor = get_actor_info(request)
    audit_logger.log(
        actor_sub=actor["sub"],
        actor_email=actor["email"],
        actor_roles=actor["roles"],
        action="gnn:load_model",
        resource_type="MODEL",
        resource_id="FinGuard-GraphSAGE",
        status="SUCCESS",
        details={"model_path": response.model_path, "parameters": response.parameters_loaded},
    )
    return response


@model_router.get("/info", response_model=ModelInfoResponse)
def get_gnn_model_info(
    service: GNNModelService = Depends(get_gnn_service),
):
    """Returns active GNN architecture specifications, parameter counts, and benchmark metrics."""
    return service.get_info()


@model_router.post("/predict/node", response_model=NodePredictionResponse)
def predict_node_fraud_risk(
    payload: NodePredictionRequest,
    request: Request,
    service: GNNModelService = Depends(get_gnn_service),
):
    """
    Executes inductive GraphSAGE inference for an entity, computing advisory fraud probability,
    risk category, and explainable feature/neighborhood attributions.
    """
    response = service.predict_node(
        entity_id=payload.entity_id,
        include_embeddings=payload.include_embeddings,
        include_explainability=payload.include_explainability,
    )

    actor = get_actor_info(request)
    audit_logger.log(
        actor_sub=actor["sub"],
        actor_email=actor["email"],
        actor_roles=actor["roles"],
        action="gnn:predict_node",
        resource_type="ENTITY",
        resource_id=payload.entity_id,
        status="SUCCESS",
        details={"fraud_probability": response.fraud_probability, "advisory_level": response.advisory_risk_level.value},
    )
    return response


@model_router.post("/predict/nodes", response_model=BatchNodePredictionResponse)
def predict_batch_node_fraud_risk(
    payload: BatchNodePredictionRequest,
    service: GNNModelService = Depends(get_gnn_service),
):
    """Batch-evaluates network fraud probabilities across multiple entities."""
    return service.predict_batch(payload.entity_ids)


@model_router.post("/predict/link", response_model=LinkPredictionResponse)
def predict_suspicious_link(
    payload: LinkPredictionRequest,
    request: Request,
    service: GNNModelService = Depends(get_gnn_service),
):
    """
    Scores the latent affinity and suspicious association probability between two entities.
    """
    response = service.predict_link(payload.source_id, payload.target_id)

    actor = get_actor_info(request)
    audit_logger.log(
        actor_sub=actor["sub"],
        actor_email=actor["email"],
        actor_roles=actor["roles"],
        action="gnn:predict_link",
        resource_type="EDGE",
        resource_id=f"{payload.source_id}->{payload.target_id}",
        status="SUCCESS",
        details={"link_score": response.link_score, "is_suspicious": response.is_suspicious_link},
    )
    return response


@model_router.post("/embeddings", response_model=EmbeddingExtractionResponse)
def extract_entity_embeddings(
    payload: Optional[EmbeddingExtractionRequest] = None,
    service: GNNModelService = Depends(get_gnn_service),
):
    """
    Extracts 64-dimensional latent entity representations for visual clustering and downstream analytics.
    """
    entity_ids = payload.entity_ids if payload else None
    return service.extract_embeddings(entity_ids)

