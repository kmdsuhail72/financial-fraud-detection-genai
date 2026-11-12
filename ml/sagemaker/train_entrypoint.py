"""
FinGuard AI — AWS SageMaker Training Container Entrypoint.

Compatible with AWS SageMaker Scikit-Learn / XGBoost pre-built containers.
Reads input channels from /opt/ml/input/data/, hyperparameters from
/opt/ml/input/config/hyperparameters.json, and writes model artifacts to /opt/ml/model/.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path if running inside container
sys.path.insert(0, "/opt/ml/code")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.data_loader import load_and_merge_dataset, split_dataset
from ml.training.trainer import train_fraud_detection_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sagemaker-train")


def main():
    parser = argparse.ArgumentParser()

    # SageMaker standard environment paths
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train-dir", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--model-type", type=str, default="random_forest")
    parser.add_argument("--label-column", type=str, default="is_fraud")

    args, _ = parser.parse_known_args()

    train_path = Path(args.train_dir)
    features_csv = train_path / "transaction_features.csv"
    labels_csv = train_path / "fraud_labels.csv"

    if not features_csv.exists() or not labels_csv.exists():
        # Check if single merged CSV was uploaded
        merged_csv = train_path / "train.csv"
        if merged_csv.exists():
            features_csv = merged_csv
            labels_csv = merged_csv
        else:
            raise FileNotFoundError(f"Missing required training data in {train_path}")

    logger.info("SageMaker Training started. Reading from %s, saving to %s", train_path, args.model_dir)

    X, y, ids, _ = load_and_merge_dataset(
        features_path=features_csv,
        labels_path=labels_csv,
        label_column=args.label_column,
    )

    splits = split_dataset(X, y, ids, val_size=0.15, test_size=0.15)
    train_fraud_detection_pipeline(
        splits=splits,
        model_type=args.model_type,
        output_dir=args.model_dir,
    )

    logger.info("SageMaker Training completed successfully.")


if __name__ == "__main__":
    main()

