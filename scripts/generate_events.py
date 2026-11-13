"""Phase 19 — Synthetic Temporal Transaction Event Generator.

Generates chronological event streams with:
- Legitimate baseline transaction rhythms
- Rapid burst laundering loops (e.g. 5 transfers within 3 minutes)
- Fan-in mule structuring patterns
- Dynamic device & IP shifts

Usage:
    python scripts/generate_events.py --events 500 --output examples/temporal_events.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def generate_synthetic_temporal_events(num_events: int = 500) -> List[Dict[str, Any]]:
    random.seed(42)
    events: List[Dict[str, Any]] = []

    base_time = 1794500000.0  # reference start time
    current_time = base_time

    # Normal entities pool
    normal_accounts = [f"ACC-TEMP-{i:03d}" for i in range(10, 60)]
    normal_devices = [f"DEV-TEMP-{i:02d}" for i in range(10, 40)]
    normal_ips = [f"198.51.100.{i}" for i in range(10, 80)]
    normal_merchants = [f"MER-TEMP-{i:02d}" for i in range(1, 10)]

    # Fraud syndicate pool
    syndicate_accounts = [f"ACC-BURST-{i:02d}" for i in range(1, 6)]
    rogue_device = "DEV-ROGUE-01"
    tor_ip = "192.0.2.99"
    cashout_crypto = "MER-CRYPTO-99"

    for i in range(1, num_events + 1):
        # 15% probability of temporal fraud burst
        is_fraud_event = random.random() < 0.15

        if is_fraud_event:
            # Bursts occur within seconds of each other
            current_time += random.uniform(10.0, 45.0)
            src = random.choice(syndicate_accounts)
            dst = random.choice(syndicate_accounts)
            while dst == src:
                dst = random.choice(syndicate_accounts)

            amount = round(random.uniform(5000.0, 15000.0), 2)
            device = rogue_device
            ip = tor_ip
            merchant = cashout_crypto if random.random() < 0.3 else None
            is_fraud = True
        else:
            # Normal events spaced by minutes/hours
            current_time += random.uniform(120.0, 900.0)
            src = random.choice(normal_accounts)
            dst = random.choice(normal_accounts)
            while dst == src:
                dst = random.choice(normal_accounts)

            amount = round(random.uniform(15.0, 350.0), 2)
            device = random.choice(normal_devices)
            ip = random.choice(normal_ips)
            merchant = random.choice(normal_merchants) if random.random() < 0.4 else None
            is_fraud = False

        event = {
            "transaction_id": f"TXN-TEMP-{i:05d}",
            "timestamp": round(current_time, 2),
            "source_account": src,
            "target_account": dst if not merchant else None,
            "merchant_id": merchant,
            "device_id": device,
            "ip_address": ip,
            "amount": amount,
            "currency": "USD",
            "channel": "mobile" if random.random() < 0.8 else "web",
            "event_type": "PAYMENT" if merchant else "TRANSFER",
            "is_fraud": is_fraud,
        }
        events.append(event)

    return events


def generate_training_records(events: List[Dict[str, Any]], seq_len: int = 5) -> List[Dict[str, Any]]:
    """Converts raw event stream into chronological sequence records for GRU training."""
    from temporal.feature_engineer import TemporalFeatureEngineer
    from temporal.models import TemporalTransactionEvent
    from temporal.temporal_graph import TemporalGraph

    graph = TemporalGraph()
    engineer = TemporalFeatureEngineer(graph)
    records: List[Dict[str, Any]] = []

    for ev_dict in events:
        ev = TemporalTransactionEvent(**ev_dict)
        graph.add_event(ev)

        # Build feature sequence of length seq_len
        hist = graph.get_entity_events(ev.source_account, as_of=ev.timestamp, limit=seq_len)
        vectors = []
        for h in hist:
            f = engineer.compute_features(ev.source_account, as_of_timestamp=h.timestamp, current_event=h)
            vectors.append(f.to_feature_vector())

        while len(vectors) < seq_len:
            vectors.insert(0, [0.0] * 12)

        records.append({
            "transaction_id": ev.transaction_id,
            "entity_id": ev.source_account,
            "timestamp": ev.timestamp,
            "sequence": vectors[-seq_len:],
            "label": 1 if ev.is_fraud else 0,
        })

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic temporal transaction stream.")
    parser.add_argument("--events", type=int, default=500, help="Total events to generate")
    parser.add_argument("--output", type=str, default="examples/temporal_events.jsonl", help="Output JSONL path")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.events} synthetic temporal events...")
    events = generate_synthetic_temporal_events(num_events=args.events)

    with open(out_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    print(f"Saved {len(events)} events to {out_path.resolve()}")

    # Also generate examples/training_record.jsonl
    training_path = out_path.parent / "training_record.jsonl"
    print(f"Constructing chronological training sequences -> {training_path}...")
    training_records = generate_training_records(events)

    with open(training_path, "w", encoding="utf-8") as f:
        for rec in training_records:
            f.write(json.dumps(rec) + "\n")

    print(f"Saved {len(training_records)} training records to {training_path.resolve()}\n")


if __name__ == "__main__":
    main()
