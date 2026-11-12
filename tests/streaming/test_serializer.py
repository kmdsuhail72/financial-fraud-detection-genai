"""
Unit tests for Kinesis transaction serialization and partition key strategy.
"""
from streaming.serializer import TransactionSerializer


def test_serializer_valid_transaction():
    txn = {
        "transaction_id": "TXN-20261112-000001",
        "account_id": "ACC-100045",
        "customer_id": "CUS-200045",
        "amount": 87500.00,
        "currency": "INR",
        "channel": "MOBILE",
        "transaction_timestamp": "2026-11-12T10:30:00Z"
    }

    is_valid, record, error = TransactionSerializer.validate_and_serialize(txn)

    assert is_valid is True
    assert error == ""
    assert record["PartitionKey"] == "ACC-100045"
    assert isinstance(record["Data"], bytes)

    # Test deserialization
    ok_deser, decoded, deser_err = TransactionSerializer.deserialize(record["Data"])
    assert ok_deser is True
    assert decoded["transaction_id"] == "TXN-20261112-000001"
    assert decoded["amount"] == 87500.00


def test_serializer_missing_required_field():
    invalid_txn = {
        "transaction_id": "TXN-20261112-000002",
        # Missing account_id and amount
        "customer_id": "CUS-200045",
    }

    is_valid, record, error = TransactionSerializer.validate_and_serialize(invalid_txn)
    assert is_valid is False
    assert "Missing required transaction fields" in error
    assert "account_id" in error
