"""
FinGuard AI — SageMaker Runtime Client (Phase 7).

Invokes the SageMaker real-time inference endpoint with low-latency JSON payload.
Supports graceful offline fallback for integration and unit testing.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SageMakerScorer:
    """Invokes SageMaker real-time endpoint for transaction fraud and anomaly scoring."""

    def __init__(
        self,
        endpoint_name: str,
        region_name: str = "ap-south-1",
        sagemaker_client: Optional[Any] = None,
        mock_mode: bool = False,
    ):
        self.endpoint_name = endpoint_name
        self.region_name = region_name
        self.mock_mode = mock_mode or endpoint_name.lower() in ("mock", "local", "offline", "")

        if not self.mock_mode and sagemaker_client is None:
            self.client = boto3.client("sagemaker-runtime", region_name=region_name)
        else:
            self.client = sagemaker_client

    def score_transaction(self, transaction_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends transaction features to SageMaker endpoint and returns predictions.

        Returns:
            Dict containing fraud_probability, anomaly_score, risk_score, risk_level, etc.
        """
        if self.mock_mode:
            return self._mock_score(transaction_id, features)

        payload = {
            "transaction_id": transaction_id,
            "features": features,
        }

        try:
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType="application/json",
                Accept="application/json",
                Body=json.dumps(payload),
            )
            body = response["Body"].read().decode("utf-8")
            result = json.loads(body)
            return result
        except ClientError as exc:
            logger.error("SageMaker invocation error for %s: %s", transaction_id, exc)
            raise

    def _mock_score(self, transaction_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic fallback prediction for local development and test suites."""
        amount = float(features.get("amount", features.get("transaction_amount", 500.0)))
        count_5m = int(features.get("transaction_count_5m_prior", features.get("transaction_count_5m", 0)))
        new_dev = bool(features.get("new_device_flag", features.get("new_device", False)))
        loc_chg = bool(features.get("home_city_mismatch", features.get("location_change", False)))

        # Simple deterministic heuristic: high amount + high count or new device = high score
        if amount > 50000 or count_5m >= 4 or (new_dev and loc_chg):
            p_fraud = 0.87
            a_score = 0.72
        elif amount > 15000 or count_5m >= 2:
            p_fraud = 0.45
            a_score = 0.40
        else:
            p_fraud = 0.05
            a_score = 0.08

        return {
            "transaction_id": transaction_id,
            "fraud_probability": p_fraud,
            "anomaly_score": a_score,
            "model_version": "v20261112-mock",
        }

