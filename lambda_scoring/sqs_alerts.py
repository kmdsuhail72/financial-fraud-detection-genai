"""
FinGuard AI — SQS Investigation Alert Publisher (Phase 7).

Dispatches alerts for HIGH risk transactions to Amazon SQS for downstream
human case creation and AI-assisted investigation workflows.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from lambda_scoring.risk_engine import RiskDecision

logger = logging.getLogger(__name__)


class InvestigationAlertPublisher:
    """Dispatches high-risk alerts to Amazon SQS."""

    def __init__(
        self,
        queue_url: str,
        region_name: str = "ap-south-1",
        sqs_client: Optional[Any] = None,
    ):
        self.queue_url = queue_url
        self.region_name = region_name
        self.sqs = sqs_client or (boto3.client("sqs", region_name=region_name) if queue_url else None)

    def publish_alert(
        self,
        transaction: Dict[str, Any],
        decision: RiskDecision,
    ) -> Optional[str]:
        """
        Publishes an alert to SQS if queue_url is configured.

        Returns:
            SQS MessageId if sent, None otherwise.
        """
        if not self.queue_url or not self.sqs:
            logger.info("SQS alert queue not configured; skipping SQS dispatch for %s", decision.transaction_id)
            return None

        alert_payload = {
            "event_type": "HIGH_RISK_FRAUD_ALERT",
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
            "reason": decision.reason,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "requires_investigation": True,
        }

        try:
            kwargs = {
                "QueueUrl": self.queue_url,
                "MessageBody": json.dumps(alert_payload),
                "MessageAttributes": {
                    "RiskLevel": {
                        "DataType": "String",
                        "StringValue": decision.risk_level,
                    },
                    "TransactionId": {
                        "DataType": "String",
                        "StringValue": decision.transaction_id,
                    },
                },
            }

            # If FIFO queue, include deduplication & group IDs
            if self.queue_url.endswith(".fifo"):
                kwargs["MessageGroupId"] = transaction.get("account_id", "DEFAULT_GROUP")
                kwargs["MessageDeduplicationId"] = decision.transaction_id

            response = self.sqs.send_message(**kwargs)
            msg_id = response.get("MessageId")
            logger.info("Published investigation alert for %s (MessageId: %s)", decision.transaction_id, msg_id)
            return msg_id
        except ClientError as exc:
            logger.error("Failed to publish alert to SQS for %s: %s", decision.transaction_id, exc)
            raise

