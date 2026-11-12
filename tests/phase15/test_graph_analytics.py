"""Unit and Integration Tests for Phase 15 Enterprise Graph Analytics & Fraud Ring Detection."""

import os
import sys
from pathlib import Path

os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient

from api.app import app
from graph.fraud_graph_engine import FraudGraphEngine
from graph.graph_store import GraphStore, graph_store
from graph.models import (
    CentralityMetrics,
    CyclePath,
    EdgeType,
    EntityGraphScore,
    FraudRing,
    GraphEdge,
    GraphNode,
    NodeType,
    RingRiskLevel,
    SubgraphExport,
)
from graph.neptune_queries import NeptuneQueryCatalog
from security.auth import create_test_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def clean_engine():
    """Provides a fresh isolated instance of FraudGraphEngine."""
    engine = FraudGraphEngine()
    return engine


# ========================================================
# 1. Models & Validation Tests
# ========================================================
def test_models_and_enums():
    """Validates domain models, serialization, and enum values."""
    node = GraphNode(
        id="CUS-TEST-01",
        type=NodeType.CUSTOMER,
        label="Test Customer",
        risk_score=0.75,
        properties={"kyc_tier": "TIER_2"},
    )
    assert node.id == "CUS-TEST-01"
    assert node.type == NodeType.CUSTOMER
    assert node.risk_score == 0.75

    edge = GraphEdge(
        source="CUS-TEST-01",
        target="ACC-TEST-01",
        type=EdgeType.OWNS_ACCOUNT,
        weight=1.0,
    )
    assert edge.source == "CUS-TEST-01"
    assert edge.target == "ACC-TEST-01"
    assert edge.type == EdgeType.OWNS_ACCOUNT

    ring = FraudRing(
        ring_id="RING-999",
        ring_name="Test Ring",
        risk_level=RingRiskLevel.CRITICAL,
        risk_score=0.95,
        member_customers=["CUS-1", "CUS-2"],
        member_accounts=["ACC-1", "ACC-2"],
        shared_devices=["DEV-1"],
    )
    assert ring.risk_level == RingRiskLevel.CRITICAL
    assert len(ring.member_customers) == 2


# ========================================================
# 2. Engine Ingestion & Reset Tests
# ========================================================
def test_engine_ingest_and_clear(clean_engine):
    """Verifies node and edge ingestion, graph mirroring, and clearing."""
    n1 = GraphNode(id="ACC-A", type=NodeType.ACCOUNT, label="Account A")
    n2 = GraphNode(id="ACC-B", type=NodeType.ACCOUNT, label="Account B")
    e1 = GraphEdge(source="ACC-A", target="ACC-B", type=EdgeType.TRANSFERRED_TO, weight=5000.0)

    clean_engine.ingest_batch([n1, n2], [e1])
    assert clean_engine.g_full.number_of_nodes() == 2
    assert clean_engine.g_full.number_of_edges() == 1
    assert clean_engine.g_transfers.number_of_nodes() == 2
    assert clean_engine.g_transfers.number_of_edges() == 1

    clean_engine.clear()
    assert clean_engine.g_full.number_of_nodes() == 0
    assert clean_engine.g_transfers.number_of_nodes() == 0


# ========================================================
# 3. Fraud Ring Detection Tests (Syndicate-Apex)
# ========================================================
def test_fraud_ring_detection():
    """Verifies detection of multi-identity syndicate sharing devices, IPs, and phones."""
    store = GraphStore(seed=True)
    rings = store.engine.detect_fraud_rings()

    assert len(rings) >= 1
    apex_ring = next((r for r in rings if "DEV-APEX-99" in r.shared_devices), None)
    assert apex_ring is not None
    assert apex_ring.risk_level == RingRiskLevel.CRITICAL
    assert apex_ring.risk_score >= 0.80
    assert "CUS-801" in apex_ring.member_customers
    assert "CUS-802" in apex_ring.member_customers
    assert "ACC-801" in apex_ring.member_accounts
    assert "DEV-APEX-99" in apex_ring.shared_devices
    assert "IP-198.51.100.42" in apex_ring.shared_ips
    assert "PH-88001" in apex_ring.shared_phones
    assert apex_ring.total_flow_amount > 0
    assert "SYNTHETIC_IDENTITY_DEVICE_SHARING" in apex_ring.detected_patterns


# ========================================================
# 4. Circular Transfer & Wash Trading Cycle Detection Tests
# ========================================================
def test_cycle_detection():
    """Verifies detection of circular fund transfers (A -> B -> C -> A)."""
    store = GraphStore(seed=True)
    cycles = store.engine.detect_cycles()

    assert len(cycles) >= 1
    mule_cycle = next((c for c in cycles if "ACC-701" in c.nodes), None)
    assert mule_cycle is not None
    assert mule_cycle.length == 3
    assert set(mule_cycle.nodes) == {"ACC-701", "ACC-702", "ACC-703"}
    assert mule_cycle.total_amount > 150000.0


# ========================================================
# 5. Mule Fan-In & Smurfing Detection Tests
# ========================================================
def test_mule_fan_in_detection():
    """Verifies smurfing fan-in node identification and risk evaluation."""
    store = GraphStore(seed=True)
    eval_score = store.engine.calculate_entity_risk("ACC-600")

    assert eval_score.entity_id == "ACC-600"
    assert eval_score.risk_level in (RingRiskLevel.HIGH, RingRiskLevel.CRITICAL)
    assert eval_score.graph_risk_score >= 0.70
    assert eval_score.centrality.in_degree >= 5
    assert any("fan-in" in rf.lower() for rf in eval_score.risk_factors)


