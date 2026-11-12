"""
FinGuard AI — Feature Preprocessing Pipeline & Feature Manifest Generator.

Normalizes incoming feature names and aliases, imputes missing values,
scales features, and produces a standardized feature manifest for model governance.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler

# Mapping common alias names from external clients/events to canonical feature names
FEATURE_ALIASES = {
    "amount": "transaction_amount",
    "transaction_count_5m_prior": "transaction_count_5m",
    "transaction_count_1h_prior": "transaction_count_1h",
    "new_device_flag": "new_device",
    "home_city_mismatch": "location_change",
    "is_international": "international_flag",
    "international": "international_flag",
    "velocity_5m": "transaction_count_5m",
    "velocity_1h": "transaction_count_1h",
}


@dataclass
class FeatureMetadata:
    name: str
    dtype: str
    mean: float
    std: float
    median: float
    min_val: float
    max_val: float
    default_value: float
    description: str


class FeaturePreprocessor(BaseEstimator, TransformerMixin):
    """
    Standardizes feature schemas, maps aliases, computes derived fields,
    imputes missing values, and produces scaled numpy arrays or aligned DataFrames.
    """

    def __init__(self, feature_names: Optional[List[str]] = None, scale_features: bool = True):
        self.feature_names = feature_names or []
        self.scale_features = scale_features
        self.scaler: Optional[StandardScaler] = None
        self.impute_values: Dict[str, float] = {}
        self.manifest: Dict[str, Any] = {}

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> "FeaturePreprocessor":
        """Fits imputer defaults and standard scaler from training data."""
        df = self._normalize_columns(X)
        if not self.feature_names:
            self.feature_names = list(df.columns)

        # Compute imputation defaults (median for numeric columns)
        for col in self.feature_names:
            val = float(df[col].median()) if col in df else 0.0
            self.impute_values[col] = val

        # Handle derived logic defaults if present
        if "amount_deviation" in self.feature_names and self.impute_values.get("amount_deviation", 0.0) == 0.0:
            self.impute_values["amount_deviation"] = 1.0

        aligned = self._align_and_impute(df)

        if self.scale_features:
            self.scaler = StandardScaler()
            self.scaler.fit(aligned)

        # Build feature manifest
        self.manifest = self._build_manifest(df)
        return self

    def transform(self, X: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> np.ndarray:
        """Transforms input data into model-ready numpy array."""
        df = self._normalize_input(X)
        aligned = self._align_and_impute(df)

        if self.scale_features and self.scaler is not None:
            return self.scaler.transform(aligned)
        return aligned.to_numpy(dtype=np.float32)

    def transform_df(self, X: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> pd.DataFrame:
        """Transforms input data and returns an aligned DataFrame with original column names."""
        df = self._normalize_input(X)
        return self._align_and_impute(df)

    def _normalize_input(self, X: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> pd.DataFrame:
        if isinstance(X, dict):
            # Check if nested features dict: e.g. {"transaction_id": "...", "features": {...}}
            if "features" in X and isinstance(X["features"], dict):
                row = dict(X["features"])
                if "transaction_id" in X and "transaction_id" not in row:
                    row["transaction_id"] = X["transaction_id"]
                df = pd.DataFrame([row])
            else:
                df = pd.DataFrame([X])
        elif isinstance(X, list):
            rows = []
            for item in X:
                if isinstance(item, dict) and "features" in item and isinstance(item["features"], dict):
                    row = dict(item["features"])
                    if "transaction_id" in item and "transaction_id" not in row:
                        row["transaction_id"] = item["transaction_id"]
                    rows.append(row)
                else:
                    rows.append(item)
            df = pd.DataFrame(rows)
        elif isinstance(X, pd.DataFrame):
            df = X.copy()
        else:
            raise ValueError(f"Unsupported input type: {type(X)}")

        return self._normalize_columns(df)

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies canonical column name aliases and computes derivations."""
        renamed = {}
        for col in df.columns:
            lower = col.lower()
            if lower in FEATURE_ALIASES:
                renamed[col] = FEATURE_ALIASES[lower]
        df = df.rename(columns=renamed)

        # Fallbacks for derived features if missing
        if "transaction_amount" in df.columns:
            if "avg_amount_24h" not in df.columns:
                df["avg_amount_24h"] = df["transaction_amount"]
            if "amount_deviation" not in df.columns:
                # amount_deviation = transaction_amount / max(avg_amount_24h, 1.0)
                denom = df["avg_amount_24h"].replace(0, np.nan).fillna(1.0).clip(lower=1.0)
                df["amount_deviation"] = df["transaction_amount"] / denom

        return df

    def _align_and_impute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures all expected feature columns are present and imputed."""
        out = pd.DataFrame(index=df.index)
        for col in self.feature_names:
            if col in df.columns:
                series = pd.to_numeric(df[col], errors="coerce")
                default_val = self.impute_values.get(col, 0.0)
                out[col] = series.fillna(default_val).astype(float)
            else:
                out[col] = float(self.impute_values.get(col, 0.0))
        return out[self.feature_names]

    def _build_manifest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generates detailed metadata dictionary for feature_manifest.json."""
        feature_entries = []
        descriptions = {
            "transaction_amount": "Monetary value of the banking transaction in account currency",
            "avg_amount_24h": "Historical 24-hour rolling average transaction amount for this customer account",
            "transaction_count_5m": "Velocity metric: number of transactions in prior 5 minutes",
            "transaction_count_1h": "Velocity metric: number of transactions in prior 1 hour",
            "amount_deviation": "Ratio of transaction amount to 24-hour historical baseline amount",
            "new_device": "Binary indicator (1.0 = true) flagging an unrecognized device ID",
            "location_change": "Binary indicator (1.0 = true) flagging transaction outside customer home city",
            "international_flag": "Binary indicator (1.0 = true) flagging cross-border / foreign transaction",
            "merchant_risk": "Historical merchant fraud risk index [0.0 - 1.0]",
            "account_age_days": "Customer account age in days since origination",
        }

        for col in self.feature_names:
            if col in df.columns:
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                mean = float(s.mean()) if not s.empty else 0.0
                std = float(s.std()) if not s.empty else 1.0
                median = float(s.median()) if not s.empty else 0.0
                min_v = float(s.min()) if not s.empty else 0.0
                max_v = float(s.max()) if not s.empty else 1.0
            else:
                mean, std, median, min_v, max_v = 0.0, 1.0, 0.0, 0.0, 1.0

            meta = FeatureMetadata(
                name=col,
                dtype="float64",
                mean=round(mean, 4),
                std=round(std, 4),
                median=round(median, 4),
                min_val=round(min_v, 4),
                max_val=round(max_v, 4),
                default_value=round(self.impute_values.get(col, median), 4),
                description=descriptions.get(col, f"Feature {col}"),
            )
            feature_entries.append(asdict(meta))

        return {
            "version": "1.0.0",
            "num_features": len(self.feature_names),
            "feature_names": self.feature_names,
            "features": feature_entries,
            "aliases": FEATURE_ALIASES,
        }

    def export_manifest(self) -> Dict[str, Any]:
        return self.manifest

