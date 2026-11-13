"""Unit and Integration Tests for Phase 16 Enterprise Neptune Graph & Real-Time Streaming."""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Prevent AWS metadata queries during testing
os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

from api.app import app
from graph.gremlin_library import GremlinQueryLibrary
from graph.models import (
    EdgeType,
    NodeType,
    RingRiskLevel,
    RiskEnrichmentRequest,
)
from graph.neptune_client import NeptuneGremlinClient
from graph.relationship_sync import RelationshipSyncEngine
from graph.scoring_adapter import GraphRiskEnricher
from lambda_graph_sync.handler import lambda_handler
from security.auth import create_test_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_test_token(
        sub="investigator-1",
        email="investigator@finguard.internal",
        roles=["Investigator", "Analyst"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def isolated_neptune():
    """Provides a fresh isolated NeptuneGremlinClient for test assertions."""
    return NeptuneGremlinClient(force_local=True)


# 1. Neptune Client Initialization & Health
def test_neptune_client_initialization_and_health(isolated_neptune):
    health = isolated_neptune.health()
    assert health.status == "HEALTHY"
    assert "EMULATED_STANDALONE" in health.mode
    assert health.vertex_count == 0
    assert health.edge_count == 0


# 2. Vertex & Edge Upsert
def test_vertex_and_edge_upsert(isolated_neptune):
    # Upsert Vertex
    v1 = isolated_neptune.upsert_vertex("CUS-999", "Customer", {"kyc_level": "Tier-2"})
    assert v1.id == "CUS-999"
    assert v1.type == NodeType.CUSTOMER
    assert v1.properties["kyc_level"] == "Tier-2"

    v2 = isolated_neptune.upsert_vertex("ACC-999", "Account", {"currency": "USD"})
    assert v2.id == "ACC-999"

    # Upsert Edge
    e = isolated_neptune.upsert_edge("CUS-999", "ACC-999", EdgeType.OWNS_ACCOUNT, weight=1.0)
    assert e.source == "CUS-999"
    assert e.target == "ACC-999"
    assert e.type == EdgeType.OWNS_ACCOUNT

    v_count, e_count = isolated_neptune.get_counts()
    assert v_count == 2
    assert e_count == 1


# 3. Gremlin Query Library Parametric Generation
def test_gremlin_query_library_generation():
    lib = GremlinQueryLibrary()

    v_q = lib.add_vertex("Customer", "CUS-101", {"status": "ACTIVE", "score": 95.5})
    assert "g.V('CUS-101')" in v_q
    assert "addV('Customer')" in v_q
    assert ".property('status', 'ACTIVE')" in v_q
    assert ".property('score', 95.5)" in v_q

    e_q = lib.add_edge("CUS-101", "ACC-202", "OWNS_ACCOUNT", weight=2.5)
    assert "g.V('CUS-101').as('src')" in e_q
    assert "addE('OWNS_ACCOUNT')" in e_q

    shared_dev_q = lib.shared_devices()
    assert "hasLabel('Customer')" in shared_dev_q
    assert "USES_DEVICE" in shared_dev_q


# 4. Relationship Sync & Idempotency Protection
def test_relationship_sync_and_idempotency(isolated_neptune):
    sync_engine = RelationshipSyncEngine(client=isolated_neptune)

    event = {
        "transaction_id": "TXN-TEST-SYNC-1",
        "customer_id": "CUS-301",
        "source_account_id": "ACC-301",
        "destination_account_id": "ACC-302",
        "amount": 1500.0,
        "currency": "USD",
        "timestamp": "2026-11-13T10:00:00Z",
        "device_id": "dev_test_phone",
        "ip_address": "198.51.100.33",
    }

    # Initial Sync
    res1 = sync_engine.sync_transaction_event(event)
    assert res1["status"] == "SYNCHRONIZED"
    assert res1["vertices_upserted"] >= 4  # Customer, Acc1, Acc2, Device, IP
    assert res1["edges_upserted"] >= 3

    # Duplicate Replay Sync
    res2 = sync_engine.sync_transaction_event(event)
    assert res2["status"] == "DUPLICATE_SKIPPED"
    assert sync_engine.metrics["duplicates_skipped"] == 1


# 5. Lambda Kinesis Batch Processor
def test_lambda_kinesis_handler_batch_processing(isolated_neptune):
    # Patch global engine to use test neptune client
    from lambda_graph_sync import handler
    handler.SYNC_ENGINE = RelationshipSyncEngine(client=isolated_neptune)

    event_payload = {
        "transaction_id": "TXN-KINESIS-001",
        "customer_id": "CUS-KIN-1",
        "source_account_id": "ACC-KIN-1",
        "destination_account_id": "ACC-KIN-2",
        "amount": 500.0,
        "device_id": "dev_kinesis_1",
    }
    encoded_data = base64.b64encode(json.dumps(event_payload).encode("utf-8")).decode("utf-8")

    kinesis_event = {
        "Records": [
            {
                "kinesis": {
                    "sequenceNumber": "seq-1001",
                    "data": encoded_data,
                }
            }
        ]
    }

    resp = lambda_handler(kinesis_event, None)
    assert resp["statusCode"] == 200
    assert resp["stats"]["processed"] == 1
    assert len(resp["batchItemFailures"]) == 0


# 6. Shared Infrastructure and Circular Loop Detection
def test_shared_infrastructure_and_loop_detection(isolated_neptune):
    # Setup shared device across 3 customers
    dev_id = "dev_shared_terminal"
    for i in range(1, 4):
        isolated_neptune.upsert_edge(f"ACC-DEV-{i}", dev_id, EdgeType.USES_DEVICE)

    shared = isolated_neptune.find_shared_devices()
    assert len(shared) == 1
    assert shared[0]["device_id"] == dev_id
    assert shared[0]["shared_user_count"] == 3

    # Setup circular loop A -> B -> C -> A
    isolated_neptune.upsert_edge("ACC-A", "ACC-B", EdgeType.TRANSFERRED_TO)
    isolated_neptune.upsert_edge("ACC-B", "ACC-C", EdgeType.TRANSFERRED_TO)
    isolated_neptune.upsert_edge("ACC-C", "ACC-A", EdgeType.TRANSFERRED_TO)

    cycles = isolated_neptune.find_cycles(max_length=4)
    assert len(cycles) >= 1
    assert any("ACC-A" in c and "ACC-B" in c and "ACC-C" in c for c in cycles)


# 7. Risk Enrichment Feature Extraction
def test_graph_risk_enricher_features(isolated_neptune):
    enricher = GraphRiskEnricher(client=isolated_neptune)

    # Setup syndicate device
    syndicate_dev = "dev_rogue_box"
    for i in range(1, 4):
        isolated_neptune.upsert_edge(f"ACC-SYN-{i}", syndicate_dev, EdgeType.USES_DEVICE)

    req = RiskEnrichmentRequest(
        transaction_id="TXN-RISK-01",
        account_id="ACC-SYN-1",
        device_id=syndicate_dev,
        amount=5000.0,
    )

    enriched = enricher.enrich(req)
    assert enriched.transaction_id == "TXN-RISK-01"
    assert enriched.shared_device_customers_count >= 3
    assert enriched.is_in_known_fraud_ring is True
    assert enriched.risk_level in (RingRiskLevel.HIGH, RingRiskLevel.CRITICAL)
    assert "graph_network_risk_score" in enriched.enriched_features
    assert "Device Farming" in enriched.network_risk_factors[0]


# 8. API Graph Endpoints Test
def test_api_graph_endpoints_authorized(client, auth_headers):
    # Health
    resp_health = client.get("/graph/health", headers=auth_headers)
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "HEALTHY"

    # Create Entity
    entity_payload = {
        "id": "CUS-API-TEST",
        "type": "CUSTOMER",
        "label": "Test Customer",
        "properties": {"kyc": "VERIFIED"},
    }
    resp_entity = client.post("/graph/entities", json=entity_payload, headers=auth_headers)
    assert resp_entity.status_code == 201
    assert resp_entity.json()["id"] == "CUS-API-TEST"

    # Create Relationship
    rel_payload = {
        "source": "CUS-API-TEST",
        "target": "ACC-API-TEST",
        "type": "OWNS_ACCOUNT",
        "weight": 1.0,
        "properties": {"active": True},
    }
    resp_rel = client.post("/graph/relationships", json=rel_payload, headers=auth_headers)
    assert resp_rel.status_code == 201
    assert resp_rel.json()["source"] == "CUS-API-TEST"

    # Get Entity Details
    resp_get = client.get("/graph/entities/CUS-API-TEST", headers=auth_headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == "CUS-API-TEST"

    # Get Entity Neighbors
    resp_neigh = client.get("/graph/entities/CUS-API-TEST/neighbors", headers=auth_headers)
    assert resp_neigh.status_code == 200
    neighbors = resp_neigh.json()
    assert any(n["id"] == "ACC-API-TEST" for n in neighbors)

    # Get Entity Network
    resp_net = client.get("/graph/entities/CUS-API-TEST/network?depth=2", headers=auth_headers)
    assert resp_net.status_code == 200
    assert resp_net.json()["node_count"] >= 2

    # Risk Enrichment
    enrich_payload = {
        "transaction_id": "TXN-API-ENRICH",
        "account_id": "ACC-API-TEST",
        "amount": 250.0,
    }
    resp_enrich = client.post("/graph/risk-enrichment", json=enrich_payload, headers=auth_headers)
    assert resp_enrich.status_code == 200
    assert "graph_risk_score" in resp_enrich.json()

    # Fraud Rings
    resp_rings = client.get("/graph/fraud-rings", headers=auth_headers)
    assert resp_rings.status_code == 200
    assert isinstance(resp_rings.json(), list)

    # Analyze
    analyze_payload = {"max_depth": 2}
    resp_analyze = client.post("/graph/analyze", json=analyze_payload, headers=auth_headers)
    assert resp_analyze.status_code == 200
    assert "total_nodes" in resp_analyze.json()
    assert "summary" in resp_analyze.json()

