"""
Unit tests for transaction validation and business rules.
"""
from lambda_app.validator import TransactionValidator


def test_validator_valid_payload():
    valid_txn = {
        "transaction_id": "TXN-000001",
        "account_id": "ACC-000001",
        "customer_id": "CUS-000001",
        "amount": 87500.0,
        "currency": "INR",
        "channel": "MOBILE",
        "transaction_timestamp": "2026-11-12T10:30:00Z"
    }
    is_valid, code, msg = TransactionValidator.validate(valid_txn)
    assert is_valid is True
    assert code == ""
    assert msg == ""


def test_validator_missing_fields():
    invalid_txn = {
        "transaction_id": "TXN-000001",
        # Missing account_id, customer_id, amount, etc.
    }
    is_valid, code, msg = TransactionValidator.validate(invalid_txn)
    assert is_valid is False
    assert code == "MISSING_REQUIRED_FIELD"


def test_validator_negative_or_zero_amount():
    txn_zero = {
        "transaction_id": "TXN-000001",
        "account_id": "ACC-000001",
        "customer_id": "CUS-000001",
        "amount": 0.0,
        "currency": "INR",
        "channel": "MOBILE",
        "transaction_timestamp": "2026-11-12T10:30:00Z"
    }
    is_valid, code, msg = TransactionValidator.validate(txn_zero)
    assert is_valid is False
    assert code == "INVALID_AMOUNT"


def test_validator_invalid_timestamp():
    txn_bad_time = {
        "transaction_id": "TXN-000001",
        "account_id": "ACC-000001",
        "customer_id": "CUS-000001",
        "amount": 100.0,
        "currency": "INR",
        "channel": "MOBILE",
        "transaction_timestamp": "not-a-timestamp"
    }
    is_valid, code, msg = TransactionValidator.validate(txn_bad_time)
    assert is_valid is False
    assert code == "INVALID_TIMESTAMP"

