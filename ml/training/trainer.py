"""
FinGuard AI — Machine Learning Training Engine.

Orchestrates data preprocessing, supervised model training (Random Forest or XGBoost),
unsupervised anomaly detection (Isolation Forest), validation threshold tuning,
test set evaluation, and model artifact persistence.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from xgboost import XGBClassifier

from ml.data_loader import DatasetSplits
from ml.evaluation.metrics import compute_classification_metrics
from ml.evaluation.threshold_tuning import tune_classification_thresholds
from ml.inference.predictor import EnsembleFraudModel
from ml.preprocessing.pipeline import FeaturePreprocessor
from ml.registry.model_card import generate_model_card

logger = logging.getLogger(__name__)


def train_fraud_detection_pipeline(
    splits: DatasetSplits,
    model_type: str = "random_forest",
    output_dir: Optional[str] = "artifacts",
    random_state: int = 42,
) -> Tuple[EnsembleFraudModel, Dict[str, Any]]:
    """
    Trains supervised and unsupervised models, tunes thresholds, evaluates held-out test data,
    and saves all 5 standard artifacts to output_dir.

    Returns:
        ensemble_model: Trained EnsembleFraudModel.
        artifacts_metadata: Dict with metrics, thresholds, manifest, and model card.
    """
    out_path = Path(output_dir) if output_dir else Path("artifacts")
    out_path.mkdir(parents=True, exist_ok=True)

    model_version = f"v{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    logger.info("Initializing FinGuard ML training: model_type=%s, version=%s", model_type, model_version)

    # 1. Feature Preprocessing & Scaling
    preprocessor = FeaturePreprocessor(feature_names=splits.feature_names, scale_features=True)
    preprocessor.fit(splits.X_train)

    X_train_scaled = preprocessor.transform(splits.X_train)
    X_val_scaled = preprocessor.transform(splits.X_val)
    X_test_scaled = preprocessor.transform(splits.X_test)

    # 2. Train Supervised Classifier
    if model_type.lower() == "xgboost":
        pos_count = int(np.sum(splits.y_train))
        neg_count = int(len(splits.y_train) - pos_count)
        scale_pos_weight = float(neg_count / max(pos_count, 1))

        classifier = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=random_state,
            n_jobs=-1,
        )
        classifier.fit(X_train_scaled, splits.y_train)
    else:
        classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )
        classifier.fit(X_train_scaled, splits.y_train)

    # 3. Train Unsupervised Anomaly Detector (Isolation Forest)
    # Train on normal transactions (y == 0) or full train set to model normal behavior
    normal_indices = np.where(splits.y_train.to_numpy() == 0)[0]
    X_normal = X_train_scaled[normal_indices] if len(normal_indices) > 0 else X_train_scaled

    anomaly_detector = IsolationForest(
        n_estimators=100,
        contamination=0.03,
        random_state=random_state,
        n_jobs=-1,
    )
    anomaly_detector.fit(X_normal)

    # Determine empirical range of Isolation Forest decision function
    train_anom_scores = anomaly_detector.decision_function(X_train_scaled)
    anom_min = float(np.percentile(train_anom_scores, 1))
    anom_max = float(np.percentile(train_anom_scores, 99))
    logger.info("Isolation Forest empirical score bounds: min=%.4f, max=%.4f", anom_min, anom_max)

    # 4. Validation Set Evaluation & Threshold Tuning
    y_prob_val = classifier.predict_proba(X_val_scaled)[:, 1]
    thresholds = tune_classification_thresholds(splits.y_val.to_numpy(), y_prob_val)
    selected_threshold = float(thresholds["selected_classifier_threshold"])
    logger.info("Tuned validation threshold (best F1): %.4f", selected_threshold)

    # 5. Evaluate Performance
    y_prob_train = classifier.predict_proba(X_train_scaled)[:, 1]
    y_prob_test = classifier.predict_proba(X_test_scaled)[:, 1]

    train_metrics = compute_classification_metrics(splits.y_train.to_numpy(), y_prob_train, selected_threshold)
    val_metrics = compute_classification_metrics(splits.y_val.to_numpy(), y_prob_val, selected_threshold)
    test_metrics = compute_classification_metrics(splits.y_test.to_numpy(), y_prob_test, selected_threshold)

    metrics_payload = {
        "model_type": model_type,
        "model_version": model_version,
        "selected_threshold": selected_threshold,
        "test_metrics": test_metrics,
        "validation_metrics": val_metrics,
        "train_metrics": train_metrics,
    }

    # 6. Assemble Ensemble Model
    ensemble = EnsembleFraudModel(
        classifier=classifier,
        anomaly_detector=anomaly_detector,
        preprocessor=preprocessor,
        thresholds=thresholds,
        model_version=model_version,
        model_type=model_type,
        anomaly_min=anom_min,
        anomaly_max=anom_max,
    )

    # 7. Generate Model Card
    dataset_summary = {
        "total_records": len(splits.X_train) + len(splits.X_val) + len(splits.X_test),
        "train_records": len(splits.X_train),
        "val_records": len(splits.X_val),
        "test_records": len(splits.X_test),
        "train_fraud_rate": round(splits.train_fraud_rate, 4),
        "val_fraud_rate": round(splits.val_fraud_rate, 4),
        "test_fraud_rate": round(splits.test_fraud_rate, 4),
    }

    feature_manifest = preprocessor.export_manifest()
    model_card = generate_model_card(
        model_version=model_version,
        model_type=model_type,
        feature_names=splits.feature_names,
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        thresholds=thresholds,
        dataset_summary=dataset_summary,
    )

    # 8. Persist Artifacts
    # Artifact 1: model.joblib
    model_file = out_path / "model.joblib"
    ensemble.save(str(model_file))

    # Artifact 2: metrics.json
    metrics_file = out_path / "metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics_payload, f, indent=2)

    # Artifact 3: feature_manifest.json
    manifest_file = out_path / "feature_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(feature_manifest, f, indent=2)

    # Artifact 4: thresholds.json
    thresholds_file = out_path / "thresholds.json"
    with open(thresholds_file, "w") as f:
        json.dump(thresholds, f, indent=2)

    # Artifact 5: model_card.json
    card_file = out_path / "model_card.json"
    with open(card_file, "w") as f:
        json.dump(model_card, f, indent=2)

    logger.info("Successfully exported all 5 model artifacts to %s", out_path)

    return ensemble, {
        "model_file": str(model_file),
        "metrics_file": str(metrics_file),
        "manifest_file": str(manifest_file),
        "thresholds_file": str(thresholds_file),
        "card_file": str(card_file),
        "test_metrics": test_metrics,
        "selected_threshold": selected_threshold,
    }
