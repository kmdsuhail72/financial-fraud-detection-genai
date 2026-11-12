"""
FinGuard AI — Machine Learning Evaluation Metrics.

Computes precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix,
and financial performance indicators for model assessment and compliance reporting.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Computes a comprehensive set of classification and calibration metrics.

    Args:
        y_true: Ground truth binary labels (0 or 1).
        y_prob: Predicted fraud probabilities [0.0 - 1.0].
        threshold: Classification decision cutoff.

    Returns:
        Dictionary of serialized performance metrics.
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Core detection metrics
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Curve AUCs
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except ValueError:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except ValueError:
        pr_auc = float(np.mean(y_true))

    # Additional diagnostic metrics
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    brier = float(brier_score_loss(y_true, y_prob))

    try:
        loss = float(log_loss(y_true, np.clip(y_prob, 1e-7, 1 - 1e-7)))
    except Exception:
        loss = 0.0

    return {
        "threshold": round(threshold, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "specificity": round(specificity, 4),
        "false_positive_rate": round(fpr, 4),
        "brier_score": round(brier, 4),
        "log_loss": round(loss, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "sample_count": len(y_true),
        "positive_count": int(np.sum(y_true)),
        "negative_count": int(len(y_true) - np.sum(y_true)),
        "base_fraud_rate": round(float(np.mean(y_true)), 4),
    }
