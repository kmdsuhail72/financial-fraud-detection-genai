"""
FinGuard AI — SageMaker Real-Time Inference Script.

Standard SageMaker Scikit-learn inference script implementing:
- model_fn: Loads model.joblib
- input_fn: Deserializes JSON payloads
- predict_fn: Runs ensemble fraud & anomaly inference
- output_fn: Formats predictions as JSON response
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Union

import joblib

logger = logging.getLogger("sagemaker-inference")
logger.setLevel(logging.INFO)


def model_fn(model_dir: str) -> Any:
    """
    Deserializes the trained EnsembleFraudModel from the SageMaker model directory.
    """
    model_path = Path(model_dir) / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"model.joblib not found in model_dir: {model_dir}")

    logger.info("Loading SageMaker model from: %s", model_path)
    model = joblib.load(str(model_path))
    return model


def input_fn(request_body: Union[str, bytes], request_content_type: str = "application/json") -> Dict[str, Any]:
    """
    Deserializes incoming HTTP request body into Python dictionary.
    """
    if "application/json" in request_content_type:
        if isinstance(request_body, bytes):
            request_body = request_body.decode("utf-8")
        return json.loads(request_body)
    raise ValueError(f"Unsupported content type: {request_content_type}. FinGuard endpoint accepts application/json.")


def predict_fn(input_data: Union[Dict[str, Any], List[Dict[str, Any]]], model: Any) -> Any:
    """
    Executes real-time inference using the loaded EnsembleFraudModel.
    """
    if isinstance(input_data, list):
        return model.predict_batch(input_data)
    elif isinstance(input_data, dict):
        if "transactions" in input_data and isinstance(input_data["transactions"], list):
            return model.predict_batch(input_data["transactions"])

        txn_id = input_data.get("transaction_id", "txn-online")
        features = input_data.get("features", input_data)
        return model.predict_one(txn_id, features)
    else:
        raise ValueError(f"Invalid input data type: {type(input_data)}")


def output_fn(prediction: Any, accept: str = "application/json") -> str:
    """
    Serializes model prediction results into JSON string.
    """
    if "application/json" in accept or "*/*" in accept or accept == "":
        return json.dumps(prediction)
    raise ValueError(f"Unsupported accept type: {accept}. FinGuard endpoint returns application/json.")

