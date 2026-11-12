"""
Tests for Data Loader and Target Leakage Safeguards.
"""
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from ml.data_loader import load_and_merge_dataset, split_dataset, LEAKAGE_COLUMNS


def test_data_loader_leakage_prevention():
    """Verify that all target and fraud scenario columns are excluded from features."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        feat_csv = tmp_path / "feat.csv"
        lbl_csv = tmp_path / "lbl.csv"

        df_feat = pd.DataFrame({
            "transaction_id": ["TXN-1", "TXN-2", "TXN-3", "TXN-4"],
            "amount": [100.0, 200.0, 50.0, 500.0],
            "velocity": [1, 2, 1, 5],
            "fraud_scenario": ["ACCOUNT_TAKEOVER", "NORMAL", "NORMAL", "VELOCITY"],
            "is_flagged": [1, 0, 0, 1],
        })
        df_lbl = pd.DataFrame({
            "transaction_id": ["TXN-1", "TXN-2", "TXN-3", "TXN-4"],
            "is_fraud": [1, 0, 0, 1],
        })

        df_feat.to_csv(feat_csv, index=False)
        df_lbl.to_csv(lbl_csv, index=False)

        X, y, ids, feature_names = load_and_merge_dataset(
            features_path=feat_csv,
            labels_path=lbl_csv,
            label_column="is_fraud",
        )

        # Ensure no leakage columns in feature matrix
        for col in X.columns:
            assert col.lower() not in LEAKAGE_COLUMNS, f"Leaked column found: {col}"
            assert col != "is_fraud"

        assert "transaction_id" not in X.columns
        assert len(X) == 4
        assert len(y) == 4
        assert len(ids) == 4


def test_data_loader_stratified_split():
    """Verify that dataset splitting preserves class balance reproducibly."""
    X = pd.DataFrame({
        "feat1": list(range(100)),
        "feat2": list(range(100, 200)),
    })
    # 10% fraud rate: 10 ones, 90 zeros
    y = pd.Series([1] * 10 + [0] * 90)
    ids = pd.Series([f"TXN-{i}" for i in range(100)])

    splits = split_dataset(X, y, ids, val_size=0.15, test_size=0.15, random_state=42)

    # 70 train, 15 val, 15 test
    assert len(splits.X_train) == 70
    assert len(splits.X_val) == 15
    assert len(splits.X_test) == 15

    # Check that fraud cases exist across all splits
    assert splits.y_train.sum() > 0
    assert splits.y_val.sum() > 0
    assert splits.y_test.sum() > 0

