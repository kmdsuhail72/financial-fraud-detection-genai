"""Synthetic behavioral dataset generator for FinGuard AI UEBA (Phase 14).

Usage:
    python scripts/generate_dataset.py --users 100 --events 5000 --output data/ueba_events.jsonl --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List


def generate_synthetic_events(num_users: int = 100, num_events: int = 5000, seed: int = 42) -> List[Dict]:
    random.seed(seed)

    cities_pool = ["New York", "San Francisco", "Chicago", "Boston", "London", "Austin", "Seattle", "Toronto"]
    anomaly_cities = ["Tokyo", "Moscow", "Lagos", "Reykjavik", "Sydney"]

    # 1. Generate user profiles and baselines
    users = []
    for i in range(1, num_users + 1):
        entity_id = f"CUS-{100000 + i}"
        tier = random.choice(["RETAIL", "HIGH_NET_WORTH", "COMMERCIAL"])
        if tier == "RETAIL":
            base_amt = round(random.uniform(30.0, 180.0), 2)
            std_amt = round(base_amt * 0.4, 2)
            active_hours = list(range(8, 22))
        elif tier == "HIGH_NET_WORTH":
            base_amt = round(random.uniform(1200.0, 4500.0), 2)
            std_amt = round(base_amt * 0.5, 2)
            active_hours = list(range(9, 20))
        else:
            base_amt = round(random.uniform(3500.0, 9000.0), 2)
            std_amt = round(base_amt * 0.45, 2)
            active_hours = list(range(8, 18))

        home_city = random.choice(cities_pool)
        user_devices = [f"dev_{entity_id}_{d}" for d in ["phone", "laptop"]][: random.choice([1, 2])]
        user_ips = [f"198.51.{i % 250}.{random.randint(10, 200)}"]

        users.append({
            "entity_id": entity_id,
            "tier": tier,
            "avg_amount": base_amt,
            "std_amount": std_amt,
            "active_hours": active_hours,
            "home_city": home_city,
            "devices": user_devices,
            "ips": user_ips,
        })

    # 2. Generate events
    start_time = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
    events = []

    for event_idx in range(1, num_events + 1):
        event_id = f"EVT-{20261100 + (event_idx // 1000):08d}-{event_idx:05d}"
        user = random.choice(users)

        # 8% chance of injected anomaly
        is_anomaly = random.random() < 0.08
        anomaly_type = None

        if not is_anomaly:
            # Baseline normal behavior
            hour = random.choice(user["active_hours"])
            event_time = start_time + timedelta(
                days=random.randint(0, 12),
                hours=hour,
                minutes=random.randint(0, 59),
            )
            amount = max(5.0, round(random.gauss(user["avg_amount"], user["std_amount"]), 2))
            device_id = random.choice(user["devices"])
            ip_address = random.choice(user["ips"])
            city = user["home_city"]
            velocity_1h = random.choice([1, 1, 1, 2])
            velocity_24h = random.randint(1, 5)
        else:
            # Anomaly injection
            anomaly_types = [
                "UNUSUAL_AMOUNT_SPIKE",
                "OFF_HOURS_ELEVATED_VALUE",
                "NEW_DEVICE_BURST",
                "IMPOSSIBLE_TRAVEL_VELOCITY",
                "MULTI_SIGNAL_ATTACK",
            ]
            anomaly_type = random.choice(anomaly_types)

            if anomaly_type == "UNUSUAL_AMOUNT_SPIKE":
                hour = random.choice(user["active_hours"])
                amount = round(user["avg_amount"] * random.uniform(8.0, 18.0), 2)
                device_id = random.choice(user["devices"])
                ip_address = random.choice(user["ips"])
                city = user["home_city"]
                velocity_1h = 1
                velocity_24h = 2

            elif anomaly_type == "OFF_HOURS_ELEVATED_VALUE":
                hour = random.choice([1, 2, 3, 4])  # Deep night
                amount = round(user["avg_amount"] * random.uniform(3.5, 7.0), 2)
                device_id = random.choice(user["devices"])
                ip_address = f"203.0.113.{random.randint(1, 250)}"  # external IP
                city = user["home_city"]
                velocity_1h = 2
                velocity_24h = 3

            elif anomaly_type == "NEW_DEVICE_BURST":
                hour = random.choice(user["active_hours"])
                amount = round(user["avg_amount"] * random.uniform(1.2, 2.5), 2)
                device_id = f"dev_unknown_rogue_{random.randint(100, 999)}"
                ip_address = f"192.0.2.{random.randint(1, 250)}"
                city = user["home_city"]
                velocity_1h = random.randint(5, 12)  # Burst
                velocity_24h = velocity_1h + 3

            elif anomaly_type == "IMPOSSIBLE_TRAVEL_VELOCITY":
                hour = random.choice(user["active_hours"])
                amount = round(user["avg_amount"] * random.uniform(1.5, 4.0), 2)
                device_id = f"dev_foreign_terminal_{random.randint(10, 99)}"
                ip_address = f"198.51.100.{random.randint(1, 250)}"
                city = random.choice(anomaly_cities)
                velocity_1h = 3
                velocity_24h = 6

            else:  # MULTI_SIGNAL_ATTACK
                hour = random.choice([2, 3, 4])
                amount = round(user["avg_amount"] * random.uniform(10.0, 25.0), 2)
                device_id = f"dev_adversary_bot_{random.randint(100, 999)}"
                ip_address = f"203.0.113.{random.randint(10, 90)}"
                city = random.choice(anomaly_cities)
                velocity_1h = random.randint(6, 15)
                velocity_24h = velocity_1h + 5

            event_time = start_time + timedelta(
                days=random.randint(0, 12),
                hours=hour,
                minutes=random.randint(0, 59),
            )

        events.append({
            "event_id": event_id,
            "entity_id": user["entity_id"],
            "timestamp": event_time.isoformat(),
            "amount": amount,
            "currency": "USD",
            "hour_of_day": hour,
            "device_id": device_id,
            "ip_address": ip_address,
            "city": city,
            "velocity_1h": velocity_1h,
            "velocity_24h": velocity_24h,
            "is_injected_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "user_avg_amount": user["avg_amount"],
            "user_std_amount": user["std_amount"],
        })

    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic behavioral events for UEBA testing and training.")
    parser.add_argument("--users", type=int, default=100, help="Number of distinct user entities")
    parser.add_argument("--events", type=int, default=5000, help="Total events to generate")
    parser.add_argument("--output", type=str, default="data/ueba_events.jsonl", help="Output JSONL file path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.events} synthetic events across {args.users} users (seed={args.seed})...")
    events = generate_synthetic_events(num_users=args.users, num_events=args.events, seed=args.seed)

    anomaly_count = sum(1 for e in events if e["is_injected_anomaly"])
    print(f"Generated {len(events)} events ({anomaly_count} injected anomalies, {anomaly_count / len(events):.2%}).")

    with open(out_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    print(f"Saved dataset to: {out_path.resolve()}")


if __name__ == "__main__":
    main()

