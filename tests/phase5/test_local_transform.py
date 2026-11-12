"""
Unit tests for local Parquet transformation and flattening.
"""
import os
import shutil
import tempfile
import pandas as pd
from scripts.phase5.local_transform import flatten_transaction, transform_bronze_to_silver


def test_flatten_transaction():
    nested_txn = {
        "transaction_id": "TXN-001",
        "account_id": "ACC-01",
        "customer_id": "CUS-01",
        "amount": 2500.0,
        "currency": "INR",
        "channel": "POS",
        "transaction_timestamp": "2026-11-12T14:30:00Z",
        "location": {"city": "Bengaluru", "country": "IN"},
        "features": {
            "transaction_count_5m_prior": 2,
            "new_device_flag": 0
        }
    }

    flat = flatten_transaction(nested_txn)
    assert flat["location_city"] == "Bengaluru"
    assert flat["feat_transaction_count_5m_prior"] == 2
    assert flat["feat_new_device_flag"] == 0
    assert flat["year"] == 2026
    assert flat["month"] == 11
    assert flat["day"] == 12


def test_transform_bronze_to_silver_parquet():
    temp_dir = tempfile.mkdtemp()
    try:
        sample_records = [
            {
                "transaction_id": f"TXN-{i:03d}",
                "account_id": "ACC-01",
                "customer_id": "CUS-01",
                "amount": float(i * 100),
                "currency": "INR",
                "channel": "MOBILE",
                "transaction_timestamp": "2026-11-12T10:00:00Z",
                "location": {"city": "Mumbai", "country": "IN"},
                "features": {"new_device_flag": 0}
            }
            for i in range(1, 10)
        ]

        silver_out = os.path.join(temp_dir, "silver")
        df = transform_bronze_to_silver(sample_records, silver_out)

        assert len(df) == 9
        # Read back from parquet directory
        df_read = pd.read_parquet(silver_out)
        assert len(df_read) == 9
        assert "feat_new_device_flag" in df_read.columns
        assert "location_city" in df_read.columns
    finally:
        shutil.rmtree(temp_dir)
