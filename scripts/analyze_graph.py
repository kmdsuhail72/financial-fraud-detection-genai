"""Phase 17 — Graph Algorithms Execution & Predictive Fraud Analytics CLI.

Usage:
    python scripts/analyze_graph.py --input data/phase17_graph_scenario.json --output artifacts/phase17
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph.advanced_analytics import AdvancedNetworkAnalytics
from graph.graph_store import GraphStore
from graph.models import (
    GraphEdge,
    GraphNode,
    NodeType,
    PathAnalysisRequest,
)
from graph.neptune_client import NeptuneGremlinClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute Louvain, PageRank, Centrality, and Predictive Risk.")
    parser.add_argument("--input", type=str, default="data/phase17_graph_scenario.json", help="Input scenario JSON")
    parser.add_argument("--output", type=str, default="artifacts/phase17", help="Output directory")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading scenario from {in_path}...")
    with open(in_path, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    # Initialize graph store and neptune client
    store = GraphStore(seed=False)
    neptune = NeptuneGremlinClient(force_local=True)

    # Ingest entities
    nodes = [GraphNode(**n) for n in scenario["nodes"]]
    edges = [GraphEdge(**e) for e in scenario["edges"]]
    store.engine.ingest_batch(nodes=nodes, edges=edges)

    for n in nodes:
        neptune.upsert_vertex(n.id, n.type.value, n.properties, n.type)
    for e in edges:
        neptune.upsert_edge(e.source, e.target, e.type, e.weight, e.properties)

    analytics = AdvancedNetworkAnalytics(store=store, neptune=neptune)

    # 1. Community Detection
    print("Executing Louvain Community Detection...")
    communities = analytics.detect_communities()
    print(f"Discovered {len(communities)} communities.")

    # 2. PageRank
    print("Calculating PageRank Authority Scores...")
    pr_scores = analytics.calculate_pagerank()

    # 3. Path Analysis
    print("Executing Shortest Path Analysis between syndicate account and merchant...")
    path_req = PathAnalysisRequest(source_id="ACC-P17-01", target_id="MER-P17-01", max_depth=5)
    path_res = analytics.find_shortest_path(path_req)

    # 4. Predictive Network Risk across all accounts
    print("Generating Predictive Network Risk Indices...")
    predictive_risks = []
    for n in nodes:
        if n.type in (NodeType.CUSTOMER, NodeType.ACCOUNT):
            p_risk = analytics.predict_entity_risk(n.id)
            predictive_risks.append(p_risk.model_dump(mode="json"))

    # Write JSON report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_scenario": str(in_path),
        "total_entities": len(nodes),
        "total_relationships": len(edges),
        "communities": [c.model_dump(mode="json") for c in communities],
        "top_pagerank": sorted(
            [{"entity_id": k, "pagerank": v} for k, v in pr_scores.items()],
            key=lambda x: x["pagerank"],
            reverse=True,
        )[:10],
        "sample_path_analysis": path_res.model_dump(mode="json"),
        "predictive_risks": predictive_risks,
    }

    report_path = out_dir / "graph_analysis_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Write Markdown Summary
    summary_md = f"""# FinGuard AI — Phase 17 Advanced Graph Analytics Report

- **Executed Timestamp:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **Total Entities Evaluated:** {len(nodes)}
- **Total Relationships Evaluated:** {len(edges)}
- **Topological Communities Detected:** {len(communities)}

## 1. Top Communities by Risk Score

| Community ID | Members Count | Density | Risk Score | Risk Classification | Suspicious Flags |
|---|---|---|---|---|---|
"""
    for c in communities[:5]:
        flags_str = ", ".join(c.suspicious_indicators) if c.suspicious_indicators else "Nominal"
        summary_md += f"| `{c.community_id}` | {c.size} | {c.density:.3f} | `{c.risk_score:.2f}` | **{c.risk_level.value}** | {flags_str} |\n"

    summary_md += """
## 2. Top PageRank Authority Prominence

| Entity ID | PageRank Score |
|---|---|
"""
    for item in report["top_pagerank"][:5]:
        summary_md += f"| `{item['entity_id']}` | `{item['pagerank']:.5f}` |\n"

    summary_md += f"""
## 3. Shortest Path Routing Analysis
- **Route:** `{path_res.source_id}` $\\rightarrow$ `{path_res.target_id}`
- **Path Exists:** `{path_res.path_exists}`
- **Hops:** `{path_res.shortest_path_hops}`
- **Path Sequence:** `{' -> '.join(path_res.path_nodes)}`

## 4. Investigative Note
> [!NOTE]
> All graph risk scores and predictive ratings are **heuristic indicators** intended to guide human investigators during fraud triage. Autonomous adverse actions (e.g. account blocking) are never executed without investigator verification.
"""

    summary_path = out_dir / "summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"\nAnalysis Complete!")
    print(f"Report saved to: {report_path.resolve()}")
    print(f"Summary saved to: {summary_path.resolve()}")


if __name__ == "__main__":
    main()
