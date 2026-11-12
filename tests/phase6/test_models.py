"""
Tests for ML Preprocessing, Random Forest, XGBoost, Isolation Forest, and Predictor.
"""
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from xgboost import XGBClassifier

from ml.data_loader import DatasetSplits
from ml.inference.predictor import EnsembleFraudModel
from ml.preprocessing.pipeline import FeaturePreprocessor
from ml.training.trainer import train_fraud_detection_pipeline


@pytest.fixture
def sample_splits() -> DatasetSplits:
    """Creates a synthetic dataset fixture for fast model testing."""
    np.random.seed(42)
    n = 200
    X = pd.DataFrame({
        "transaction_amount": np.random.uniform(10, 5000, n),
        "avg_amount_24h": np.random.uniform(10, 3000, n),
        "transaction_count_5m": np.random.poisson(0.5, n),
        "transaction_count_1h": np.random.poisson(1.5, n),
        "amount_deviation": np.random.uniform(0.5, 10.0, n),
        "new_device": np.random.binomial(1, 0.1, n),
        "location_change": np.random.binomial(1, 0.1, n),
        "international_flag": np.random.binomial(1, 0.05, n),
        "merchant_risk": np.random.uniform(0.01, 0.9, n),
        "account_age_days": np.random.randint(30, 1000, n),
    })
    # Fraud correlates with high deviation and high count
    y_raw = (X["amount_deviation"] > 5.0) | (X["new_device"] == 1) & (X["location_change"] == 1)
    y = y_raw.astype(int)
    ids = pd.Series([f"TXN-{i:06d}" for i in range(n)])

    feature_names = list(X.columns)
    return DatasetSplits(
        X_train=X.iloc[:140].reset_index(drop=True),
        y_train=y.iloc[:140].reset_index(drop=True),
        X_val=X.iloc[140:170].reset_index(drop=True),
        y_val=y.iloc[140:170].reset_index(drop=True),
        X_test=X.iloc[170:].reset_index(drop=True),
        y_test=y.iloc[170:].reset_index(drop=True),
        feature_names=feature_names,
        train_ids=ids.iloc[:140].reset_index(drop=True),
        val_ids=ids.iloc[140:170].reset_index(drop=True),
        test_ids=ids.iloc[170:].reset_index(drop=True),
    )


def test_preprocessor_alias_and_imputation(sample_splits):
    """Test that preprocessor correctly maps aliases and fills missing fields."""
    prep = FeaturePreprocessor(feature_names=sample_splits.feature_names)
    prep.fit(sample_splits.X_train)

    incoming = {
        "amount": 4500.0,  # alias for transaction_amount
        "transaction_count_5m_prior": 3,  # alias for transaction_count_5m
        "new_device_flag": True,  # alias for new_device
        "home_city_mismatch": False,  # alias for location_change
        "is_international": True,  # alias for international_flag
    }

    scaled = prep.transform(incoming)
    assert scaled.shape == (1, len(sample_splits.feature_names))

    manifest = prep.export_manifest()
    assert manifest["num_features"] == len(sample_splits.feature_names)
    assert "transaction_amount" in manifest["feature_names"]


def test_train_pipeline_random_forest(sample_splits):
    """Test full training pipeline with Random Forest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ensemble, meta = train_fraud_detection_pipeline(
            splits=sample_splits,
            model_type="random_forest",
            output_dir=tmpdir,
        )

        assert Path(meta["model_file"]).exists()
        assert Path(meta["metrics_file"]).exists()
        assert Path(meta["manifest_file"]).exists()
        assert Path(meta["thresholds_file"]).exists()
        assert Path(meta["card_file"]).exists()

        assert meta["test_metrics"]["roc_auc"] >= 0.5
        assert 0.0 < ensemble.classifier_threshold < 1.0


def test_train_pipeline_xgboost(sample_splits):
    """Test full training pipeline with XGBoost."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ensemble, meta = train_fraud_detection_pipeline(
            splits=sample_splits,
            model_type="xgboost",
            output_dir=tmpdir,
        )

        assert Path(meta["model_file"]).exists()
        assert isinstance(ensemble.classifier, XGBClassifier)


def test_ensemble_model_save_and_load(sample_splits):
    """Verify that saved model can be reloaded and yields identical predictions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_file = Path(tmpdir) / "model.joblib"
        ensemble, _ = train_fraud_detection_pipeline(
            splits=sample_splits,
            model_type="random_forest",
            output_dir=tmpdir,
        )

        loaded = EnsembleFraudModel.load(str(model_file))
        test_payload = {
            "transaction_amount": 15000.0,
            "avg_amount_24h": 500.0,
            "amount_deviation": 30.0,
            "transaction_count_5m": 5,
            "new_device": 1.0,
            "location_change": 1.0,
        }

        pred_orig = ensemble.predict_one("TXN-TEST", test_payload)
        pred_loaded = loaded.predict_one("TXN-TEST", test_payload)

        assert pred_orig["fraud_probability"] == pred_loaded["fraud_probability"]
        assert pred_orig["anomaly_score"] == pred_loaded["anomaly_score"]
        assert pred_orig["risk_score"] == pred_loaded["risk_score"]
        assert pred_orig["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
