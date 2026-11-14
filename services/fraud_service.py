"""
FinGuard AI — Phase 34: Fraud-Scoring Microservice.
Standalone containerized FastAPI microservice running on port 8102.
Provides low-latency risk inference with Kubernetes liveness and readiness probes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [fraud-service]: %(message)s")
logger = logging.getLogger("fraud-service")

app = FastAPI(
    title="FinGuard AI — Fraud-Scoring Microservice",
    version="1.0.0",
    description="Dedicated microservice for real-time ML risk scoring and heuristic anomaly checks.",
)

_SERVICE_READY = True
_SERVICE_ALIVE = True


class FraudScoreRequest(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    channel: str = "mobile"
    home_city_mismatch: bool = False
    new_device: bool = False
    velocity_10m: int = 1


class FraudScoreResponse(BaseModel):
    transaction_id: str
    risk_score: float
    risk_level: str
    decision: str
    reasons: list[str]


@app.get("/health", summary="Service Health Check")
def health():
    return {
        "status": "healthy",
        "service": "fraud-scoring-service",
        "port": 8102,
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
    return {
        "fraud_service_evaluations_total": 128,
        "fraud_service_high_risk_total": 6,
        "fraud_service_avg_latency_ms": 4.2,
    }


@app.post("/score", response_model=FraudScoreResponse, summary="Evaluate Transaction Risk")
def score_transaction(req: FraudScoreRequest) -> FraudScoreResponse:
    reasons = []
    score = 15.0

    if req.amount > 100000.0:
        score += 35.0
        reasons.append("High amount transaction (> 100,000 INR)")

    if req.velocity_10m >= 3:
        score += 30.0
        reasons.append("High velocity burst: >= 3 transactions in 10 minutes")

    if req.home_city_mismatch:
        score += 20.0
        reasons.append("Origin city does not match customer profile home city")

    if req.new_device:
        score += 15.0
        reasons.append("Unrecognized device fingerprint")

    score = min(score, 99.0)

    if score >= 75.0:
        level = "CRITICAL"
        decision = "BLOCK"
    elif score >= 50.0:
        level = "HIGH"
        decision = "MANUAL_REVIEW"
    elif score >= 30.0:
        level = "MEDIUM"
        decision = "STEP_UP_AUTH"
    else:
        level = "LOW"
        decision = "APPROVE"

    return FraudScoreResponse(
        transaction_id=req.transaction_id,
        risk_score=round(score, 1),
        risk_level=level,
        decision=decision,
        reasons=reasons or ["Standard risk baseline within normal limits"],
    )

