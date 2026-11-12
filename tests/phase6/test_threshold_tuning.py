"""
Tests for Threshold Tuning and Performance Metrics Computation.
"""
import numpy as np
import pytest

from ml.evaluation.metrics import compute_classification_metrics
from ml.evaluation.threshold_tuning import tune_classification_thresholds


def test_compute_classification_metrics():
    """Verify classification metrics logic and confusion matrix calculation."""
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.7, 0.2, 0.8, 0.9, 0.95])

    metrics = compute_classification_metrics(y_true, y_prob, threshold=0.5)

    assert metrics["threshold"] == 0.5
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0
    assert 0.0 <= metrics["f1_score"] <= 1.0
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert metrics["confusion_matrix"]["true_positives"] == 3
    assert metrics["confusion_matrix"]["false_positives"] == 1
    assert metrics["confusion_matrix"]["false_negatives"] == 1
    assert metrics["confusion_matrix"]["true_negatives"] == 3


def test_tune_classification_thresholds():
    """Verify threshold tuning sweeps and outputs."""
    np.random.seed(42)
    n = 500
    y_val = np.random.binomial(1, 0.05, n)
    # Fraud probabilities higher for fraud cases
    y_prob = np.where(y_val == 1, np.random.uniform(0.6, 0.99, n), np.random.uniform(0.01, 0.4, n))

    results = tune_classification_thresholds(y_val, y_prob, cost_fn=500.0, cost_fp=25.0)

    assert "selected_classifier_threshold" in results
    assert "best_f1" in results
    assert "cost_optimal" in results
    assert "high_recall" in results
    assert "high_precision" in results

    best_thresh = results["selected_classifier_threshold"]
    assert 0.01 <= best_thresh <= 0.99
    assert results["best_f1"]["f1_score"] > 0.0