# ========================================================
# 6. Legitimate Baseline Account Scoring Test
# ========================================================
def test_legitimate_entity_scoring():
    """Verifies clean baseline customer/account receives LOW risk score with no rings or cycles."""
    store = GraphStore(seed=True)
    eval_score = store.engine.calculate_entity_risk("ACC-100045")

    assert eval_score.entity_id == "ACC-100045"
    assert eval_score.risk_level == RingRiskLevel.LOW
    assert eval_score.graph_risk_score <= 0.15
    assert eval_score.ring_membership is None
    assert len(eval_score.participating_cycles) == 0


# ========================================================
# 7. Subgraph Ego-Network Extraction Test
# ========================================================
def test_subgraph_ego_extraction():
    """Verifies extraction of k-hop ego-network around device node."""
    store = GraphStore(seed=True)
    subgraph = store.engine.extract_subgraph("DEV-APEX-99", radius=2)

    assert isinstance(subgraph, SubgraphExport)
    assert subgraph.center_node == "DEV-APEX-99"
    assert subgraph.depth_hops == 2
    assert subgraph.node_count >= 5
    assert subgraph.edge_count >= 4
    # Center node must be present
    assert any(n.id == "DEV-APEX-99" for n in subgraph.nodes)


# ========================================================
# 8. Neptune Query Catalog Test
# ========================================================
def test_neptune_query_catalog():
    """Verifies Gremlin and openCypher queries are properly constructed."""
    gremlin = NeptuneQueryCatalog.get_gremlin_queries()
    opencypher = NeptuneQueryCatalog.get_opencypher_queries()

    assert "shared_device_syndicates" in gremlin
    assert "three_hop_cycle_detection" in gremlin
    assert "g.V()" in gremlin["shared_device_syndicates"]

    assert "shared_device_syndicates" in opencypher
    assert "circular_fund_flow_3hop" in opencypher
    assert "MATCH" in opencypher["circular_fund_flow_3hop"]


# ========================================================
# 9. FastAPI Graph Endpoints (Authorized) Tests
# ========================================================
def test_api_graph_endpoints_authorized(client):
    """Verifies authenticated access to graph analytics endpoints."""
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /graph/rings
    resp_rings = client.get("/graph/rings", headers=headers)
    assert resp_rings.status_code == 200
    rings = resp_rings.json()
    assert isinstance(rings, list)
    assert len(rings) >= 1
    assert rings[0]["risk_level"] == "CRITICAL"

    # 2. GET /graph/rings/{ring_id}
    ring_id = rings[0]["ring_id"]
    resp_single_ring = client.get(f"/graph/rings/{ring_id}", headers=headers)
    assert resp_single_ring.status_code == 200
    assert resp_single_ring.json()["ring_id"] == ring_id

    # 3. GET /graph/cycles
    resp_cycles = client.get("/graph/cycles", headers=headers)
    assert resp_cycles.status_code == 200
    cycles = resp_cycles.json()
    assert isinstance(cycles, list)
    assert len(cycles) >= 1

    # 4. GET /graph/risk/{entity_id}
    resp_risk = client.get("/graph/risk/ACC-801", headers=headers)
    assert resp_risk.status_code == 200
    risk_data = resp_risk.json()
    assert risk_data["entity_id"] == "ACC-801"
    assert risk_data["graph_risk_score"] >= 0.80

    # 5. GET /graph/entity/{entity_id}/subgraph
    resp_sub = client.get("/graph/entity/DEV-APEX-99/subgraph?radius=2", headers=headers)
    assert resp_sub.status_code == 200
    sub_data = resp_sub.json()
    assert sub_data["center_node"] == "DEV-APEX-99"
    assert "nodes" in sub_data
    assert "links" in sub_data

    # 6. GET /graph/neptune/queries
    resp_queries = client.get("/graph/neptune/queries", headers=headers)
    assert resp_queries.status_code == 200
    q_data = resp_queries.json()
    assert "gremlin" in q_data
    assert "opencypher" in q_data


# ========================================================
# 10. FastAPI Graph Endpoints (Unauthorized / Forbidden) Tests
# ========================================================
def test_api_graph_endpoints_unauthorized(client):
    """Verifies unauthenticated requests are rejected with 401."""
    resp = client.get("/graph/rings")
    assert resp.status_code == 401

    resp_risk = client.get("/graph/risk/ACC-801")
    assert resp_risk.status_code == 401


# ========================================================
# 11. Dynamic Data Ingestion Endpoint Test
# ========================================================
def test_api_graph_ingest_endpoint(client):
    """Verifies dynamic ingestion of new entities and relationships via API."""
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "nodes": [
            {
                "id": "CUS-NEW-101",
                "type": "CUSTOMER",
                "label": "Dynamic Customer",
                "risk_score": 0.5,
                "properties": {},
            },
            {
                "id": "ACC-NEW-101",
                "type": "ACCOUNT",
                "label": "Dynamic Account",
                "risk_score": 0.5,
                "properties": {},
            },
        ],
        "edges": [
            {
                "source": "CUS-NEW-101",
                "target": "ACC-NEW-101",
                "type": "OWNS_ACCOUNT",
                "weight": 1.0,
                "properties": {},
            }
        ],
    }

    resp = client.post("/graph/ingest", json=payload, headers=headers)
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["nodes_ingested"] == 2
    assert res_data["edges_ingested"] == 1
