"""
Tests for SageMaker inference.py handler script.
"""
import json
import pytest
from pathlib import Path

from sagemaker.inference import model_fn, input_fn, predict_fn, output_fn


def test_sagemaker_inference_pipeline():
    """Verify inference.py functions with real model artifact from Phase 6."""
    model_dir = "artifacts"
    if not (Path(model_dir) / "model.joblib").exists():
        pytest.skip("artifacts/model.joblib not present")

    # 1. model_fn
    model = model_fn(model_dir)
    assert model is not None

    # 2. input_fn
    req_body = json.dumps({
        "transaction_id": "txn-test-01",
        "features": {
            "amount": 25000,
            "currency": "INR",
            "transaction_count_5m_prior": 2,
            "new_device_flag": True,
        }
    })
    parsed = input_fn(req_body, "application/json")
    assert parsed["transaction_id"] == "txn-test-01"

    # 3. predict_fn
    result = predict_fn(parsed, model)
    assert result["transaction_id"] == "txn-test-01"
    assert "fraud_probability" in result
    assert "anomaly_score" in result
    assert "risk_score" in result
    assert "risk_level" in result

    # 4. output_fn
    out_json = output_fn(result, "application/json")
    decoded = json.loads(out_json)
    assert decoded["transaction_id"] == "txn-test-01"

