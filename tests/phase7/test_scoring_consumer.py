"""
Tests for Fraud Scoring Lambda Consumer and Kinesis Event Handler.
"""
import base64
import json
from unittest.mock import MagicMock
import pytest

from lambda_scoring.handler import FraudScoringConsumer
from lambda_scoring.risk_engine import RiskDecisionEngine, RiskDecision


def test_scoring_consumer_single_record_high_risk():
    """Verify high-risk transaction invokes SageMaker, stores decision, and dispatches SQS alert."""
    mock_sagemaker = MagicMock()
    mock_sagemaker.score_transaction.return_value = {
        "transaction_id": "txn-high-01",
        "fraud_probability": 0.88,
        "anomaly_score": 0.75,
        "model_version": "v1",
    }

    mock_store = MagicMock()
    mock_store.save_decision.return_value = True

    mock_alert_pub = MagicMock()
    mock_alert_pub.publish_alert.return_value = "msg-alert-123"

    engine = RiskDecisionEngine(threshold_high=0.60, threshold_review=0.35)

    consumer = FraudScoringConsumer(
        sagemaker_scorer=mock_sagemaker,
        decision_store=mock_store,
        alert_publisher=mock_alert_pub,
        risk_engine=engine,
    )

    record_data = {
        "transaction_id": "txn-high-01",
        "amount": 75000,
        "account_id": "acc-999",
    }

    result = consumer.process_record(record_data)
    assert result["transaction_id"] == "txn-high-01"
    assert result["decision"].risk_level == "HIGH"
    assert result["alert_sent"] is True

    # Verify SQS alert dispatched
    assert mock_alert_pub.publish_alert.call_count == 1
    # Verify DynamoDB decision stored
    assert mock_store.save_decision.call_count == 1


def test_kinesis_batch_with_partial_failure():
    """Verify that a batch with one bad record returns only that item identifier in batchItemFailures."""
    mock_sagemaker = MagicMock()
    mock_sagemaker.score_transaction.return_value = {
        "transaction_id": "txn-valid",
        "fraud_probability": 0.1,
        "anomaly_score": 0.1,
        "model_version": "v1",
    }

    mock_store = MagicMock()
    mock_alert_pub = MagicMock()

    consumer = FraudScoringConsumer(
        sagemaker_scorer=mock_sagemaker,
        decision_store=mock_store,
        alert_publisher=mock_alert_pub,
    )

    # Valid transaction
    valid_txn = {"transaction_id": "txn-valid", "amount": 100}
    valid_b64 = base64.b64encode(json.dumps(valid_txn).encode("utf-8")).decode("utf-8")

    # Corrupt transaction (not JSON)
    bad_b64 = base64.b64encode(b"NOT_A_VALID_JSON").decode("utf-8")

    event = {
        "Records": [
            {
                "kinesis": {
                    "sequenceNumber": "seq-101",
                    "data": valid_b64,
                }
            },
            {
                "kinesis": {
                    "sequenceNumber": "seq-102",
                    "data": bad_b64,
                }
            },
        ]
    }

    response = consumer.process_kinesis_event(event)
    assert "batchItemFailures" in response
    failures = response["batchItemFailures"]
    assert len(failures) == 1
    assert failures[0]["itemIdentifier"] == "seq-102"

