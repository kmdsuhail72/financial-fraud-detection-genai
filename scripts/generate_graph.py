"""Phase 17 & Phase 18 — Planted Synthetic Graph Scenario Generator.

Generates:
- Phase 17 benchmark scenario: 38 entities and 33 relationships (data/phase17_graph_scenario.json).
- Phase 18 GNN benchmark scenario: 92 entities and 81 relationships (data/phase18_graph_scenario.json).

Usage:
    python scripts/generate_graph.py
    python scripts/generate_graph.py --phase 18 --output data/phase18_graph_scenario.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gnn.dataset import generate_phase18_graph


def generate_benchmark_graph() -> Dict[str, Any]:
    """
    Phase 17 Planted Scenario:
    Constructs 38 entities and 33 relationships:
    - 10 Customers (CUS-01..10)
    - 15 Accounts (ACC-01..15)
    - 6 Devices (DEV-01..06)
    - 4 IPs (IP-01..04)
    - 3 Merchants (MER-01..03)
    Total = 38 entities, 33 relationships.
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Vertices (38 entities)
    # 10 Customers
    for i in range(1, 11):
        nodes.append({
            "id": f"CUS-P17-{i:02d}",
            "type": "CUSTOMER",
            "label": f"Customer {i}",
            "properties": {"kyc_tier": "Tier-1" if i > 5 else "Tier-2"},
        })

    # 15 Accounts
    for i in range(1, 16):
        nodes.append({
            "id": f"ACC-P17-{i:02d}",
            "type": "ACCOUNT",
            "label": f"Account {i}",
            "properties": {"currency": "USD", "status": "ACTIVE"},
        })

    # 6 Devices
    for i in range(1, 7):
        nodes.append({
            "id": f"DEV-P17-{i:02d}",
            "type": "DEVICE",
            "label": "Rogue Device Emulator" if i == 1 else f"Mobile Device {i}",
            "properties": {"is_emulator": i == 1},
        })

    # 4 IP Addresses
    for i in range(1, 5):
        nodes.append({
            "id": f"IP-P17-{i:02d}",
            "type": "IP_ADDRESS",
            "label": f"198.51.100.{10 * i}",
            "properties": {"asn": f"AS-{50000 + i}"},
        })

    # 3 Merchants
    for i in range(1, 4):
        nodes.append({
            "id": f"MER-P17-{i:02d}",
            "type": "MERCHANT",
            "label": f"Merchant Store {i}",
            "properties": {"category": "Crypto" if i == 1 else "Retail"},
        })

    assert len(nodes) == 38, f"Expected 38 nodes, got {len(nodes)}"

    # 2. Edges (33 relationships)
    # 10 OWNS_ACCOUNT
    for i in range(1, 11):
        edges.append({
            "source": f"CUS-P17-{i:02d}",
            "target": f"ACC-P17-{i:02d}",
            "type": "OWNS_ACCOUNT",
            "weight": 1.0,
            "properties": {"since": "2026-01-01"},
        })

    # 7 USES_DEVICE (DEV-01 is shared across ACC-01, ACC-02, ACC-03 -> Device Farm Syndicate)
    edges.append({"source": "ACC-P17-01", "target": "DEV-P17-01", "type": "USES_DEVICE", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-02", "target": "DEV-P17-01", "type": "USES_DEVICE", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-03", "target": "DEV-P17-01", "type": "USES_DEVICE", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-04", "target": "DEV-P17-02", "type": "USES_DEVICE", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-05", "target": "DEV-P17-03", "type": "USES_DEVICE", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-06", "target": "DEV-P17-04", "type": "USES_DEVICE", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-07", "target": "DEV-P17-05", "type": "USES_DEVICE", "weight": 1.0, "properties": {}})

    # 5 ASSOCIATED_IP (IP-01 shared across ACC-01, ACC-02)
    edges.append({"source": "ACC-P17-01", "target": "IP-P17-01", "type": "ASSOCIATED_IP", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-02", "target": "IP-P17-01", "type": "ASSOCIATED_IP", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-08", "target": "IP-P17-02", "type": "ASSOCIATED_IP", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-09", "target": "IP-P17-03", "type": "ASSOCIATED_IP", "weight": 1.0, "properties": {}})
    edges.append({"source": "ACC-P17-10", "target": "IP-P17-04", "type": "ASSOCIATED_IP", "weight": 1.0, "properties": {}})

    # 8 TRANSFERRED_TO (Planted Circular Loop: ACC-01 -> ACC-02 -> ACC-03 -> ACC-01, plus chain transfers)
    edges.append({"source": "ACC-P17-01", "target": "ACC-P17-02", "type": "TRANSFERRED_TO", "weight": 7500.0, "properties": {"amount": 7500}})
    edges.append({"source": "ACC-P17-02", "target": "ACC-P17-03", "type": "TRANSFERRED_TO", "weight": 7400.0, "properties": {"amount": 7400}})
    edges.append({"source": "ACC-P17-03", "target": "ACC-P17-01", "type": "TRANSFERRED_TO", "weight": 7350.0, "properties": {"amount": 7350}})
    edges.append({"source": "ACC-P17-04", "target": "ACC-P17-05", "type": "TRANSFERRED_TO", "weight": 1200.0, "properties": {"amount": 1200}})
    edges.append({"source": "ACC-P17-05", "target": "ACC-P17-06", "type": "TRANSFERRED_TO", "weight": 1150.0, "properties": {"amount": 1150}})
    edges.append({"source": "ACC-P17-07", "target": "ACC-P17-11", "type": "TRANSFERRED_TO", "weight": 2100.0, "properties": {"amount": 2100}})
    edges.append({"source": "ACC-P17-08", "target": "ACC-P17-12", "type": "TRANSFERRED_TO", "weight": 3400.0, "properties": {"amount": 3400}})
    edges.append({"source": "ACC-P17-09", "target": "ACC-P17-13", "type": "TRANSFERRED_TO", "weight": 890.0, "properties": {"amount": 890}})

    # 3 PAID_MERCHANT
    edges.append({"source": "ACC-P17-03", "target": "MER-P17-01", "type": "PAID_MERCHANT", "weight": 5000.0, "properties": {"amount": 5000}})
    edges.append({"source": "ACC-P17-04", "target": "MER-P17-02", "type": "PAID_MERCHANT", "weight": 120.0, "properties": {"amount": 120}})
    edges.append({"source": "ACC-P17-05", "target": "MER-P17-03", "type": "PAID_MERCHANT", "weight": 85.0, "properties": {"amount": 85}})

    assert len(edges) == 33, f"Expected 33 edges, got {len(edges)}"

    return {
        "metadata": {
            "scenario": "Phase-17-Planted-Fraud-Ring",
            "entity_count": len(nodes),
            "relationship_count": len(edges),
            "planted_rings": ["DEV-P17-01 Device Farm", "ACC-P17-01/02/03 Circular Wash Loop"],
        },
        "nodes": nodes,
        "edges": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic benchmark graphs for FinGuard AI.")
    parser.add_argument("--phase", type=int, default=18, choices=[17, 18], help="Target phase benchmark (17 or 18)")
    parser.add_argument("--output", type=str, default=None, help="Explicit output path")
    args = parser.parse_args()

    # Always generate Phase 17 data
    p17_path = Path("data/phase17_graph_scenario.json")
    p17_path.parent.mkdir(parents=True, exist_ok=True)
    p17_data = generate_benchmark_graph()
    with open(p17_path, "w", encoding="utf-8") as f:
        json.dump(p17_data, f, indent=2)

    # Always generate Phase 18 data
    p18_path = Path("data/phase18_graph_scenario.json")
    p18_path.parent.mkdir(parents=True, exist_ok=True)
    p18_data = generate_phase18_graph()
    with open(p18_path, "w", encoding="utf-8") as f:
        json.dump(p18_data, f, indent=2)

    if args.output:
        custom_path = Path(args.output)
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        chosen_data = p18_data if args.phase == 18 else p17_data
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump(chosen_data, f, indent=2)
        print(f"Saved Phase {args.phase} scenario to {custom_path.resolve()}")

    print(f"Generated Phase 17 Planted Scenario: {len(p17_data['nodes'])} entities, {len(p17_data['edges'])} relationships -> {p17_path}")
    print(f"Generated Phase 18 GNN Scenario: {len(p18_data['nodes'])} entities, {len(p18_data['edges'])} relationships -> {p18_path}")


if __name__ == "__main__":
    main()
