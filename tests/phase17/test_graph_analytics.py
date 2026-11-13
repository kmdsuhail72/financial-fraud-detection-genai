"""Unit and Integration Tests for Phase 17 Advanced Fraud Intelligence & Predictive Network Analytics.

Validates:
1. Planted benchmark scenario generator (38 entities, 33 relationships).
2. Louvain community detection with topological fallback.
3. Suspicious community risk scoring and indicator flags.
4. Degree, In/Out-degree, and Betweenness centrality calculation.
5. PageRank authority flow scores and rankings.
6. Shortest relationship path routing (connected vs disconnected).
7. Predictive network risk scoring index & advisory recommendation.
8. FastAPI REST endpoints for communities, centrality, and PageRank.
9. FastAPI REST endpoints for path analysis, predictive risk, and algorithms runner.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from api.app import app
from graph.advanced_analytics import AdvancedNetworkAnalytics
from graph.graph_store import GraphStore
from graph.models import (
    CommunityCluster,
    GraphEdge,
    GraphNode,
    PathAnalysisRequest,
    PathAnalysisResponse,
    PredictiveNetworkRisk,
    RingRiskLevel,
)
from graph.neptune_client import NeptuneGremlinClient
from scripts.generate_graph import generate_benchmark_graph
from security.auth import create_test_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def populated_analytics():
    """Provides an isolated AdvancedNetworkAnalytics instance loaded with 38 nodes & 33 edges."""
    data = generate_benchmark_graph()
    store = GraphStore(seed=False)
    neptune = NeptuneGremlinClient(force_local=True)

    nodes = [GraphNode(**n) for n in data["nodes"]]
    edges = [GraphEdge(**e) for e in data["edges"]]

    store.engine.ingest_batch(nodes=nodes, edges=edges)
    for n in nodes:
        neptune.upsert_vertex(n.id, n.type.value, n.properties, n.type)
    for e in edges:
        neptune.upsert_edge(e.source, e.target, e.type, e.weight, e.properties)

    return AdvancedNetworkAnalytics(store=store, neptune=neptune)


# =============================================================================
# 1. Benchmark Graph Generation Test
# =============================================================================
def test_planted_graph_generation():
    """Verifies generation of exactly 38 synthetic entities and 33 relationships with planted rings."""
    graph_data = generate_benchmark_graph()
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    assert len(nodes) == 38, f"Expected 38 entities, got {len(nodes)}"
    assert len(edges) == 33, f"Expected 33 relationships, got {len(edges)}"

    # Node type counts breakdown
    type_counts = {}
    for n in nodes:
        type_counts[n["type"]] = type_counts.get(n["type"], 0) + 1

    assert type_counts.get("CUSTOMER") == 10
    assert type_counts.get("ACCOUNT") == 15
    assert type_counts.get("DEVICE") == 6
    assert type_counts.get("IP_ADDRESS") == 4
    assert type_counts.get("MERCHANT") == 3

    # Verify planted shared device DEV-P17-01
    dev_edges = [e for e in edges if e["target"] == "DEV-P17-01"]
    assert len(dev_edges) == 3, "DEV-P17-01 must be linked to 3 accounts (device farm)"

    # Verify circular wash transfer loop
    loop_edges = [
        (e["source"], e["target"])
        for e in edges
        if e["type"] == "TRANSFERRED_TO" and "ACC-P17-0" in e["source"] and "ACC-P17-0" in e["target"]
    ]
    assert ("ACC-P17-01", "ACC-P17-02") in loop_edges
    assert ("ACC-P17-02", "ACC-P17-03") in loop_edges
    assert ("ACC-P17-03", "ACC-P17-01") in loop_edges


# =============================================================================
# 2. Louvain Community Detection Test
# =============================================================================
def test_louvain_community_detection(populated_analytics):
    """Verifies Louvain community detection executes successfully and returns valid clusters."""
    communities = populated_analytics.detect_communities()
    assert isinstance(communities, list)
    assert len(communities) >= 1

    total_clustered_entities = sum(c.size for c in communities)
    assert total_clustered_entities == 38, "All 38 nodes must belong to a detected community"

    for comm in communities:
        assert isinstance(comm, CommunityCluster)
        assert comm.community_id.startswith("COMM-")
        assert comm.size > 0
        assert 0.0 <= comm.density <= 1.0
        assert 0.0 <= comm.risk_score <= 1.0
        assert isinstance(comm.risk_level, RingRiskLevel)


# =============================================================================
# 3. Suspicious Community Risk Scoring Test
# =============================================================================
def test_suspicious_community_risk_scoring(populated_analytics):
    """Verifies suspicious indicator extraction and elevated risk scoring for syndicate clusters."""
    communities = populated_analytics.detect_communities()
    critical_or_high = [c for c in communities if c.risk_level in (RingRiskLevel.CRITICAL, RingRiskLevel.HIGH)]
    assert len(critical_or_high) >= 1, "Planted fraud ring should trigger HIGH or CRITICAL community risk"

    top_community = communities[0]
    assert top_community.risk_score >= 0.50
    # Planted syndicate should exhibit shared device or circular transfer indicators
    assert top_community.has_shared_device or top_community.has_circular_loop or top_community.has_shared_ip
    assert len(top_community.suspicious_indicators) >= 1


# =============================================================================
# 4. Centrality Metrics Test
# =============================================================================
def test_centrality_metrics(populated_analytics):
    """Verifies point-in-time degree, in/out-degree, and betweenness centrality calculations."""
    # Test high-traffic node in the syndicate
    metrics = populated_analytics.calculate_centrality("ACC-P17-01")
    assert "degree_centrality" in metrics
    assert "in_degree_centrality" in metrics
    assert "out_degree_centrality" in metrics
    assert "betweenness_centrality" in metrics
    assert "clustering_coefficient" in metrics

    assert metrics["degree_centrality"] > 0.0
    assert metrics["out_degree_centrality"] > 0.0
    assert 0.0 <= metrics["betweenness_centrality"] <= 1.0

    # Non-existent node handles gracefully with 0.0 values
    empty_metrics = populated_analytics.calculate_centrality("UNKNOWN-ENTITY-999")
    assert empty_metrics["degree_centrality"] == 0.0
    assert empty_metrics["betweenness_centrality"] == 0.0


# =============================================================================
# 5. PageRank Authority Flow Test
# =============================================================================
def test_pagerank_authority_flow(populated_analytics):
    """Verifies PageRank algorithm ranks entities by authority flow with normalized sum."""
    pr_scores = populated_analytics.calculate_pagerank()
    assert isinstance(pr_scores, dict)
    assert len(pr_scores) == 38

    # Check sum of PageRank scores is close to 1.0
    total_pr = sum(pr_scores.values())
    assert 0.90 <= total_pr <= 1.10, f"Expected total PageRank ~1.0, got {total_pr}"

    # Verify high-inflow account or merchant receives positive score
    assert pr_scores.get("ACC-P17-01", 0.0) > 0.0
    assert pr_scores.get("MER-P17-01", 0.0) > 0.0


# =============================================================================
# 6. Shortest Path Routing Analysis Test
# =============================================================================
def test_shortest_path_routing(populated_analytics):
    """Verifies transaction and relationship routing traversal between entities."""
    # Connected entities in the graph (ACC-01 to MER-01)
    req_connected = PathAnalysisRequest(
        source_id="ACC-P17-01",
        target_id="MER-P17-01",
        max_depth=5,
    )
    res_connected = populated_analytics.find_shortest_path(req_connected)

    assert isinstance(res_connected, PathAnalysisResponse)
    assert res_connected.path_exists is True
    assert res_connected.shortest_path_hops >= 1
    assert res_connected.path_nodes[0] == "ACC-P17-01"
    assert res_connected.path_nodes[-1] == "MER-P17-01"
    assert len(res_connected.path_relationships) == res_connected.shortest_path_hops

    # Disconnected / non-existent entity
    req_disconnected = PathAnalysisRequest(
        source_id="ACC-P17-01",
        target_id="DISCONNECTED-GHOST-ENTITY",
        max_depth=3,
    )
    res_disconnected = populated_analytics.find_shortest_path(req_disconnected)
    assert res_disconnected.path_exists is False
    assert res_disconnected.shortest_path_hops == 0
    assert len(res_connected.path_nodes) >= 2


# =============================================================================
# 7. Predictive Network Risk Scoring Test
# =============================================================================
def test_predictive_network_risk_scoring(populated_analytics):
    """Verifies advisory predictive risk index calculation fusing community, centrality & PageRank."""
    # Evaluate a syndicate node
    risk_assessment = populated_analytics.predict_entity_risk("ACC-P17-01")
    assert isinstance(risk_assessment, PredictiveNetworkRisk)
    assert risk_assessment.entity_id == "ACC-P17-01"
    assert 0.0 <= risk_assessment.predictive_fraud_risk <= 1.0
    assert risk_assessment.advisory_risk_level in (RingRiskLevel.CRITICAL, RingRiskLevel.HIGH, RingRiskLevel.MEDIUM, RingRiskLevel.LOW)
    assert len(risk_assessment.risk_factors) > 0
    assert "verification" in risk_assessment.recommendation.lower() or "monitor" in risk_assessment.recommendation.lower()

    # Evaluate non-existent node gracefully
    empty_risk = populated_analytics.predict_entity_risk("NON-EXISTENT-ENTITY")
    assert empty_risk.predictive_fraud_risk == 0.05
    assert empty_risk.advisory_risk_level == RingRiskLevel.LOW


# =============================================================================
# 8. REST API Communities, Centrality & PageRank Endpoints Test
# =============================================================================
def test_api_communities_and_centrality(client, auth_headers):
    """Verifies GET /graph/communities, /graph/centrality/{id}, and /graph/pagerank."""
    # Seed default scenario into the server's graph_store
    data = generate_benchmark_graph()
    from graph.graph_store import graph_store
    from graph.neptune_client import get_neptune_client

    nodes = [GraphNode(**n) for n in data["nodes"]]
    edges = [GraphEdge(**e) for e in data["edges"]]
    graph_store.engine.ingest_batch(nodes=nodes, edges=edges)

    neptune = get_neptune_client()
    for n in nodes:
        neptune.upsert_vertex(n.id, n.type.value, n.properties, n.type)
    for e in edges:
        neptune.upsert_edge(e.source, e.target, e.type, e.weight, e.properties)

    # 1. GET /graph/communities
    resp = client.get("/graph/communities", headers=auth_headers)
    assert resp.status_code == 200
    communities = resp.json()
    assert isinstance(communities, list)
    assert len(communities) >= 1

    first_comm_id = communities[0]["community_id"]

    # 2. GET /graph/communities/{id}
    resp_comm = client.get(f"/graph/communities/{first_comm_id}", headers=auth_headers)
    assert resp_comm.status_code == 200
    assert resp_comm.json()["community_id"] == first_comm_id

    # 3. GET /graph/communities/invalid
    resp_invalid = client.get("/graph/communities/COMM-INVALID-99", headers=auth_headers)
    assert resp_invalid.status_code == 404

    # 4. GET /graph/centrality/{id}
    resp_cent = client.get("/graph/centrality/ACC-P17-01", headers=auth_headers)
    assert resp_cent.status_code == 200
    cent_data = resp_cent.json()
    assert "degree_centrality" in cent_data
    assert "betweenness_centrality" in cent_data

    # 5. GET /graph/pagerank
    resp_pr = client.get("/graph/pagerank?limit=10", headers=auth_headers)
    assert resp_pr.status_code == 200
    pr_list = resp_pr.json()
    assert isinstance(pr_list, list)
    assert len(pr_list) <= 10
    assert "entity_id" in pr_list[0]
    assert "pagerank" in pr_list[0]


# =============================================================================
# 9. REST API Paths, Predictive Risk & Algorithm Runner Endpoints Test
# =============================================================================
def test_api_paths_predict_and_run(client, auth_headers):
    """Verifies POST /graph/paths/shortest, /graph/predict-risk, and /graph/algorithms/run."""
    # 1. POST /graph/paths/shortest
    path_payload = {
        "source_id": "ACC-P17-01",
        "target_id": "MER-P17-01",
        "max_depth": 5,
    }
    resp_path = client.post("/graph/paths/shortest", json=path_payload, headers=auth_headers)
    assert resp_path.status_code == 200
    path_data = resp_path.json()
    assert path_data["source_id"] == "ACC-P17-01"
    assert path_data["target_id"] == "MER-P17-01"
    assert path_data["path_exists"] is True

    # 2. POST /graph/predict-risk
    risk_payload = {"entity_id": "ACC-P17-01"}
    resp_risk = client.post("/graph/predict-risk", json=risk_payload, headers=auth_headers)
    assert resp_risk.status_code == 200
    risk_data = resp_risk.json()
    assert risk_data["entity_id"] == "ACC-P17-01"
    assert "predictive_fraud_risk" in risk_data
    assert "recommendation" in risk_data

    # 3. POST /graph/algorithms/run
    resp_run = client.post("/graph/algorithms/run", headers=auth_headers)
    assert resp_run.status_code == 200
    run_data = resp_run.json()
    assert run_data["status"] == "COMPLETED"
    assert "communities_count" in run_data
    assert "top_pagerank_entities" in run_data
