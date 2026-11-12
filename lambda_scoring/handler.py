"""
FinGuard AI — Real-Time Fraud Scoring Lambda Consumer (Phase 7).

Consumes banking transactions from Amazon Kinesis Data Streams,
invokes the Amazon SageMaker endpoint for ensemble model predictions,
evaluates risk thresholds via the Risk Decision Engine,
persists decisions to DynamoDB with idempotency,
and publishes high-risk investigation alerts to Amazon SQS.

Implements partial batch failure reporting:
    {"batchItemFailures": [{"itemIdentifier": sequence_number}]}
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, List, Optional

from lambda_scoring.config import ScoringConfig
from lambda_scoring.dynamodb_decisions import DecisionStore
from lambda_scoring.risk_engine import RiskDecisionEngine
from lambda_scoring.sagemaker_client import SageMakerScorer
from lambda_scoring.sqs_alerts import InvestigationAlertPublisher

logger = logging.getLogger("finguard-scoring-consumer")
logger.setLevel(logging.INFO)


class FraudScoringConsumer:
    """Orchestrates end-to-end stream scoring and alert generation."""

    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        sagemaker_scorer: Optional[SageMakerScorer] = None,
        decision_store: Optional[DecisionStore] = None,
        alert_publisher: Optional[InvestigationAlertPublisher] = None,
        risk_engine: Optional[RiskDecisionEngine] = None,
    ):
        self.config = config or ScoringConfig()
        self.sagemaker = sagemaker_scorer or SageMakerScorer(
            endpoint_name=self.config.sagemaker_endpoint_name,
            region_name=self.config.aws_region,
        )
        self.decision_store = decision_store or DecisionStore(
            table_name=self.config.dynamodb_decisions_table,
            region_name=self.config.aws_region,
            ttl_days=self.config.decision_ttl_days,
        )
        self.alert_publisher = alert_publisher or InvestigationAlertPublisher(
            queue_url=self.config.sqs_investigation_queue_url,
            region_name=self.config.aws_region,
        )
        self.risk_engine = risk_engine or RiskDecisionEngine(
            threshold_high=self.config.risk_threshold_high,
            threshold_review=self.config.risk_threshold_review,
            weight_fraud_probability=self.config.weight_fraud_probability,
            weight_anomaly_score=self.config.weight_anomaly_score,
        )

    def process_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processes a single decoded transaction record."""
        txn_id = record_data.get("transaction_id", "UNKNOWN")

        # 1. Feature Extraction (supports nested or flat feature formats)
        features = record_data.get("features", record_data)

        # 2. SageMaker Inference
        pred = self.sagemaker.score_transaction(txn_id, features)
        p_fraud = pred.get("fraud_probability", 0.0)
        a_score = pred.get("anomaly_score", 0.0)
        model_version = pred.get("model_version", "v1")

        # 3. Risk Decision Engine
        decision = self.risk_engine.calculate_risk(
            transaction_id=txn_id,
            fraud_probability=p_fraud,
            anomaly_score=a_score,
        )

        # 4. SQS High-Risk Alert Dispatch
        alert_sent = False
        if decision.requires_investigation:
            msg_id = self.alert_publisher.publish_alert(record_data, decision)
            alert_sent = msg_id is not None

        # 5. DynamoDB Decision Persistence & Idempotency
        self.decision_store.save_decision(
            transaction=record_data,
            decision=decision,
            model_version=model_version,
            alert_sent=alert_sent,
        )

        return {
            "transaction_id": txn_id,
            "decision": decision,
            "alert_sent": alert_sent,
        }

    def process_kinesis_event(self, event: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """
        Processes a batch of Kinesis stream records with partial batch failure reporting.
        """
        records = event.get("Records", [])
        batch_failures = []
        logger.info("Processing Kinesis batch of %d records", len(records))

        for record in records:
            seq_num = record.get("kinesis", {}).get("sequenceNumber", "")
            try:
                # Decode Kinesis record payload
                encoded_data = record.get("kinesis", {}).get("data", "")
                decoded_bytes = base64.b64decode(encoded_data)
                transaction_data = json.loads(decoded_bytes.decode("utf-8"))

                # Process transaction
                self.process_record(transaction_data)

            except Exception as exc:
                logger.error("Failed processing record sequence %s: %s", seq_num, exc, exc_info=True)
                if seq_num:
                    batch_failures.append({"itemIdentifier": seq_num})

        logger.info("Batch processing finished. Success: %d, Failures: %d",
                    len(records) - len(batch_failures), len(batch_failures))

        return {"batchItemFailures": batch_failures}


# Global singleton instance for Lambda container reuse
_CONSUMER: Optional[FraudScoringConsumer] = None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, List[Dict[str, str]]]:
    """AWS Lambda entrypoint."""
    global _CONSUMER
    if _CONSUMER is None:
        _CONSUMER = FraudScoringConsumer()
    return _CONSUMER.process_kinesis_event(event)
