"""Machine Learning Anomaly Detection Engine powered by Isolation Forest for UEBA."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from ueba.feature_engineer import UEBAFeatureEngineer
from ueba.models import BehavioralFeatures

logger = logging.getLogger("finguard-ueba")


class IsolationForestAnomalyDetector:
    """Scikit-Learn Isolation Forest pipeline for behavioral outlier detection."""

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.05,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.model: Optional[IsolationForest] = None
        self._is_fitted = False
        self._init_default_baseline()

    def _init_default_baseline(self) -> None:
        """Initializes and pre-fits an operational baseline on simulated standard activity."""
        rng = np.random.default_rng(self.random_state)
        normal_samples = rng.normal(
            loc=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            scale=[0.3, 0.5, 0.1, 0.1, 0.1, 0.1, 0.2, 0.4],
            size=(250, 8),
        )
        normal_samples = np.clip(normal_samples, a_min=0.0, a_max=None)

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self.model.fit(normal_samples)
        self._is_fitted = True

    def _to_matrix(self, data: Union[np.ndarray, List[BehavioralFeatures]]) -> np.ndarray:
        if isinstance(data, list):
            vectors = [UEBAFeatureEngineer.to_feature_vector(f) for f in data]
            return np.vstack(vectors)
        return data

    def fit(self, X: Union[np.ndarray, List[BehavioralFeatures]]) -> None:
        """Fits the Isolation Forest on behavioral feature vectors."""
        mat = self._to_matrix(X)
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self.model.fit(mat)
        self._is_fitted = True
        logger.info("Fitted IsolationForest on %d feature vectors (dim: %d)", mat.shape[0], mat.shape[1])

    def score_samples(self, X: Union[np.ndarray, List[BehavioralFeatures]]) -> np.ndarray:
        """
        Computes continuous anomaly scores in range [0.0, 1.0].
        Higher score = more anomalous.
        """
        if not self._is_fitted or self.model is None:
            self._init_default_baseline()

        mat = self._to_matrix(X)
        raw_decisions = self.model.decision_function(mat)
        # Transform to [0, 1] range: lower decision value -> higher anomaly score
        anomaly_scores = 1.0 / (1.0 + np.exp(raw_decisions * 4.0))
        return np.round(np.clip(anomaly_scores, 0.0, 1.0), 4)

    def score_sample(self, features: Union[BehavioralFeatures, np.ndarray]) -> float:
        """Scores a single event feature vector."""
        if isinstance(features, BehavioralFeatures):
            vec = UEBAFeatureEngineer.to_feature_vector(features).reshape(1, -1)
        else:
            vec = features.reshape(1, -1)
        scores = self.score_samples(vec)
        return float(scores[0])

    def predict_single(self, vector: np.ndarray) -> float:
        return self.score_sample(vector)

    def save(self, filepath: str) -> None:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, filepath)
        logger.info("Saved Isolation Forest model to %s", filepath)

    @classmethod
    def load(cls, filepath: str) -> IsolationForestAnomalyDetector:
        detector = cls()
        detector.model = joblib.load(filepath)
        detector._is_fitted = True
        logger.info("Loaded Isolation Forest model from %s", filepath)
        return detector
