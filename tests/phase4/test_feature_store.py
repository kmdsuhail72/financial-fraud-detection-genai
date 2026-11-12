"""
Unit tests for customer feature state and behavioral velocity calculations.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock
from lambda_app.feature_store import CustomerFeatureStore


def test_feature_computation_with_prior_history():
    mock_dynamo = MagicMock()
    store = CustomerFeatureStore(dynamodb_client=mock_dynamo)

    # 10 minutes ago and 2 minutes ago
    now_epoch = int(datetime(2026, 11, 12, 10, 30, 0, tzinfo=timezone.utc).timestamp())
    state = {
        "registered_devices": {"DEV-KNOWN-01"},
        "home_city": "Kolkata",
        "recent_transactions": [
            {"epoch": now_epoch - 600, "amount": 2000.0},  # 10m ago (in 1h window)
            {"epoch": now_epoch - 120, "amount": 3000.0},  # 2m ago (in 5m and 1h window)
        ]
    }

    current_txn = {
        "transaction_id": "TXN-000001",
        "account_id": "ACC-000001",
        "customer_id": "CUS-000001",
        "amount": 87500.0,
        "currency": "INR",
        "channel": "MOBILE",
        "device_id": "DEV-NEW-99",  # Unseen device
        "location": {"country": "IN", "city": "Mumbai"},  # City mismatch vs Kolkata
        "transaction_timestamp": "2026-11-12T10:30:00Z",
        "is_international": False
    }

    features, updated_state = store.compute_features(current_txn, state)

    # Check velocity features
    assert features["transaction_count_5m_prior"] == 1  # only 2m ago
    assert features["transaction_count_1h_prior"] == 2  # both 10m and 2m ago
    assert features["average_amount_1h_prior"] == 2500.0  # (2000 + 3000) / 2
    assert features["amount_vs_prior_average"] == 35.0  # 87500 / 2500
    assert features["new_device_flag"] == 1
    assert features["home_city_mismatch"] == 1  # Mumbai vs Kolkata
    assert features["is_international"] == 0
    assert features["amount_log1p"] > 0

    # Check updated state has new transaction and device added
    assert len(updated_state["recent_transactions"]) == 3
    assert "DEV-NEW-99" in updated_state["registered_devices"]

