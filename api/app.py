"""
FinGuard AI — Real-Time Transaction Scoring FastAPI Application (Phase 6).

Serves low-latency ML inferences for incoming transactions combining
supervised fraud probability and unsupervised anomaly detection.

Usage:
    export FINGUARD_MODEL_PATH=artifacts/model.joblib
    uvicorn api.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from ml.inference.predictor import EnsembleFraudModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("finguard-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Attempt non-blocking model load at startup."""
    model_path = os.getenv("FINGUARD_MODEL_PATH", "artifacts/model.joblib")
    if Path(model_path).exists():
        try:
            get_model()
        except Exception as e:
            logger.warning("Startup model load deferred: %s", e)
    else:
        logger.info("Model path '%s' not present yet. Model will be loaded on demand.", model_path)
    yield


app = FastAPI(
    title="FinGuard AI — Real-Time Fraud & Anomaly Scoring API",
    version="1.0.0",
    description="Sub-10ms real-time scoring engine integrating Random Forest / XGBoost with Isolation Forest.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model holder
MODEL_HOLDER: Dict[str, Any] = {
    "model": None,
    "model_path": None,
    "load_error": None,
}


def get_model() -> EnsembleFraudModel:
    """Retrieves or lazy-loads the model artifact from FINGUARD_MODEL_PATH."""
    model_path_str = os.getenv("FINGUARD_MODEL_PATH", "artifacts/model.joblib")
    model_path = Path(model_path_str)

    # Check if loaded and path hasn't changed
    if MODEL_HOLDER["model"] is not None and MODEL_HOLDER["model_path"] == str(model_path):
        return MODEL_HOLDER["model"]

    if not model_path.exists():
        err_msg = f"Model artifact not found at: {model_path}. Please run training first or check FINGUARD_MODEL_PATH."
        MODEL_HOLDER["load_error"] = err_msg
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=err_msg)

    try:
        loaded = EnsembleFraudModel.load(str(model_path))
        MODEL_HOLDER["model"] = loaded
        MODEL_HOLDER["model_path"] = str(model_path)
        MODEL_HOLDER["load_error"] = None
        logger.info("Successfully loaded EnsembleFraudModel from %s (version: %s)", model_path, loaded.model_version)
        return loaded
    except Exception as exc:
        err_msg = f"Failed to load model from {model_path}: {exc}"
        MODEL_HOLDER["load_error"] = err_msg
        logger.error(err_msg, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err_msg)


# ==========================================
# Pydantic Schemas
# ==========================================
class TransactionScoreRequest(BaseModel):
    transaction_id: str = Field(..., json_schema_extra={"example": "txn-demo"})
    features: Dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "example": {
                "amount": 12500,
                "currency": "INR",
                "channel": "mobile",
                "transaction_count_5m_prior": 4,
                "transaction_count_1h_prior": 12,
                "new_device_flag": True,
                "home_city_mismatch": False,
                "is_international": True,
            }
        },
    )
    model_config = ConfigDict(extra="allow")


class TransactionScoreResponse(BaseModel):
    transaction_id: str = Field(..., json_schema_extra={"example": "txn-demo"})
    fraud_probability: float = Field(..., json_schema_extra={"example": 0.87})
    anomaly_score: float = Field(..., json_schema_extra={"example": 0.72})
    risk_score: float = Field(..., json_schema_extra={"example": 0.8325})
    risk_level: str = Field(..., json_schema_extra={"example": "HIGH"})
    classifier_threshold: float = Field(..., json_schema_extra={"example": 0.45})
    model_version: str = Field(..., json_schema_extra={"example": "v20261112T100000Z"})


class HealthCheckResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: Optional[str] = None
    model_path: Optional[str] = None
    uptime_seconds: float


START_TIME = time.time()


# ==========================================
# Endpoints
# ==========================================
@app.get("/health", response_model=HealthCheckResponse)
def health():
    """System health and model readiness probe."""
    is_loaded = MODEL_HOLDER["model"] is not None
    version = MODEL_HOLDER["model"].model_version if is_loaded else None
    m_path = MODEL_HOLDER["model_path"]
    return HealthCheckResponse(
        status="HEALTHY" if is_loaded else "INITIALIZING",
        model_loaded=is_loaded,
        model_version=version,
        model_path=m_path,
        uptime_seconds=round(time.time() - START_TIME, 2),
    )


@app.post("/score", response_model=TransactionScoreResponse)
def score_transaction(payload: Union[TransactionScoreRequest, Dict[str, Any]]):
    """
    Real-time fraud scoring for a single transaction.

    Accepts structured features with alias mapping (e.g., amount, new_device_flag).
    """
    model = get_model()

    if isinstance(payload, TransactionScoreRequest):
        txn_id = payload.transaction_id
        features = payload.features
    elif isinstance(payload, dict):
        txn_id = payload.get("transaction_id", f"txn-{int(time.time()*1000)}")
        features = payload.get("features", payload)
    else:
        raise HTTPException(status_code=400, detail="Invalid request body")

    try:
        result = model.predict_one(txn_id, features)
        return TransactionScoreResponse(**result)
    except Exception as exc:
        logger.error("Scoring failure for %s: %s", txn_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference error: {exc}")


@app.post("/score/batch", response_model=List[TransactionScoreResponse])
def score_batch_transactions(transactions: List[TransactionScoreRequest]):
    """Batch scoring for high-throughput streaming batches."""
    model = get_model()
    try:
        txns_raw = [{"transaction_id": t.transaction_id, "features": t.features} for t in transactions]
        results = model.predict_batch(txns_raw)
        return [TransactionScoreResponse(**r) for r in results]
    except Exception as exc:
        logger.error("Batch scoring failure: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch inference error: {exc}")


@app.get("/model/metadata")
def get_model_metadata():
    """Retrieves model governance metadata, thresholds, and input schema."""
    model = get_model()
    return {
        "model_version": model.model_version,
        "model_type": model.model_type,
        "classifier_threshold": model.classifier_threshold,
        "thresholds": model.thresholds,
        "feature_manifest": model.preprocessor.export_manifest(),
    }
