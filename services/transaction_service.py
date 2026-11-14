"""
FinGuard AI — Phase 34: Transaction Microservice.
Standalone containerized FastAPI microservice running on port 8101.
Includes Kubernetes startup, liveness, and readiness probes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from events.models import InitiateTransactionRequest
from events.service import microservices_coordinator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [txn-service]: %(message)s")
logger = logging.getLogger("transaction-service")

app = FastAPI(
    title="FinGuard AI — Transaction Microservice",
    version="1.0.0",
    description="Dedicated microservice for transaction lifecycle, outbox persistence, and Saga coordination.",
)

_SERVICE_READY = True
_SERVICE_ALIVE = True


@app.get("/health", summary="Service Health Check")
def health():
    return {
        "status": "healthy",
        "service": "transaction-service",
        "port": 8101,
        "version": "1.0.0",
        "ready": _SERVICE_READY,
        "alive": _SERVICE_ALIVE,
    }


@app.get("/live", summary="Kubernetes Liveness Probe")
def liveness():
    if not _SERVICE_ALIVE:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Liveness check failed")
    return {"status": "alive"}


@app.get("/ready", summary="Kubernetes Readiness Probe")
def readiness():
    if not _SERVICE_READY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service not ready")
    return {"status": "ready"}


@app.get("/startup", summary="Kubernetes Startup Probe")
def startup():
    return {"status": "started"}


@app.get("/metrics", summary="Prometheus Metrics Endpoint")
def metrics():
    m = microservices_coordinator.get_metrics()
    return {
        "transaction_service_events_published": m.total_events_published,
        "transaction_service_pending_outbox": m.pending_outbox_count,
        "transaction_service_sagas_completed": m.sagas_completed,
        "transaction_service_sagas_compensated": m.sagas_compensated,
    }


@app.post("/transactions", summary="Initiate Transaction")
def initiate_transaction(
    req: InitiateTransactionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    result = microservices_coordinator.process_transaction(req, idempotency_key=idempotency_key)
    return result

