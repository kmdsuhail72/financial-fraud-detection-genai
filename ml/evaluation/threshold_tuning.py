"""
FinGuard AI — Threshold Optimization & Cost-Sensitive Tuning.

Evaluates candidate decision thresholds on validation data to optimize
F1-score, high-recall, high-precision, and total financial operating cost.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


def tune_classification_thresholds(
    y_val: np.ndarray,
    y_prob_val: np.ndarray,
    cost_fn: float = 500.0,
    cost_fp: float = 25.0,
    target_high_recall: float = 0.90,
    target_high_precision: float = 0.90,
) -> Dict[str, Any]:
    """
    Sweeps decision cutoffs from 0.01 to 0.99 to find optimal thresholds.

    Args:
        y_val: Validation ground truth binary labels.
        y_prob_val: Validation predicted fraud probabilities.
        cost_fn: Cost of a False Negative (missed fraud loss).
        cost_fp: Cost of a False Positive (manual review overhead).
        target_high_recall: Target recall for conservative alert policy.
        target_high_precision: Target precision for automated blocking policy.

    Returns:
        Structured dictionary matching thresholds.json schema.
    """
    y_val = np.asarray(y_val).astype(int)
    y_prob_val = np.asarray(y_prob_val).astype(float)

    thresholds = np.linspace(0.01, 0.99, 99)

    best_f1_val = -1.0
    best_f1_thresh = 0.5
    best_f1_metrics = {}

    min_cost = float("inf")
    cost_opt_thresh = 0.5
    cost_opt_metrics = {}

    high_rec_thresh = 0.01
    high_rec_metrics = {}

    high_prec_thresh = 0.99
    high_prec_metrics = {}

    for t in thresholds:
        t_val = round(float(t), 2)
        y_pred = (y_prob_val >= t_val).astype(int)
        cm = confusion_matrix(y_val, y_pred, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        p = float(precision_score(y_val, y_pred, zero_division=0))
        r = float(recall_score(y_val, y_pred, zero_division=0))
        f1 = float(f1_score(y_val, y_pred, zero_division=0))
        total_cost = float(fn * cost_fn + fp * cost_fp)

        metrics_obj = {
            "threshold": t_val,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f1, 4),
            "cost": round(total_cost, 2),
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn),
        }

        # Check Best F1
        if f1 > best_f1_val:
            best_f1_val = f1
            best_f1_thresh = t_val
            best_f1_metrics = metrics_obj

        # Check Cost Optimal
        if total_cost < min_cost:
            min_cost = total_cost
            cost_opt_thresh = t_val
            cost_opt_metrics = metrics_obj

        # Check High Recall (highest threshold that still meets target recall)
        if r >= target_high_recall:
            high_rec_thresh = t_val
            high_rec_metrics = metrics_obj

        # Check High Precision (lowest threshold that meets target precision)
        if p >= target_high_precision and not high_prec_metrics:
            high_prec_thresh = t_val
            high_prec_metrics = metrics_obj

    # Fallback if targets were not met
    if not high_rec_metrics:
        high_rec_metrics = best_f1_metrics
        high_rec_thresh = best_f1_thresh
    if not high_prec_metrics:
        high_prec_metrics = best_f1_metrics
        high_prec_thresh = best_f1_thresh

    return {
        "selected_classifier_threshold": best_f1_thresh,
        "best_f1": best_f1_metrics,
        "cost_optimal": cost_opt_metrics,
        "high_recall": high_rec_metrics,
        "high_precision": high_prec_metrics,
        "cost_assumptions": {
            "false_negative_cost_usd": cost_fn,
            "false_positive_cost_usd": cost_fp,
        },
        "risk_tier_thresholds": {
            "critical_review": 0.80,
            "high_investigate": 0.60,
            "medium_monitor": 0.35,
            "low_allow": 0.00,
        },
    }

