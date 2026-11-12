"""
Unit tests for Gold analytics mart aggregations.
"""
import os
import shutil
import tempfile
import pandas as pd
from scripts.phase5.local_transform import generate_gold_aggregates


def test_gold_analytics_marts():
    temp_dir = tempfile.mkdtemp()
    try:
        data = {
            "transaction_id": ["T1", "T2", "T3"],
            "amount": [1000.0, 2000.0, 3000.0],
            "channel": ["MOBILE", "MOBILE", "WEB"],
            "merchant_category": ["GROCERY", "GROCERY", "ELECTRONICS"],
            "year": [2026, 2026, 2026],
            "month": [11, 11, 11],
            "day": [12, 12, 12],
            "feat_new_device_flag": [0, 1, 0],
            "feat_home_city_mismatch": [0, 0, 1],
            "feat_transaction_count_5m_prior": [1, 5, 2]
        }
        df = pd.DataFrame(data)

        gold_out = os.path.join(temp_dir, "gold")
        marts = generate_gold_aggregates(df, gold_out)

        assert "daily_mart" in marts
        assert "channel_mart" in marts
        assert "merchant_mart" in marts

        # Test daily totals
        daily = marts["daily_mart"]
        assert daily["total_transactions"].iloc[0] == 3
        assert daily["total_volume_inr"].iloc[0] == 6000.0

        # Test channel totals
        channel = marts["channel_mart"]
        mobile_row = channel[channel["channel"] == "MOBILE"].iloc[0]
        assert mobile_row["transaction_count"] == 2
        assert mobile_row["total_volume"] == 3000.0

        # Verify files written to disk
        assert os.path.exists(os.path.join(gold_out, "daily_summary.parquet"))
        assert os.path.exists(os.path.join(gold_out, "channel_summary.parquet"))
        assert os.path.exists(os.path.join(gold_out, "merchant_category_summary.parquet"))
    finally:
        shutil.rmtree(temp_dir)

