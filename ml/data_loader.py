"""
FinGuard AI — ML Dataset Loader & Target Leakage Prevention.

Loads transaction features and fraud labels, merges strictly on transaction_id,
enforces strict target leakage prevention by excluding any label/scenario attributes
from the feature matrix, and produces reproducible train/val/test splits.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# Explicit list of columns that must NEVER enter the feature matrix (leakage prevention)
LEAKAGE_COLUMNS = {
    "is_fraud",
    "fraud_scenario",
    "scenario_name",
    "injected_scenario",
    "label",
    "is_flagged",
    "fraud_flag",
    "fraud_label",
    "target",
}

# Identifier columns that should not be used as numeric/classification features
IDENTIFIER_COLUMNS = {
    "transaction_id",
    "account_id",
    "customer_id",
    "device_id",
    "merchant_id",
    "timestamp",
    "transaction_timestamp",
}


@dataclass
class DatasetSplits:
    """Encapsulates reproducible Train, Validation, and Test dataset splits."""
    X_train: pd.DataFrame
    y_train: pd.Series
    X_val: pd.DataFrame
    y_val: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series
    feature_names: List[str]
    train_ids: pd.Series
    val_ids: pd.Series
    test_ids: pd.Series

    @property
    def train_fraud_rate(self) -> float:
        return float(self.y_train.mean())

    @property
    def val_fraud_rate(self) -> float:
        return float(self.y_val.mean())

    @property
    def test_fraud_rate(self) -> float:
        return float(self.y_test.mean())


def load_and_merge_dataset(
    features_path: Union[str, Path],
    labels_path: Union[str, Path],
    label_column: str = "is_fraud",
    id_column: str = "transaction_id",
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, List[str]]:
    """
    Loads features and labels from CSV files and merges them on transaction_id.

    Returns:
        X: Feature matrix with target and identifier columns cleanly removed.
        y: Binary label Series.
        ids: Series of transaction IDs corresponding to rows in X.
        feature_names: List of column names in X.
    """
    feat_path = Path(features_path)
    lbl_path = Path(labels_path)

    if not feat_path.exists():
        raise FileNotFoundError(f"Features file not found at: {feat_path}")
    if not lbl_path.exists():
        raise FileNotFoundError(f"Labels file not found at: {lbl_path}")

    # Load data
    df_features = pd.read_csv(feat_path)
    df_labels = pd.read_csv(lbl_path)

    if id_column not in df_features.columns:
        raise ValueError(f"Features file missing required ID column: '{id_column}'")
    if id_column not in df_labels.columns:
        raise ValueError(f"Labels file missing required ID column: '{id_column}'")
    if label_column not in df_labels.columns:
        raise ValueError(f"Labels file missing required label column: '{label_column}'")

    # Merge on transaction_id
    merged = pd.merge(df_features, df_labels[[id_column, label_column]], on=id_column, how="inner")
    logger.info("Merged %d records from features and labels on %s", len(merged), id_column)

    # Extract target and IDs
    y = merged[label_column].astype(int)
    ids = merged[id_column].copy()

    # Drop leakage columns and identifier columns
    cols_to_drop = [
        col for col in merged.columns
        if col.lower() in LEAKAGE_COLUMNS or col.lower() in IDENTIFIER_COLUMNS or col == label_column
    ]
    X = merged.drop(columns=cols_to_drop, errors="ignore")

    # Ensure all remaining columns are numeric/boolean
    for col in X.columns:
        if X[col].dtype == object or X[col].dtype == bool:
            try:
                X[col] = X[col].astype(float)
            except Exception:
                # If non-numeric categorical, drop or encode
                logger.warning("Dropping non-numeric column '%s' from feature matrix", col)
                X = X.drop(columns=[col])

    feature_names = list(X.columns)
    logger.info("Cleaned feature matrix: %d rows, %d features: %s", len(X), len(feature_names), feature_names)

    return X, y, ids, feature_names


def split_dataset(
    X: pd.DataFrame,
    y: pd.Series,
    ids: pd.Series,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> DatasetSplits:
    """
    Splits features and labels into Stratified Train, Validation, and Test sets.

    Default ratio:
      - Train: 70%
      - Validation: 15%
      - Test: 15%
    """
    total_val_test = val_size + test_size
    test_ratio_of_holdout = test_size / total_val_test

    # First split: Train vs Holdout (Val + Test)
    X_train, X_holdout, y_train, y_holdout, ids_train, ids_holdout = train_test_split(
        X, y, ids,
        test_size=total_val_test,
        stratify=y,
        random_state=random_state,
    )

    # Second split: Validation vs Test
    X_val, X_test, y_val, y_test, ids_val, ids_test = train_test_split(
        X_holdout, y_holdout, ids_holdout,
        test_size=test_ratio_of_holdout,
        stratify=y_holdout,
        random_state=random_state,
    )

    return DatasetSplits(
        X_train=X_train.reset_index(drop=True),
        y_train=y_train.reset_index(drop=True),
        X_val=X_val.reset_index(drop=True),
        y_val=y_val.reset_index(drop=True),
        X_test=X_test.reset_index(drop=True),
        y_test=y_test.reset_index(drop=True),
        feature_names=list(X.columns),
        train_ids=ids_train.reset_index(drop=True),
        val_ids=ids_val.reset_index(drop=True),
        test_ids=ids_test.reset_index(drop=True),
    )

