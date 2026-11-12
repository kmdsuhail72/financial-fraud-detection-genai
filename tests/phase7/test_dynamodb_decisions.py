"""
Tests for DynamoDB Decision Store and Idempotency.
"""
from unittest.mock import MagicMock
from botocore.exceptions import ClientError
import pytest

from lambda_scoring.dynamodb_decisions import DecisionStore
from lambda_scoring.risk_engine import RiskDecision


def test_save_decision_success():
    """Verify first-time transaction decision is successfully written to DynamoDB."""
    mock_resource = MagicMock()
    mock_table = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_table.put_item.return_value = {}

    store = DecisionStore(table_name="finguard-fraud-decisions", dynamodb_resource=mock_resource)

    txn = {
        "transaction_id": "txn-test-1",
        "account_id": "acc-101",
        "customer_id": "cus-201",
        "amount": 15000.0,
        "currency": "INR",
    }
    decision = RiskDecision(
        transaction_id="txn-test-1",
        fraud_probability=0.87,
        anomaly_score=0.72,
        risk_score=0.8175,
        risk_level="HIGH",
        action="INVESTIGATE",
        requires_investigation=True,
        reason="Exceeds HIGH risk threshold",
    )

    saved = store.save_decision(txn, decision, model_version="v1", alert_sent=True)
    assert saved is True
    assert mock_table.put_item.call_count == 1

    # Verify ConditionExpression is enforced
    call_kwargs = mock_table.put_item.call_args[1]
    assert call_kwargs["ConditionExpression"] == "attribute_not_exists(transaction_id)"


def test_save_decision_duplicate_suppression():
    """Verify duplicate transaction is suppressed when conditional check fails."""
    mock_resource = MagicMock()
    mock_table = MagicMock()
    mock_resource.Table.return_value = mock_table

    # Simulate ConditionalCheckFailedException
    mock_table.put_item.side_effect = ClientError(
        error_response={"Error": {"Code": "ConditionalCheckFailedException", "Message": "Item exists"}},
        operation_name="PutItem",
    )

    store = DecisionStore(table_name="finguard-fraud-decisions", dynamodb_resource=mock_resource)

    txn = {"transaction_id": "txn-duplicate"}
    decision = RiskDecision(
        transaction_id="txn-duplicate",
        fraud_probability=0.1,
        anomaly_score=0.1,
        risk_score=0.1,
        risk_level="LOW",
        action="ALLOW",
        requires_investigation=False,
        reason="Normal",
    )

    saved = store.save_decision(txn, decision)
    assert saved is False


def test_get_decision():
    """Verify retrieval of an existing decision."""
    mock_resource = MagicMock()
    mock_table = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_table.get_item.return_value = {
        "Item": {
            "transaction_id": "txn-found",
            "risk_score": 0.8175,
            "risk_level": "HIGH",
        }
    }

    store = DecisionStore(table_name="finguard-fraud-decisions", dynamodb_resource=mock_resource)
    item = store.get_decision("txn-found")
    assert item is not None
    assert item["transaction_id"] == "txn-found"
    assert item["risk_level"] == "HIGH"

