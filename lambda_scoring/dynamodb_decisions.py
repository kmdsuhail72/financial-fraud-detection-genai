"""
FinGuard AI — DynamoDB Decision Store & Idempotency Manager (Phase 7).

Persists transaction scoring decisions and suppresses duplicate processing
using conditional writes on primary key transaction_id.
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from lambda_scoring.risk_engine import RiskDecision

logger = logging.getLogger(__name__)


def float_to_decimal(obj: Any) -> Any:
    """Recursively converts floats to Decimal for DynamoDB serialization."""
    if isinstance(obj, float):
        return Decimal(str(round(obj, 6)))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(item) for item in obj]
    return obj


def decimal_to_float(obj: Any) -> Any:
    """Recursively converts Decimals to float for JSON compatibility."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


class DecisionStore:
    """Manages idempotency and decision record persistence in DynamoDB."""

    def __init__(
        self,
        table_name: str,
        region_name: str = "ap-south-1",
        dynamodb_resource: Optional[Any] = None,
        ttl_days: int = 90,
    ):
        self.table_name = table_name
        self.region_name = region_name
        self.ttl_seconds = ttl_days * 86400

        if dynamodb_resource is None:
            self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        else:
            self.dynamodb = dynamodb_resource
        self.table = self.dynamodb.Table(table_name)

    def save_decision(
        self,
        transaction: Dict[str, Any],
        decision: RiskDecision,
        model_version: str = "v1",
        alert_sent: bool = False,
    ) -> bool:
        """
        Conditionally persists the scoring decision in DynamoDB.

        Returns:
            True if newly inserted, False if record already exists (duplicate).
        """
        now = time.time()
        ttl_expire = int(now + self.ttl_seconds)

        item = {
            "transaction_id": decision.transaction_id,
            "account_id": transaction.get("account_id", "UNKNOWN"),
            "customer_id": transaction.get("customer_id", "UNKNOWN"),
            "amount": transaction.get("amount", transaction.get("transaction_amount", 0.0)),
            "currency": transaction.get("currency", "INR"),
            "fraud_probability": decision.fraud_probability,
            "anomaly_score": decision.anomaly_score,
            "risk_score": decision.risk_score,
            "risk_level": decision.risk_level,
            "action": decision.action,
            "requires_investigation": decision.requires_investigation,
            "reason": decision.reason,
            "alert_sent": alert_sent,
            "model_version": model_version,
            "decision_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "ttl": ttl_expire,
        }

        dynamo_item = float_to_decimal(item)

        try:
            # Conditional write guarantees idempotency
            self.table.put_item(
                Item=dynamo_item,
                ConditionExpression="attribute_not_exists(transaction_id)",
            )
            logger.info("Saved fraud decision for %s (risk: %s)", decision.transaction_id, decision.risk_level)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.warning("Duplicate transaction %s ignored by DynamoDB idempotency guard", decision.transaction_id)
                return False
            logger.error("Failed to write decision to DynamoDB: %s", exc)
            raise

    def get_decision(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an existing transaction decision."""
        try:
            resp = self.table.get_item(Key={"transaction_id": transaction_id})
            item = resp.get("Item")
            if item:
                return decimal_to_float(item)
            return None
        except ClientError as exc:
            logger.error("Failed to get decision for %s: %s", transaction_id, exc)
            raise
