#!/usr/bin/env python3
"""
FinGuard AI — Enterprise Graph Analytics & Fraud Ring Detection CLI Demonstration (Phase 15).

Demonstrates:
1. Automated discovery of synthetic identity clusters and shared infrastructure rings.
2. Circular money mule transfer loop detection (wash trading).
3. Smurfing fan-in node identification and bulk offshore liquidation.
4. Calculation of composite Graph Risk Scores and centrality metrics.
5. Generation of interactive visualization artifacts.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph.graph_store import GraphStore
from graph.neptune_queries import NeptuneQueryCatalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo-fraud-ring")


def run_demo(output_dir: str = "artifacts/phase15"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("================================================================================")
    print("      FinGuard AI — Enterprise Graph Analytics & Fraud Ring Detection           ")
    print("================================================================================")

    store = GraphStore(seed=True)
    engine = store.engine

    print(f"\n[*] Total Graph Vertices : {engine.g_full.number_of_nodes()}")
    print(f"[*] Total Graph Edges    : {engine.g_full.number_of_edges()}")
    print(f"[*] Transfer Graph Nodes : {engine.g_transfers.number_of_nodes()}")
    print(f"[*] Transfer Graph Edges : {engine.g_transfers.number_of_edges()}")

    # 1. Detect Fraud Rings
    print("\n" + "=" * 80)
    print("1. DISCOVERED FRAUD RINGS & COLLUSION SYNDICATES")
    print("=" * 80)
    rings = engine.detect_fraud_rings()
    print(f"Found {len(rings)} distinct fraud ring syndicate(s):\n")

    for r in rings:
        print(f" Ring ID         : {r.ring_id}")
        print(f" Name            : {r.ring_name}")
        print(f" Risk Level      : {r.risk_level.value} (Score: {r.risk_score:.4f})")
        print(f" Member Customers: {', '.join(r.member_customers)}")
        print(f" Member Accounts : {', '.join(r.member_accounts)}")
        print(f" Shared Devices  : {', '.join(r.shared_devices) if r.shared_devices else 'None'}")
        print(f" Shared IPs      : {', '.join(r.shared_ips) if r.shared_ips else 'None'}")
        print(f" Shared Phones   : {', '.join(r.shared_phones) if r.shared_phones else 'None'}")
        print(f" Intra-Ring Flow : INR {r.total_flow_amount:,.2f}")
        print(f" Detected Patterns: {', '.join(r.detected_patterns)}")
        print(f" Action Gate     : {r.recommended_action}")
        print("-" * 80)

    # 2. Detect Circular Fund Flows (Loops)
    print("\n" + "=" * 80)
    print("2. DETECTED CIRCULAR FUND FLOWS (WASH TRADING & MULE LOOPS)")
    print("=" * 80)
    cycles = engine.detect_cycles()
    print(f"Found {len(cycles)} closed transfer loop(s):\n")
    for c in cycles:
        print(f" Cycle ID    : {c.cycle_id}")
        print(f" Path        : {' -> '.join(c.nodes)} -> {c.nodes[0]}")
        print(f" Hop Length  : {c.length}")
        print(f" Cycle Volume: INR {c.total_amount:,.2f}")
        print(f" Summary     : {c.description}")
        print("-" * 80)

    # 3. Entity Risk Evaluations
    print("\n" + "=" * 80)
    print("3. GRAPH RISK EVALUATION & CENTRALITY ON TARGET ACCOUNTS")
    print("=" * 80)
    target_entities = ["ACC-801", "ACC-701", "ACC-600", "ACC-100045"]
    entity_evals = []

    for ent in target_entities:
        eval_score = engine.calculate_entity_risk(ent)
        entity_evals.append(eval_score.model_dump())
        print(f"\nEntity : {eval_score.entity_id} ({eval_score.entity_type.value})")
        print(f"  Graph Risk Score : {eval_score.graph_risk_score:.4f} [{eval_score.risk_level.value}]")
        print(f"  Ring Membership  : {eval_score.ring_membership or 'None'}")
        print(f"  Active Loops     : {', '.join(eval_score.participating_cycles) or 'None'}")
        print(f"  Shared Assets    : {eval_score.shared_entities_count} entities")
        print(f"  PageRank Central : {eval_score.centrality.pagerank:.6f}")
        print(f"  In/Out Degrees   : {eval_score.centrality.in_degree} In, {eval_score.centrality.out_degree} Out")
        print("  Risk Factors     :")
        for rf in eval_score.risk_factors:
            print(f"    - {rf}")

    # 4. Ego Subgraph Export
    subgraph_apex = engine.extract_subgraph("DEV-APEX-99", radius=2)
    subgraph_file = out_path / "subgraph_sample.json"
    with open(subgraph_file, "w", encoding="utf-8") as f:
        json.dump(subgraph_apex.model_dump(), f, indent=2)
    print(f"\n[+] Exported 2-hop ego subgraph around DEV-APEX-99 to: {subgraph_file}")

    # 5. Save Full JSON Report
    report_data = {
        "summary": {
            "total_nodes": engine.g_full.number_of_nodes(),
            "total_edges": engine.g_full.number_of_edges(),
            "total_fraud_rings": len(rings),
            "total_circular_loops": len(cycles),
        },
        "fraud_rings": [r.model_dump() for r in rings],
        "cycles": [c.model_dump() for c in cycles],
        "entity_evaluations": entity_evals,
        "neptune_gremlin_queries": NeptuneQueryCatalog.get_gremlin_queries(),
        "neptune_opencypher_queries": NeptuneQueryCatalog.get_opencypher_queries(),
    }

    report_file = out_path / "fraud_ring_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"[+] Saved structured fraud ring intelligence report to: {report_file}")

    # 6. Save Markdown Summary
    md_file = out_path / "graph_summary.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# FinGuard AI — Enterprise Graph Analytics & Fraud Ring Detection\n\n")
        f.write(f"**Execution Timestamp:** {json.dumps(report_data['summary'], indent=2)}\n\n")
        f.write("## 1. Discovered Fraud Rings\n\n")
        f.write("| Ring ID | Risk Level | Score | Customers | Accounts | Shared Assets | Recommended Action |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for r in rings:
            shared_info = f"Devs: {len(r.shared_devices)}, IPs: {len(r.shared_ips)}, Phones: {len(r.shared_phones)}"
            f.write(f"| **{r.ring_id}** | `{r.risk_level.value}` | `{r.risk_score:.4f}` | {len(r.member_customers)} | {len(r.member_accounts)} | {shared_info} | {r.recommended_action} |\n")

        f.write("\n## 2. Circular Fund Transfer Loops\n\n")
        for c in cycles:
            f.write(f"- **{c.cycle_id}** ({c.length} hops, INR {c.total_amount:,.2f}): `{' -> '.join(c.nodes)} -> {c.nodes[0]}`\n")

        f.write("\n## 3. Account Risk Evaluations\n\n")
        f.write("| Account | Risk Score | Risk Level | Ring Membership | Loops | Risk Summary |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for ev in entity_evals:
            loops_str = ", ".join(ev["participating_cycles"]) or "None"
            f.write(f"| `{ev['entity_id']}` | `{ev['graph_risk_score']:.4f}` | `{ev['risk_level']}` | `{ev['ring_membership'] or 'None'}` | {loops_str} | {ev['risk_factors'][0]} |\n")

    print(f"[+] Saved executive summary markdown to: {md_file}")
    print("\n[OK] Phase 15 Graph Analytics Demonstration completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinGuard AI Graph Analytics CLI")
    parser.add_argument("--output", default="artifacts/phase15", help="Output artifact directory")
    args = parser.parse_args()
    run_demo(args.output)

