"""
Local Data Lake Transformation Utility (Bronze -> Silver -> Gold).
Converts Bronze JSON to partitioned Parquet and computes Gold analytical aggregates.
"""
import argparse
import json
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd


def flatten_transaction(txn: Dict) -> Dict:
    """Flattens nested location and feature attributes for tabular Parquet storage."""
    flat = {
        "transaction_id": txn["transaction_id"],
        "account_id": txn["account_id"],
        "customer_id": txn["customer_id"],
        "transaction_type": txn.get("transaction_type", "CARD_PAYMENT"),
        "amount": float(txn["amount"]),
        "currency": txn.get("currency", "INR"),
        "merchant_id": txn.get("merchant_id", ""),
        "merchant_category": txn.get("merchant_category", ""),
        "channel": txn.get("channel", ""),
        "device_id": txn.get("device_id", ""),
        "ip_address": txn.get("ip_address", ""),
        "is_international": bool(txn.get("is_international", False)),
        "transaction_timestamp": txn["transaction_timestamp"],
    }

    # Flatten location
    loc = txn.get("location", {})
    flat["location_country"] = loc.get("country", "IN") if isinstance(loc, dict) else "IN"
    flat["location_city"] = loc.get("city", "") if isinstance(loc, dict) else ""

    # Flatten features
    feats = txn.get("features", {})
    if isinstance(feats, dict):
        for k, v in feats.items():
            flat[f"feat_{k}"] = v

    # Add partition columns
    dt = datetime.fromisoformat(txn["transaction_timestamp"].replace("Z", "+00:00"))
    flat["year"] = int(dt.strftime("%Y"))
    flat["month"] = int(dt.strftime("%m"))
    flat["day"] = int(dt.strftime("%d"))

    return flat


def load_bronze_json(input_dir: str) -> List[Dict]:
    """Recursively reads all JSON records from the Bronze directory."""
    records = []
    for root, _, files in os.walk(input_dir):
        for fname in files:
            if fname.endswith(".json") or fname.endswith(".jsonl"):
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str:
                            try:
                                records.append(json.loads(line_str))
                            except Exception:
                                pass
    return records


def transform_bronze_to_silver(records: List[Dict], silver_output_dir: str) -> pd.DataFrame:
    """Deduplicates, flattens, and writes partitioned Parquet with Snappy compression."""
    if not records:
        return pd.DataFrame()

    flattened = [flatten_transaction(r) for r in records]
    df = pd.DataFrame(flattened)

    # Deduplicate by transaction_id (preserve last occurrence)
    df = df.drop_duplicates(subset=["transaction_id"], keep="last")

    os.makedirs(silver_output_dir, exist_ok=True)

    # Write partitioned Parquet
    df.to_parquet(
        silver_output_dir,
        partition_cols=["year", "month", "day"],
        compression="snappy",
        index=False
    )
    return df


def generate_gold_aggregates(silver_df: pd.DataFrame, gold_output_dir: str) -> Dict[str, pd.DataFrame]:
    """Computes daily, channel, and merchant analytics marts in Gold layer."""
    if silver_df.empty:
        return {}

    os.makedirs(gold_output_dir, exist_ok=True)

    # 1. Daily Volume & Risk Mart
    daily_mart = silver_df.groupby(["year", "month", "day"]).agg(
        total_transactions=("transaction_id", "count"),
        total_volume_inr=("amount", "sum"),
        average_amount=("amount", "mean"),
        max_amount=("amount", "max"),
        new_device_count=("feat_new_device_flag", "sum"),
        city_mismatch_count=("feat_home_city_mismatch", "sum")
    ).reset_index()

    daily_path = os.path.join(gold_output_dir, "daily_summary.parquet")
    daily_mart.to_parquet(daily_path, compression="snappy", index=False)

    # 2. Channel Performance Mart
    channel_mart = silver_df.groupby("channel").agg(
        transaction_count=("transaction_id", "count"),
        total_volume=("amount", "sum"),
        average_ticket_size=("amount", "mean")
    ).reset_index()

    channel_path = os.path.join(gold_output_dir, "channel_summary.parquet")
    channel_mart.to_parquet(channel_path, compression="snappy", index=False)

    # 3. Merchant Category Risk Mart
    merchant_mart = silver_df.groupby("merchant_category").agg(
        transaction_count=("transaction_id", "count"),
        total_spend=("amount", "sum"),
        high_velocity_bursts=("feat_transaction_count_5m_prior", lambda x: (x >= 4).sum())
    ).reset_index()

    merchant_path = os.path.join(gold_output_dir, "merchant_category_summary.parquet")
    merchant_mart.to_parquet(merchant_path, compression="snappy", index=False)

    return {
        "daily_mart": daily_mart,
        "channel_mart": channel_mart,
        "merchant_mart": merchant_mart
    }


def main():
    parser = argparse.ArgumentParser(description="Local Data Lake Transformation (Bronze -> Silver -> Gold)")
    parser.add_argument("--input", type=str, default="data/phase5-sample", help="Bronze input directory")
    parser.add_argument("--output", type=str, default="data/phase5-parquet", help="Parquet output root directory")
    args = parser.parse_args()

    silver_dir = os.path.join(args.output, "silver", "transactions")
    gold_dir = os.path.join(args.output, "gold")

    print(f"Reading Bronze JSON records from: {args.input}")
    records = load_bronze_json(args.input)
    print(f"[*] Read {len(records)} raw records.")

    print(f"[*] Transforming to Silver Parquet in: {silver_dir}")
    silver_df = transform_bronze_to_silver(records, silver_dir)
    print(f"[+] Silver Parquet written ({len(silver_df)} deduplicated records).")

    print(f"[*] Aggregating Gold analytics marts in: {gold_dir}")
    marts = generate_gold_aggregates(silver_df, gold_dir)
    print(f"[+] Gold marts generated: {list(marts.keys())}")


if __name__ == "__main__":
    main()
