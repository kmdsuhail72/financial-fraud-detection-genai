"""
Unit and integration tests for AWS Lambda main event handler.
"""
import base64
import json
from unittest.mock import MagicMock
from lambda_app.handler import process_kinesis_records
from lambda_app.idempotency import IdempotencyService
from lambda_app.feature_store import CustomerFeatureStore
from lambda_app.sqs_quarantine import SQSQuarantineService
from lambda_app.s3_sink import S3ProcessedSink


def make_kinesis_record(txn_dict: dict, seq_num: str) -> dict:
    raw_b64 = base64.b64encode(json.dumps(txn_dict).encode("utf-8")).decode("ascii")
    return {
        "eventID": f"shardId-000000000000:{seq_num}",
        "kinesis": {
            "data": raw_b64,
            "sequenceNumber": seq_num,
            "partitionKey": txn_dict.get("account_id", "ACC-01")
        }
    }


def test_lambda_batch_processing_with_partial_failure_and_quarantine():
    mock_s3 = MagicMock()
    mock_dynamo = MagicMock()
    mock_sqs = MagicMock()

    s3_sink = S3ProcessedSink(mock_s3, "test-bucket")
    idemp_service = IdempotencyService(mock_dynamo, "test-idemp")
    feature_store = CustomerFeatureStore(mock_dynamo, "test-state")
    quarantine = SQSQuarantineService(mock_sqs, "https://sqs.test/queue")

    # Record 1: Valid transaction
    valid_txn = {
        "transaction_id": "TXN-VALID-01",
        "account_id": "ACC-01",
        "customer_id": "CUS-01",
        "amount": 5000.0,
        "currency": "INR",
        "channel": "MOBILE",
        "transaction_timestamp": "2026-11-12T10:30:00Z"
    }

    # Record 2: Invalid transaction (negative amount)
    invalid_txn = {
        "transaction_id": "TXN-INVALID-02",
        "account_id": "ACC-02",
        "customer_id": "CUS-02",
        "amount": -50.0,
        "currency": "INR",
        "channel": "MOBILE",
        "transaction_timestamp": "2026-11-12T10:30:00Z"
    }

    # Record 3: Valid transaction, but will simulate transient S3 failure
    transient_fail_txn = {
        "transaction_id": "TXN-FAIL-03",
        "account_id": "ACC-03",
        "customer_id": "CUS-03",
        "amount": 1000.0,
        "currency": "INR",
        "channel": "MOBILE",
        "transaction_timestamp": "2026-11-12T10:30:00Z"
    }

    records = [
        make_kinesis_record(valid_txn, "seq-001"),
        make_kinesis_record(invalid_txn, "seq-002"),
        make_kinesis_record(transient_fail_txn, "seq-003"),
    ]

    # Mock DynamoDB idempotency: all are new
    mock_dynamo.put_item.return_value = {}
    mock_dynamo.get_item.return_value = {}

    # Mock S3: 1st call succeeds, 2nd call raises Exception
    mock_s3.put_object.side_effect = [
        {},
        RuntimeError("Transient S3 network timeout")
    ]

    failures = process_kinesis_records(
        records=records,
        s3_sink=s3_sink,
        idempotency_service=idemp_service,
        feature_store=feature_store,
        quarantine_service=quarantine
    )

    # Record 1 succeeded: saved to S3
    # Record 2 invalid: quarantined to SQS, NOT in batchItemFailures
    # Record 3 failed transiently: in batchItemFailures for Kinesis retry
    assert len(failures) == 1
    assert failures[0]["itemIdentifier"] == "seq-003"

    # SQS quarantine called for Record 2
    assert mock_sqs.send_message.call_count == 1
    quarantine_call = mock_sqs.send_message.call_args[1]
    assert "INVALID_AMOUNT" in quarantine_call["MessageBody"]
