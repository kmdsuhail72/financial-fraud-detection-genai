#!/usr/bin/env python3
"""
FinGuard AI — Model Training CLI (Phase 6).

Executes end-to-end model training, anomaly detection, threshold optimization,
and model artifact generation.

Usage:
    python scripts/phase6/train.py \\
      --features data/generated/transaction_features.csv \\
      --labels data/generated/fraud_labels.csv \\
      --output artifacts \\
      --label-column is_fraud \\
      --model random_forest
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data_loader import load_and_merge_dataset, split_dataset
from ml.training.trainer import train_fraud_detection_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("finguard-train")


def parse_args():
    parser = argparse.ArgumentParser(description="FinGuard AI Model Training Engine")
    parser.add_argument(
        "--features",
        type=str,
        default="data/generated/transaction_features.csv",
        help="Path to transaction features CSV file",
    )
    parser.add_argument(
        "--labels",
        type=str,
        default="data/generated/fraud_labels.csv",
        help="Path to fraud ground-truth labels CSV file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts",
        help="Destination directory for serialized model and audit artifacts",
    )
    parser.add_argument(
        "--label-column",
        type=str,
        default="is_fraud",
        help="Name of the binary target label column (default: is_fraud)",
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["random_forest", "xgboost"],
        default="random_forest",
        help="Supervised model architecture to train (random_forest or xgboost)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger.info("=============================================================")
    logger.info("FinGuard AI — Phase 6 Fraud & Anomaly Model Training")
    logger.info("Features path:   %s", args.features)
    logger.info("Labels path:     %s", args.labels)
    logger.info("Label column:    %s", args.label_column)
    logger.info("Model type:      %s", args.model)
    logger.info("Output dir:      %s", args.output)
    logger.info("=============================================================")

    # 1. Load and merge data with strict target leakage prevention
    X, y, ids, feature_names = load_and_merge_dataset(
        features_path=args.features,
        labels_path=args.labels,
        label_column=args.label_column,
    )

    # 2. Split dataset into Stratified Train / Val / Test
    splits = split_dataset(X, y, ids, val_size=0.15, test_size=0.15, random_state=args.seed)
    logger.info("Dataset Split Summary:")
    logger.info("  Train set: %d rows (Fraud rate: %.2f%%)", len(splits.X_train), splits.train_fraud_rate * 100)
    logger.info("  Val set:   %d rows (Fraud rate: %.2f%%)", len(splits.X_val), splits.val_fraud_rate * 100)
    logger.info("  Test set:  %d rows (Fraud rate: %.2f%%)", len(splits.X_test), splits.test_fraud_rate * 100)

    # 3. Train models, tune thresholds, evaluate test set, and save artifacts
    _, metadata = train_fraud_detection_pipeline(
        splits=splits,
        model_type=args.model,
        output_dir=args.output,
        random_state=args.seed,
    )

    test_metrics = metadata["test_metrics"]
    logger.info("=============================================================")
    logger.info("Training Completed Successfully!")
    logger.info("Selected Classifier Threshold: %.4f", metadata["selected_threshold"])
    logger.info("Held-Out Test Set Metrics:")
    logger.info("  Precision: %.4f", test_metrics["precision"])
    logger.info("  Recall:    %.4f", test_metrics["recall"])
    logger.info("  F1-Score:  %.4f", test_metrics["f1_score"])
    logger.info("  ROC-AUC:   %.4f", test_metrics["roc_auc"])
    logger.info("  PR-AUC:    %.4f", test_metrics["pr_auc"])
    logger.info("Confusion Matrix:")
    logger.info("  True Positives:  %d", test_metrics["confusion_matrix"]["true_positives"])
    logger.info("  False Positives: %d", test_metrics["confusion_matrix"]["false_positives"])
    logger.info("  False Negatives: %d", test_metrics["confusion_matrix"]["false_negatives"])
    logger.info("  True Negatives:  %d", test_metrics["confusion_matrix"]["true_negatives"])
    logger.info("Artifacts saved to: %s", args.output)
    logger.info("=============================================================")


if __name__ == "__main__":
    main()
