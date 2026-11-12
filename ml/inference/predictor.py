"""
FinGuard AI — Real-Time Ensemble Fraud Predictor & Risk Engine.

Combines supervised fraud classification (Random Forest / XGBoost) with
unsupervised anomaly detection (Isolation Forest) into an auditable risk score.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml.preprocessing.pipeline import FeaturePreprocessor

logger = logging.getLogger(__name__)


class EnsembleFraudModel:
    """
    Unified ML model combining:
    1. Supervised Classifier (Random Forest or XGBoost) -> fraud_probability P in [0, 1]
    2. Unsupervised Anomaly Detector (Isolation Forest) -> anomaly_score A in [0, 1]
    3. Composite Risk Engine -> R = 0.65 * P + 0.35 * A
    """

    def __init__(
        self,
        classifier: Any,
        anomaly_detector: IsolationForest,
        preprocessor: FeaturePreprocessor,
        thresholds: Optional[Dict[str, Any]] = None,
        model_version: Optional[str] = None,
        model_type: str = "random_forest",
        anomaly_min: float = -0.3,
        anomaly_max: float = 0.2,
    ):
        self.classifier = classifier
        self.anomaly_detector = anomaly_detector
        self.preprocessor = preprocessor
        self.thresholds = thresholds or {"selected_classifier_threshold": 0.45}
        self.model_version = model_version or f"v{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        self.model_type = model_type
        self.anomaly_min = anomaly_min
        self.anomaly_max = anomaly_max

    @property
    def classifier_threshold(self) -> float:
        return float(self.thresholds.get("selected_classifier_threshold", 0.45))

    def _normalize_anomaly_score(self, raw_scores: np.ndarray) -> np.ndarray:
        """
        Converts Isolation Forest decision_function output to [0, 1] anomaly score.
        raw_score: positive = normal, negative = anomalous.
        normalized: 0.0 = completely normal, 1.0 = highly anomalous.
        """
        # Invert: lower raw score means higher anomaly
        # Clip to empirical bounds [-0.3, 0.2]
        denom = max(self.anomaly_max - self.anomaly_min, 1e-6)
        normalized = (self.anomaly_max - raw_scores) / denom
        return np.clip(normalized, 0.0, 1.0)

    def predict_one(self, transaction_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Real-time scoring for a single transaction event.

        Args:
            transaction_id: Unique transaction ID.
            features: Dictionary containing feature key-values.

        Returns:
            Dictionary matching the API scoring response specification.
        """
        # Transform features
        X = self.preprocessor.transform(features)

        # 1. Supervised Fraud Probability
        if hasattr(self.classifier, "predict_proba"):
            p_fraud = float(self.classifier.predict_proba(X)[0, 1])
        else:
            p_fraud = float(self.classifier.predict(X)[0])

        # 2. Unsupervised Anomaly Score
        raw_anomaly = self.anomaly_detector.decision_function(X)[0]
        a_score = float(self._normalize_anomaly_score(np.array([raw_anomaly]))[0])

        # 3. Composite Risk Score: R = 0.65 * P + 0.35 * A
        risk_score = (0.65 * p_fraud) + (0.35 * a_score)

        # Risk tier assignment
        risk_level = self.determine_risk_level(risk_score)

        return {
            "transaction_id": transaction_id,
            "fraud_probability": round(p_fraud, 4),
            "anomaly_score": round(a_score, 4),
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "classifier_threshold": round(self.classifier_threshold, 4),
            "model_version": self.model_version,
        }

    def predict_batch(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch scoring for multiple transaction events."""
        results = []
        for txn in transactions:
            txn_id = txn.get("transaction_id", "txn-unknown")
            feat = txn.get("features", txn)
            results.append(self.predict_one(txn_id, feat))
        return results

    @staticmethod
    def determine_risk_level(risk_score: float) -> str:
        """Categorizes composite risk score into standard risk tiers."""
        if risk_score >= 0.80:
            return "CRITICAL"
        elif risk_score >= 0.60:
            return "HIGH"
        elif risk_score >= 0.35:
            return "MEDIUM"
        else:
            return "LOW"

    def save(self, filepath: str) -> None:
        """Serializes the ensemble model to disk via joblib."""
        joblib.dump(self, filepath)
        logger.info("Saved EnsembleFraudModel to %s", filepath)

    @classmethod
    def load(cls, filepath: str) -> "EnsembleFraudModel":
        """Loads serialized ensemble model from disk."""
        model = joblib.load(filepath)
        if not isinstance(model, cls):
            raise TypeError(f"Loaded object is of type {type(model)}, expected {cls.__name__}")
        return model
