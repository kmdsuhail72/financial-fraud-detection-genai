"""
FinGuard AI — AWS SageMaker Inference Handler.

Implements the standard SageMaker Python SDK inference interface:
- model_fn: Deserializes the EnsembleFraudModel from model_dir.
- input_fn: Deserializes JSON / CSV input payload.
- predict_fn: Executes ensemble scoring.
- output_fn: Formats scoring response as JSON.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Union

import joblib

logger = logging.getLogger("sagemaker-inference")


def model_fn(model_dir: str) -> Any:
    """Loads the model.joblib artifact from SageMaker model directory."""
    model_path = Path(model_dir) / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at: {model_path}")

    logger.info("Loading SageMaker model from: %s", model_path)
    model = joblib.load(str(model_path))
    return model


def input_fn(request_body: Union[str, bytes], request_content_type: str = "application/json") -> Dict[str, Any]:
    """Parses incoming request payload."""
    if request_content_type == "application/json":
        if isinstance(request_body, bytes):
            request_body = request_body.decode("utf-8")
        return json.loads(request_body)
    raise ValueError(f"Unsupported content type: {request_content_type}. Only application/json is supported.")


def predict_fn(input_data: Dict[str, Any], model: Any) -> Dict[str, Any]:
    """Generates real-time predictions for single transaction or batch."""
    if isinstance(input_data, list):
        return model.predict_batch(input_data)
    elif isinstance(input_data, dict):
        if "transactions" in input_data and isinstance(input_data["transactions"], list):
            return model.predict_batch(input_data["transactions"])
        txn_id = input_data.get("transaction_id", "txn-sagemaker")
        features = input_data.get("features", input_data)
        return model.predict_one(txn_id, features)
    else:
        raise ValueError("Invalid input data format.")


def output_fn(prediction: Any, accept: str = "application/json") -> str:
    """Serializes prediction result to JSON."""
    if accept == "application/json" or accept == "*/*":
        return json.dumps(prediction)
    raise ValueError(f"Unsupported accept type: {accept}")

