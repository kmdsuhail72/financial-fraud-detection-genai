"""
Unit tests for DynamoDB idempotency deduplication.
"""
from unittest.mock import MagicMock
from botocore.exceptions import ClientError
from lambda_app.idempotency import IdempotencyService


def test_idempotency_first_time_transaction():
    mock_dynamo = MagicMock()
    mock_dynamo.put_item.return_value = {}

    service = IdempotencyService(dynamodb_client=mock_dynamo, table_name="test-idemp")
    is_new, err = service.check_and_set_processed("TXN-NEW-001")

    assert is_new is True
    assert err == ""
    assert mock_dynamo.put_item.call_count == 1


def test_idempotency_duplicate_transaction():
    mock_dynamo = MagicMock()
    # Simulate DynamoDB ConditionalCheckFailedException
    mock_dynamo.put_item.side_effect = ClientError(
        error_response={"Error": {"Code": "ConditionalCheckFailedException", "Message": "The conditional request failed"}},
        operation_name="PutItem"
    )

    service = IdempotencyService(dynamodb_client=mock_dynamo, table_name="test-idemp")
    is_new, err = service.check_and_set_processed("TXN-DUPLICATE-001")

    assert is_new is False
    assert err == "DUPLICATE_TRANSACTION"
