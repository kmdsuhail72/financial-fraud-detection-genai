"""Unit and Integration Tests for Phase 18 Enterprise Graph Neural Networks & Deep Learning.

Validates:
1. Benchmark synthetic graph topology (92 entities, 81 relationships).
2. Heterogeneous feature tensor encoding and split masks.
3. GraphSAGE 2-layer forward pass and 64-dim embeddings extraction.
4. Model training convergence and separable benchmark metrics.
5. Latent link prediction scoring and anomaly categorization.
6. Explainable risk attribution via gradient-based indicators.
7. REST API model lifecycle: POST /model/load and GET /model/info.
8. REST API inference: POST /model/predict/node, /predict/nodes, /predict/link, /embeddings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import torch
import torch.nn.functional as F
from fastapi.testclient import TestClient

from api.app import app
from gnn.dataset import GraphDataset, generate_phase18_graph
from gnn.graphsage import ExplainabilityEngine, GraphSAGE
from gnn.models import (
    BatchNodePredictionResponse,
    EmbeddingExtractionResponse,
    GNNRiskLevel,
    LinkPredictionResponse,
    ModelInfoResponse,
    ModelLoadResponse,
    NodePredictionResponse,
)
from gnn.service import GNNModelService, get_gnn_service
from security.auth import create_test_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_test_token(roles=["Investigator"], email="investigator@finguard.internal")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def gnn_service():
    return get_gnn_service()


# =============================================================================
# 1. Benchmark Graph Topology Test
# =============================================================================
def test_benchmark_graph_structure():
    """Verifies generation of exactly 92 synthetic entities and 81 graph relationships."""
    graph_data = generate_phase18_graph()
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    assert len(nodes) == 92, f"Expected 92 entities, got {len(nodes)}"
    assert len(edges) == 81, f"Expected 81 relationships, got {len(edges)}"

    # Node counts by type
    counts = {}
    for n in nodes:
        counts[n["type"]] = counts.get(n["type"], 0) + 1

    assert counts.get("CUSTOMER") == 25
    assert counts.get("ACCOUNT") == 35
    assert counts.get("DEVICE") == 15
    assert counts.get("IP_ADDRESS") == 10
    assert counts.get("MERCHANT") == 7

    # Edge counts by type
    edge_counts = {}
    for e in edges:
        edge_counts[e["type"]] = edge_counts.get(e["type"], 0) + 1

    assert edge_counts.get("OWNS_ACCOUNT") == 25
    assert edge_counts.get("USES_DEVICE") == 18
    assert edge_counts.get("ASSOCIATED_IP") == 12
    assert edge_counts.get("TRANSFERRED_TO") == 20
    assert edge_counts.get("PAID_MERCHANT") == 6


# =============================================================================
# 2. Feature Tensor Encoding Test
# =============================================================================
def test_dataset_feature_tensor_encoding():
    """Verifies heterogeneous node property encoding into PyTorch tensors with split masks."""
    dataset = GraphDataset()

    assert dataset.x.shape == (92, 16), f"Expected (92, 16) feature matrix, got {dataset.x.shape}"
    assert dataset.edge_index.shape[0] == 2
    assert dataset.edge_index.shape[1] == 162  # 81 edges * 2 (bidirectional)
    assert dataset.y.shape == (92,)

    # Verify split masks cover all 92 nodes without overlap
    total_split = dataset.train_mask.sum() + dataset.val_mask.sum() + dataset.test_mask.sum()
    assert total_split.item() == 92
    assert (dataset.train_mask & dataset.val_mask).sum().item() == 0
    assert (dataset.val_mask & dataset.test_mask).sum().item() == 0


# =============================================================================
# 3. GraphSAGE Forward Pass and Embeddings Test
# =============================================================================
def test_graphsage_forward_pass_and_embeddings():
    """Verifies 2-layer GraphSAGE forward pass and 64-dimensional latent embedding generation."""
    dataset = GraphDataset()
    model = GraphSAGE(in_dim=16, hidden_dim=64, out_dim=2, dropout=0.0)
    model.eval()

    with torch.no_grad():
        logits, embeddings = model(dataset.x, dataset.edge_index)

    assert logits.shape == (92, 2)
    assert embeddings.shape == (92, 64)
    assert not torch.isnan(logits).any(), "Logits must not contain NaN"
    assert not torch.isnan(embeddings).any(), "Embeddings must not contain NaN"


# =============================================================================
# 4. Training Convergence and Evaluation Test
# =============================================================================
def test_graphsage_training_and_convergence():
    """Verifies that GraphSAGE optimizes loss and converges on the synthetic dataset."""
    dataset = GraphDataset()
    model = GraphSAGE(in_dim=16, hidden_dim=64, out_dim=2, dropout=0.1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = torch.nn.CrossEntropyLoss()

    initial_loss = criterion(model(dataset.x, dataset.edge_index)[0][dataset.train_mask], dataset.y[dataset.train_mask]).item()

    model.train()
    for _ in range(40):
        optimizer.zero_grad()
        logits, _ = model(dataset.x, dataset.edge_index)
        loss = criterion(logits[dataset.train_mask], dataset.y[dataset.train_mask])
        loss.backward()
        optimizer.step()

    final_loss = loss.item()
    assert final_loss < initial_loss, f"Expected final loss ({final_loss}) < initial loss ({initial_loss})"

    model.eval()
    with torch.no_grad():
        test_logits, _ = model(dataset.x, dataset.edge_index)
        preds = torch.argmax(test_logits, dim=-1)
        acc = (preds[dataset.test_mask] == dataset.y[dataset.test_mask]).float().mean().item()

    assert acc >= 0.90, f"Expected test accuracy >= 0.90, got {acc}"


# =============================================================================
# 5. Link Prediction Decoder Test
# =============================================================================
def test_suspicious_link_prediction(gnn_service):
    """Verifies link prediction scoring between connected and candidate entities."""
    # Predict link between syndicate nodes (ACC-GNN-01 and DEV-GNN-01)
    res = gnn_service.predict_link("ACC-GNN-01", "DEV-GNN-01")
    assert isinstance(res, LinkPredictionResponse)
    assert res.source_id == "ACC-GNN-01"
    assert res.target_id == "DEV-GNN-01"
    assert 0.0 <= res.link_score <= 1.0
    assert len(res.advisory_assessment) > 0


# =============================================================================
# 6. Explainable Risk Attribution Test
# =============================================================================
def test_explainable_risk_attribution(gnn_service):
    """Verifies gradient saliency attribution and human-readable indicator extraction."""
    # Syndicate account
    node_idx = gnn_service.dataset.node_id_to_idx["ACC-GNN-01"]
    indicators = ExplainabilityEngine.explain_node(
        gnn_service.model,
        gnn_service.dataset.x,
        gnn_service.dataset.edge_index,
        node_idx,
    )

    assert isinstance(indicators, list)
    assert len(indicators) >= 1
    top_ind = indicators[0]
    assert len(top_ind.feature_name) > 0
    assert len(top_ind.description) > 0


# =============================================================================
# 7. REST API Model Load and Info Endpoints Test
# =============================================================================
def test_api_model_load_and_info(client, auth_headers):
    """Verifies POST /model/load and GET /model/info endpoints."""
    # 1. POST /model/load
    resp_load = client.post("/model/load", json={}, headers=auth_headers)
    assert resp_load.status_code == 200
    load_data = resp_load.json()
    assert load_data["status"] == "SUCCESS"
    assert load_data["parameters_loaded"] > 0
    assert "GraphSAGE" in load_data["architecture"]

    # 2. GET /model/info
    resp_info = client.get("/model/info", headers=auth_headers)
    assert resp_info.status_code == 200
    info_data = resp_info.json()
    assert info_data["model_name"] == "FinGuard-GraphSAGE-Fraud"
    assert info_data["input_dim"] == 16
    assert info_data["hidden_dim"] == 64
    assert info_data["is_loaded"] is True
    assert "precision" in info_data["metrics"]


# =============================================================================
# 8. REST API Node and Link Inference Endpoints Test
# =============================================================================
def test_api_node_and_link_inference(client, auth_headers):
    """Verifies POST /model/predict/node, /predict/nodes, /predict/link, and /embeddings."""
    # 1. POST /model/predict/node for syndicate entity
    node_req = {
        "entity_id": "ACC-GNN-01",
        "include_embeddings": True,
        "include_explainability": True,
    }
    resp_node = client.post("/model/predict/node", json=node_req, headers=auth_headers)
    assert resp_node.status_code == 200
    node_data = resp_node.json()
    assert node_data["entity_id"] == "ACC-GNN-01"
    assert node_data["fraud_probability"] >= 0.50
    assert node_data["is_advisory"] is True
    assert node_data["embedding"] is not None
    assert len(node_data["embedding"]) == 64
    assert len(node_data["explainable_indicators"]) >= 1

    # 2. POST /model/predict/nodes batch
    batch_req = {"entity_ids": ["ACC-GNN-01", "ACC-GNN-10"]}
    resp_batch = client.post("/model/predict/nodes", json=batch_req, headers=auth_headers)
    assert resp_batch.status_code == 200
    batch_data = resp_batch.json()
    assert batch_data["total_evaluated"] == 2
    assert len(batch_data["predictions"]) == 2

    # 3. POST /model/predict/link
    link_req = {"source_id": "ACC-GNN-01", "target_id": "MER-GNN-01"}
    resp_link = client.post("/model/predict/link", json=link_req, headers=auth_headers)
    assert resp_link.status_code == 200
    link_data = resp_link.json()
    assert link_data["source_id"] == "ACC-GNN-01"
    assert link_data["target_id"] == "MER-GNN-01"
    assert "link_score" in link_data

    # 4. POST /model/embeddings
    resp_emb = client.post("/model/embeddings", json={}, headers=auth_headers)
    assert resp_emb.status_code == 200
    emb_data = resp_emb.json()
    assert emb_data["dimension"] == 64
    assert emb_data["total_entities"] == 92
    assert "ACC-GNN-01" in emb_data["embeddings"]

