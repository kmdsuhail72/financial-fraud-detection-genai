"""
Unit tests for data lake deduplication logic.
"""
import os
import shutil
import tempfile
import pandas as pd
from scripts.phase5.local_transform import transform_bronze_to_silver


def test_deduplicate_transactions():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create duplicate events with same transaction_id
        duplicate_records = [
            {
                "transaction_id": "TXN-DUP-01",
                "account_id": "ACC-01",
                "customer_id": "CUS-01",
                "amount": 1000.0,
                "currency": "INR",
                "channel": "MOBILE",
                "transaction_timestamp": "2026-11-12T10:00:00Z",
                "location": {"city": "Delhi", "country": "IN"},
                "features": {"new_device_flag": 0}
            },
            {
                "transaction_id": "TXN-DUP-01",  # Same ID, retry delivery
                "account_id": "ACC-01",
                "customer_id": "CUS-01",
                "amount": 1000.0,
                "currency": "INR",
                "channel": "MOBILE",
                "transaction_timestamp": "2026-11-12T10:00:00Z",
                "location": {"city": "Delhi", "country": "IN"},
                "features": {"new_device_flag": 0}
            },
            {
                "transaction_id": "TXN-UNIQUE-02",
                "account_id": "ACC-02",
                "customer_id": "CUS-02",
                "amount": 2500.0,
                "currency": "INR",
                "channel": "POS",
                "transaction_timestamp": "2026-11-12T11:00:00Z",
                "location": {"city": "Mumbai", "country": "IN"},
                "features": {"new_device_flag": 1}
            }
        ]

        silver_out = os.path.join(temp_dir, "silver")
        df = transform_bronze_to_silver(duplicate_records, silver_out)

        # 3 input records -> 2 deduplicated records
        assert len(df) == 2
        assert set(df["transaction_id"]) == {"TXN-DUP-01", "TXN-UNIQUE-02"}
    finally:
        shutil.rmtree(temp_dir)

