"""
Unit tests for Kinesis event record decoder.
"""
import base64
import json
from lambda_app.decoder import KinesisRecordDecoder


def test_decode_valid_kinesis_record():
    payload = {
        "transaction_id": "TXN-000001",
        "account_id": "ACC-000001",
        "amount": 5000.0
    }
    encoded_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    record = {
        "eventID": "shardId-000000000000:seq-1",
        "kinesis": {
            "data": encoded_b64,
            "sequenceNumber": "seq-1",
            "partitionKey": "ACC-000001"
        }
    }

    is_valid, decoded, seq_num, error = KinesisRecordDecoder.decode_record(record)
    assert is_valid is True
    assert error == ""
    assert seq_num == "seq-1"
    assert decoded["transaction_id"] == "TXN-000001"
    assert decoded["amount"] == 5000.0


def test_decode_malformed_json():
    bad_bytes = b"{ invalid json"
    encoded_b64 = base64.b64encode(bad_bytes).decode("ascii")
    record = {
        "kinesis": {
            "data": encoded_b64,
            "sequenceNumber": "seq-bad-json"
        }
    }

    is_valid, decoded, seq_num, error = KinesisRecordDecoder.decode_record(record)
    assert is_valid is False
    assert "Malformed JSON payload" in error


def test_decode_missing_data_field():
    record = {"kinesis": {}}
    is_valid, decoded, seq_num, error = KinesisRecordDecoder.decode_record(record)
    assert is_valid is False
    assert "Missing 'kinesis.data'" in error
