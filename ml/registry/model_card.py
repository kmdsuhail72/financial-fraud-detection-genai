"""
FinGuard AI — Model Card Generator for Model Governance & Auditability.

Produces standardized model documentation compliant with financial risk management
and AI governance frameworks (e.g., SR 11-7 model risk management guidance).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def generate_model_card(
    model_version: str,
    model_type: str,
    feature_names: List[str],
    train_metrics: Dict[str, Any],
    val_metrics: Dict[str, Any],
    test_metrics: Dict[str, Any],
    thresholds: Dict[str, Any],
    dataset_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """Generates comprehensive Model Card metadata dictionary."""
    return {
        "model_details": {
            "model_name": "FinGuard AI Real-Time Fraud & Anomaly Detection Platform",
            "model_version": model_version,
            "model_family": "Supervised Tree Classifier + Unsupervised Isolation Forest",
            "classifier_architecture": "RandomForestClassifier" if model_type == "random_forest" else "XGBClassifier",
            "anomaly_detector_architecture": "IsolationForest",
            "creation_date": datetime.now(timezone.utc).isoformat(),
            "framework": "Scikit-learn / XGBoost",
            "license": "Apache-2.0",
        },
        "intended_use": {
            "primary_intended_uses": [
                "Real-time fraud risk scoring of inbound payment events",
                "Unsupervised anomaly detection for novel zero-day attack patterns",
                "Prioritization and routing of high-risk transactions to compliance investigators",
            ],
            "out_of_scope_uses": [
                "Autonomous irrevocable account termination without human oversight",
                "Credit scoring or lending risk assessment",
            ],
        },
        "target_leakage_safeguards": {
            "leakage_prevention_status": "ENFORCED",
            "excluded_columns": [
                "is_fraud",
                "fraud_scenario",
                "scenario_name",
                "injected_scenario",
                "label",
                "is_flagged",
            ],
            "feature_isolation": "Features computed strictly prior to or at transaction timestamp without ground-truth label visibility.",
        },
        "input_features": {
            "feature_count": len(feature_names),
            "features": feature_names,
        },
        "training_dataset": dataset_summary,
        "performance_evaluation": {
            "test_set_metrics": test_metrics,
            "validation_set_metrics": val_metrics,
            "training_set_metrics": train_metrics,
            "evaluation_threshold": test_metrics.get("threshold", 0.5),
        },
        "threshold_policy": thresholds,
        "governance_and_compliance": {
            "decision_rule": "Unified Risk Score = 0.65 * P(Supervised Fraud) + 0.35 * A(Anomaly Score)",
            "advisory_note": "ML model generates risk estimates; human investigators and rule policies make binding financial decisions.",
            "drift_monitoring_recommendation": "CloudWatch / SageMaker Clarify for population stability index (PSI) and concept drift.",
        },
    }
