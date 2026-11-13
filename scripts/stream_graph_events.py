"""End-to-End Real-Time Graph Streaming and Risk Enrichment Simulation (Phase 16).

Usage:
    python scripts/stream_graph_events.py --events 250 --output artifacts/phase16/stream_simulation_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph.neptune_client import get_neptune_client
from graph.relationship_sync import RelationshipSyncEngine
from graph.scoring_adapter import GraphRiskEnricher
from graph.models import RiskEnrichmentRequest


def generate_synthetic_stream(count: int = 250) -> List[Dict[str, Any]]:
    """Generates a mixture of nominal transactions and coordinated fraud networks."""
    events = []
    base_time = datetime(2026, 11, 13, 8, 0, 0, tzinfo=timezone.utc)

    # 1. Shared Device Farming Syndicate (5 accounts on 1 emulator device)
    syndicate_customers = [f"CUS-RING1-{i:03d}" for i in range(1, 6)]
    syndicate_accounts = [f"ACC-RING1-{i:03d}" for i in range(1, 6)]
    shared_device = "DEV-ROGUE-EMULATOR-88"
    shared_ip = "198.51.100.77"

    for i in range(5):
        events.append({
            "transaction_id": f"TXN-SYN-{i+1:04d}",
            "customer_id": syndicate_customers[i],
            "source_account_id": syndicate_accounts[i],
            "destination_account_id": f"ACC-TARGET-{100 + i}",
            "amount": 4500.0 + (i * 250.0),
            "currency": "USD",
            "timestamp": (base_time + timedelta(minutes=i * 4)).isoformat(),
            "device_id": shared_device,
            "ip_address": shared_ip,
            "city": "Chicago",
            "is_syndicate": True,
        })

    # 2. Circular Wash Trading Mule Loop (A -> B -> C -> A)
    mule_loop = ["ACC-LOOP-A", "ACC-LOOP-B", "ACC-LOOP-C"]
    for i in range(len(mule_loop)):
        src = mule_loop[i]
        dst = mule_loop[(i + 1) % len(mule_loop)]
        events.append({
            "transaction_id": f"TXN-LOOP-{i+1:04d}",
            "customer_id": f"CUS-MULE-{i+1}",
            "source_account_id": src,
            "destination_account_id": dst,
            "amount": 9800.0,
            "currency": "USD",
            "timestamp": (base_time + timedelta(minutes=30 + i * 5)).isoformat(),
            "device_id": f"dev_loop_phone_{i+1}",
            "ip_address": f"203.0.113.{50 + i}",
            "city": "Dallas",
            "is_circular_loop": True,
        })

    # 3. High Fan-in Mule Consolidation (5 senders to 1 collector)
    mule_target = "ACC-COLLECTOR-999"
    for i in range(5):
        events.append({
            "transaction_id": f"TXN-FANIN-{i+1:04d}",
            "customer_id": f"CUS-SMURF-{i+1}",
            "source_account_id": f"ACC-SMURF-{i+1:03d}",
            "destination_account_id": mule_target,
            "amount": 2950.0,
            "currency": "USD",
            "timestamp": (base_time + timedelta(minutes=60 + i * 2)).isoformat(),
            "device_id": f"dev_smurf_{i+1}",
            "ip_address": "192.0.2.144",
            "city": "New York",
            "is_mule_consolidation": True,
        })

    # 4. Standard Legitimate Baseline Transactions
    remaining = max(10, count - len(events))
    for i in range(remaining):
        events.append({
            "transaction_id": f"TXN-LEGIT-{i+1:05d}",
            "customer_id": f"CUS-LEGIT-{1000 + i}",
            "source_account_id": f"ACC-LEGIT-{2000 + i}",
            "destination_account_id": f"ACC-MERCHANT-{3000 + (i % 10)}",
            "amount": round(25.0 + (i * 7.5), 2),
            "currency": "USD",
            "timestamp": (base_time + timedelta(minutes=90 + i * 3)).isoformat(),
            "device_id": f"dev_phone_legit_{i+1}",
            "ip_address": f"198.51.100.{10 + (i % 80)}",
            "city": "San Francisco",
            "merchant_id": f"MER-STORE-{10 + (i % 5)}",
            "is_legitimate": True,
        })

    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate real-time graph event streaming to Neptune.")
    parser.add_argument("--events", type=int, default=250, help="Number of stream events")
    parser.add_argument("--output", type=str, default="artifacts/phase16/stream_simulation_report.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.events} synthetic streaming transactions...")
    events = generate_synthetic_stream(count=args.events)

    client = get_neptune_client()
    sync_engine = RelationshipSyncEngine(client=client)
    enricher = GraphRiskEnricher(client=client)

    print("Streaming transactions into Neptune Graph Synchronization Engine...")
    sync_results = []
    for ev in events:
        res = sync_engine.sync_transaction_event(ev)
        sync_results.append(res)

    # Test idempotency deduplication by re-streaming first 15 events
    print("Testing duplicate event replay protection...")
    duplicate_results = []
    for ev in events[:15]:
        dup_res = sync_engine.sync_transaction_event(ev)
        duplicate_results.append(dup_res)

    # Run Risk Enrichment across representative transactions
    print("Evaluating Phase 7 Graph Risk Enrichment...")
    enriched_samples = []

    # Syndicate test
    req_syndicate = RiskEnrichmentRequest(
        transaction_id="TXN-TEST-SYNDICATE",
        customer_id="CUS-RING1-001",
        account_id="ACC-RING1-001",
        device_id="DEV-ROGUE-EMULATOR-88",
        ip_address="198.51.100.77",
        amount=4500.0,
    )
    enriched_samples.append(enricher.enrich(req_syndicate).model_dump(mode="json"))

    # Circular loop test
    req_loop = RiskEnrichmentRequest(
        transaction_id="TXN-TEST-LOOP",
        account_id="ACC-LOOP-A",
        amount=9800.0,
    )
    enriched_samples.append(enricher.enrich(req_loop).model_dump(mode="json"))

    # Fan-in mule test
    req_mule = RiskEnrichmentRequest(
        transaction_id="TXN-TEST-MULE",
        account_id="ACC-COLLECTOR-999",
        amount=2950.0,
    )
    enriched_samples.append(enricher.enrich(req_mule).model_dump(mode="json"))

    # Normal transaction test
    req_normal = RiskEnrichmentRequest(
        transaction_id="TXN-TEST-NORMAL",
        customer_id="CUS-LEGIT-1000",
        account_id="ACC-LEGIT-2000",
        device_id="dev_phone_legit_1",
        ip_address="198.51.100.10",
        amount=45.0,
    )
    enriched_samples.append(enricher.enrich(req_normal).model_dump(mode="json"))

    v_count, e_count = client.get_counts()
    shared_devices = client.find_shared_devices()
    cycles = client.find_cycles(max_length=4)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_events_streamed": len(events),
        "duplicate_events_tested": len(duplicate_results),
        "duplicates_properly_skipped": sum(1 for d in duplicate_results if d.get("status") == "DUPLICATE_SKIPPED"),
        "final_graph_state": {
            "vertex_count": v_count,
            "edge_count": e_count,
            "shared_devices_detected": len(shared_devices),
            "circular_transfer_loops_detected": len(cycles),
        },
        "sync_engine_metrics": sync_engine.metrics,
        "sample_risk_enrichments": enriched_samples,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nSimulation Complete!")
    print(f"Graph Vertices: {v_count}, Edges: {e_count}")
    print(f"Shared Devices: {len(shared_devices)}, Circular Loops: {len(cycles)}")
    print(f"Duplicates Skipped: {sync_engine.metrics['duplicates_skipped']}")
    print(f"Report saved to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
