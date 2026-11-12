"""
Phase 5 Sample Data Generator.
Creates sample Bronze JSON transaction events partitioned by date and hour.
"""
import argparse
import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List


def generate_sample_transactions(count: int = 500, seed: int = 42) -> List[Dict]:
    rng = random.Random(seed)
    base_time = datetime(2026, 11, 12, 0, 0, 0, tzinfo=timezone.utc)
    channels = ["MOBILE", "WEB", "POS", "ATM"]
    categories = ["GROCERY", "ELECTRONICS", "TRAVEL", "JEWELRY", "DINING", "UTILITIES"]
    cities = ["Mumbai", "Delhi", "Bengaluru", "Kolkata", "Hyderabad", "Chennai"]

    transactions = []
    for i in range(1, count + 1):
        txn_id = f"TXN-20261112-{i:06d}"
        account_id = f"ACC-{100000 + (i % 80):06d}"
        customer_id = f"CUS-{200000 + (i % 50):06d}"
        category = rng.choice(categories)
        amount = round(rng.uniform(100.0, 95000.0), 2)
        channel = rng.choice(channels)
        city = rng.choice(cities)

        # Spread timestamps across 24 hours
        time_offset_sec = int((86400 / max(1, count)) * i + rng.uniform(-60, 60))
        txn_time = base_time + timedelta(seconds=max(0, time_offset_sec))

        features = {
            "transaction_count_5m_prior": rng.randint(0, 5),
            "transaction_count_1h_prior": rng.randint(0, 15),
            "average_amount_1h_prior": round(rng.uniform(1000.0, 10000.0), 2),
            "amount_vs_prior_average": round(rng.uniform(0.5, 8.5), 2),
            "new_device_flag": 1 if rng.random() < 0.15 else 0,
            "home_city_mismatch": 1 if rng.random() < 0.10 else 0,
            "is_international": 1 if rng.random() < 0.05 else 0,
            "amount_log1p": round(float(__import__("math").log1p(amount)), 4)
        }

        txn = {
            "transaction_id": txn_id,
            "account_id": account_id,
            "customer_id": customer_id,
            "transaction_type": "CARD_PAYMENT" if channel in ["POS", "WEB"] else "UPI_TRANSFER",
            "amount": amount,
            "currency": "INR",
            "merchant_id": f"MER-{90000 + (i % 30):05d}",
            "merchant_category": category,
            "channel": channel,
            "location": {
                "country": "IN",
                "city": city
            },
            "device_id": f"DEV-{40000 + (i % 60):05d}",
            "ip_address": f"192.0.2.{rng.randint(2, 250)}",
            "is_international": False,
            "transaction_timestamp": txn_time.isoformat(),
            "features": features,
            "processing_version": "phase4-v1"
        }
        transactions.append(txn)

    return transactions


def write_partitioned_sample_data(transactions: List[Dict], output_dir: str) -> List[str]:
    created_files = []
    # Group by partition path: year=YYYY/month=MM/day=DD/hour=HH
    partition_groups: Dict[str, List[Dict]] = {}

    for txn in transactions:
        dt = datetime.fromisoformat(txn["transaction_timestamp"].replace("Z", "+00:00"))
        part_key = f"year={dt.strftime('%Y')}/month={dt.strftime('%m')}/day={dt.strftime('%d')}/hour={dt.strftime('%H')}"
        partition_groups.setdefault(part_key, []).append(txn)

    for part_path, group_txns in partition_groups.items():
        target_dir = os.path.join(output_dir, part_path)
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, "transactions_part_001.json")

        with open(file_path, "w", encoding="utf-8") as f:
            for item in group_txns:
                f.write(json.dumps(item) + "\n")

        created_files.append(file_path)

    return created_files


def main():
    parser = argparse.ArgumentParser(description="Create Bronze Sample Data for Phase 5 Data Lake")
    parser.add_argument("--output", type=str, default="data/phase5-sample", help="Output directory")
    parser.add_argument("--count", type=int, default=500, help="Total transactions count")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    txns = generate_sample_transactions(count=args.count, seed=args.seed)
    files = write_partitioned_sample_data(txns, args.output)

    print(f"Generated {len(txns)} transactions across {len(files)} partition files in '{args.output}'.")


if __name__ == "__main__":
    main()
