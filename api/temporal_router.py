"""Phase 19 — Temporal Graph Learning & Real-Time Streaming REST API Router."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from security.audit import audit_logger
from temporal.models import (
    EntityTimelineResponse,
    TemporalIngestRequest,
    TemporalIngestResponse,
    TemporalMetricsResponse,
    TemporalModelInfoResponse,
    TemporalScoreRequest,
    TemporalScoreResponse,
)
from temporal.service import TemporalFraudService, get_temporal_service

logger = logging.getLogger("finguard-temporal-api")

temporal_router = APIRouter(prefix="/temporal", tags=["Temporal Graph Learning & Streaming Fraud Detection"])


def get_actor_info(request: Request) -> Dict[str, Any]:
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


@temporal_router.get("/health")
def get_temporal_health():
    """Returns health status for temporal streaming and model runtime."""
    return {"status": "HEALTHY", "phase": "Phase 19 — Temporal Graph Learning", "service": "temporal_fraud_engine"}


@temporal_router.post("/ingest", response_model=TemporalIngestResponse)
def ingest_temporal_events(
    payload: TemporalIngestRequest,
    request: Request,
    service: TemporalFraudService = Depends(get_temporal_service),
):
    """
    Ingests streaming transaction events or decoded Kinesis Lambda event batches.
    """
    if payload.kinesis_record:
        response = service.ingest_kinesis_batch(payload.kinesis_record)
    elif payload.events:
        response = service.ingest_events(payload.events)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payload must include either 'events' or 'kinesis_record'.",
        )

    actor = get_actor_info(request)
    audit_logger.log(
        actor_sub=actor["sub"],
        actor_email=actor["email"],
        actor_roles=actor["roles"],
        action="temporal:ingest_events",
        resource_type="STREAM",
        resource_id=f"batch-{response.ingested_count}",
        status="SUCCESS",
        details={"ingested": response.ingested_count, "duplicates": response.duplicate_count},
    )
    return response


@temporal_router.post("/score", response_model=TemporalScoreResponse)
def score_temporal_sequence(
    payload: TemporalScoreRequest,
    request: Request,
    service: TemporalFraudService = Depends(get_temporal_service),
):
    """
    Evaluates sequence of temporal transaction states for an entity using PyTorch GRU classifier.
    """
    response = service.score_temporal_sequence(payload)

    actor = get_actor_info(request)
    audit_logger.log(
        actor_sub=actor["sub"],
        actor_email=actor["email"],
        actor_roles=actor["roles"],
        action="temporal:score_sequence",
        resource_type="ENTITY",
        resource_id=payload.entity_id,
        status="SUCCESS",
        details={"fraud_prob": response.sequence_fraud_probability, "burst": response.velocity_burst_detected},
    )
    return response


@temporal_router.get("/entities/{entity_id}/timeline", response_model=EntityTimelineResponse)
def get_entity_timeline(
    entity_id: str,
    limit: int = Query(50, ge=1, le=200),
    service: TemporalFraudService = Depends(get_temporal_service),
):
    """Retrieves chronological transaction progression for an entity."""
    return service.get_entity_timeline(entity_id=entity_id, limit=limit)


@temporal_router.get("/model/info", response_model=TemporalModelInfoResponse)
def get_temporal_model_info(
    service: TemporalFraudService = Depends(get_temporal_service),
):
    """Returns PyTorch GRU model architecture, hidden dimension, and chronological training metrics."""
    return service.get_model_info()


@temporal_router.get("/metrics")
def get_temporal_metrics(
    service: TemporalFraudService = Depends(get_temporal_service),
):
    """Returns summary operational telemetry of temporal graph."""
    stats = service.graph.get_stats()
    return {
        "total_events_in_history": stats["total_global_edges"],
        "unique_entities_tracked": stats["total_entities_tracked"],
        "high_risk_bursts_detected": service.high_risk_burst_count,
        "sliding_window_seconds": stats["window_seconds"],
    }

