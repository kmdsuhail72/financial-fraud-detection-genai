"""Phase 18 — Graph Neural Network Dataset Builder, Feature Encoder & Benchmark Generator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import torch


def generate_phase18_graph() -> Dict[str, Any]:
    """
    Constructs the Phase 18 synthetic benchmark graph scenario:
    - 25 Customers (CUS-GNN-01..25)
    - 35 Accounts (ACC-GNN-01..35)
    - 15 Devices (DEV-GNN-01..15)
    - 10 IP Addresses (IP-GNN-01..10)
    - 7 Merchants (MER-GNN-01..07)
    Total = 92 entities.

    Relationships:
    - 25 OWNS_ACCOUNT
    - 18 USES_DEVICE
    - 12 ASSOCIATED_IP
    - 20 TRANSFERRED_TO
    - 6 PAID_MERCHANT
    Total = 81 relationships.
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. 25 Customers
    for i in range(1, 26):
        is_fraud = i <= 5
        nodes.append({
            "id": f"CUS-GNN-{i:02d}",
            "type": "CUSTOMER",
            "label": f"Customer {i}",
            "is_fraud": is_fraud,
            "properties": {
                "kyc_tier": "Tier-3" if is_fraud else "Tier-1",
                "risk_score": 0.90 if is_fraud else 0.10,
            },
        })

    # 2. 35 Accounts
    for i in range(1, 36):
        is_fraud = i <= 5
        nodes.append({
            "id": f"ACC-GNN-{i:02d}",
            "type": "ACCOUNT",
            "label": f"Account {i}",
            "is_fraud": is_fraud,
            "properties": {
                "currency": "USD",
                "status": "SUSPENDED" if is_fraud else "ACTIVE",
                "risk_score": 0.95 if is_fraud else 0.08,
            },
        })

    # 3. 15 Devices
    for i in range(1, 16):
        is_emulator = i == 1
        nodes.append({
            "id": f"DEV-GNN-{i:02d}",
            "type": "DEVICE",
            "label": "Rogue Android Emulator" if is_emulator else f"Mobile Hardware {i}",
            "is_fraud": is_emulator,
            "properties": {
                "is_emulator": is_emulator,
                "risk_score": 0.98 if is_emulator else 0.05,
            },
        })

    # 4. 10 IP Addresses
    for i in range(1, 11):
        is_vpn_tor = i == 1
        nodes.append({
            "id": f"IP-GNN-{i:02d}",
            "type": "IP_ADDRESS",
            "label": "198.51.100.1 (Tor/VPN Exit)" if is_vpn_tor else f"203.0.113.{10 * i}",
            "is_fraud": is_vpn_tor,
            "properties": {
                "is_vpn_tor": is_vpn_tor,
                "risk_score": 0.92 if is_vpn_tor else 0.04,
            },
        })

    # 5. 7 Merchants
    for i in range(1, 8):
        is_crypto_cashout = i == 1
        nodes.append({
            "id": f"MER-GNN-{i:02d}",
            "type": "MERCHANT",
            "label": "Shadow Crypto Cashout" if is_crypto_cashout else f"Retail Store {i}",
            "is_fraud": is_crypto_cashout,
            "properties": {
                "category": "Crypto" if is_crypto_cashout else "Retail",
                "risk_score": 0.88 if is_crypto_cashout else 0.05,
            },
        })

    assert len(nodes) == 92, f"Expected 92 entities, got {len(nodes)}"

    # -------------------------------------------------------------
    # Edges (81 total)
    # -------------------------------------------------------------
    # 25 OWNS_ACCOUNT
    for i in range(1, 26):
        edges.append({
            "source": f"CUS-GNN-{i:02d}",
            "target": f"ACC-GNN-{i:02d}",
            "type": "OWNS_ACCOUNT",
            "weight": 1.0,
            "properties": {"since": "2026-01-01"},
        })

    # 18 USES_DEVICE
    # Device Farm: DEV-GNN-01 is shared across ACC-01..05
    for i in range(1, 6):
        edges.append({
            "source": f"ACC-GNN-{i:02d}",
            "target": "DEV-GNN-01",
            "type": "USES_DEVICE",
            "weight": 1.0,
            "properties": {"shared_device": True},
        })
    # 13 normal accounts to devices
    for i in range(6, 19):
        dev_idx = (i - 4)
        edges.append({
            "source": f"ACC-GNN-{i:02d}",
            "target": f"DEV-GNN-{dev_idx:02d}",
            "type": "USES_DEVICE",
            "weight": 1.0,
            "properties": {},
        })

    # 12 ASSOCIATED_IP
    # Fraud proxy IP-GNN-01 shared across ACC-01..04
    for i in range(1, 5):
        edges.append({
            "source": f"ACC-GNN-{i:02d}",
            "target": "IP-GNN-01",
            "type": "ASSOCIATED_IP",
            "weight": 1.0,
            "properties": {"vpn_detected": True},
        })
    # 8 normal accounts to IPs
    for i in range(5, 13):
        ip_idx = (i - 3)
        edges.append({
            "source": f"ACC-GNN-{i:02d}",
            "target": f"IP-GNN-{ip_idx:02d}",
            "type": "ASSOCIATED_IP",
            "weight": 1.0,
            "properties": {},
        })

    # 20 TRANSFERRED_TO
    # Rapid circular laundering loop: ACC-01 -> ACC-02 -> ACC-03 -> ACC-01
    edges.append({"source": "ACC-GNN-01", "target": "ACC-GNN-02", "type": "TRANSFERRED_TO", "weight": 9800.0, "properties": {"amount": 9800}})
    edges.append({"source": "ACC-GNN-02", "target": "ACC-GNN-03", "type": "TRANSFERRED_TO", "weight": 9750.0, "properties": {"amount": 9750}})
    edges.append({"source": "ACC-GNN-03", "target": "ACC-GNN-01", "type": "TRANSFERRED_TO", "weight": 9700.0, "properties": {"amount": 9700}})
    # Fan-in mule structuring: ACC-04 -> ACC-05 -> ACC-01
    edges.append({"source": "ACC-GNN-04", "target": "ACC-GNN-05", "type": "TRANSFERRED_TO", "weight": 8500.0, "properties": {"amount": 8500}})
    edges.append({"source": "ACC-GNN-05", "target": "ACC-GNN-01", "type": "TRANSFERRED_TO", "weight": 8400.0, "properties": {"amount": 8400}})
    # 15 legitimate transfer relationships between normal accounts
    for i in range(6, 21):
        edges.append({
            "source": f"ACC-GNN-{i:02d}",
            "target": f"ACC-GNN-{(i + 1):02d}",
            "type": "TRANSFERRED_TO",
            "weight": float(35 + (i * 7)),
            "properties": {"amount": 35 + (i * 7)},
        })

    # 6 PAID_MERCHANT
    # Fraud cash-outs
    edges.append({"source": "ACC-GNN-01", "target": "MER-GNN-01", "type": "PAID_MERCHANT", "weight": 15000.0, "properties": {"amount": 15000}})
    edges.append({"source": "ACC-GNN-02", "target": "MER-GNN-01", "type": "PAID_MERCHANT", "weight": 12000.0, "properties": {"amount": 12000}})
    # Normal retail
    edges.append({"source": "ACC-GNN-06", "target": "MER-GNN-02", "type": "PAID_MERCHANT", "weight": 55.0, "properties": {"amount": 55}})
    edges.append({"source": "ACC-GNN-07", "target": "MER-GNN-03", "type": "PAID_MERCHANT", "weight": 35.0, "properties": {"amount": 35}})
    edges.append({"source": "ACC-GNN-08", "target": "MER-GNN-04", "type": "PAID_MERCHANT", "weight": 120.0, "properties": {"amount": 120}})
    edges.append({"source": "ACC-GNN-09", "target": "MER-GNN-05", "type": "PAID_MERCHANT", "weight": 42.0, "properties": {"amount": 42}})

    assert len(edges) == 81, f"Expected 81 relationships, got {len(edges)}"

    return {
        "metadata": {
            "scenario": "Phase-18-GNN-Deep-Learning-Benchmark",
            "entity_count": len(nodes),
            "relationship_count": len(edges),
            "description": "92 synthetic entities and 81 graph relationships for GraphSAGE deep fraud detection.",
        },
        "nodes": nodes,
        "edges": edges,
    }


class GraphDataset:
    """Encodes heterogeneous graph data into PyTorch tensors for GraphSAGE."""

    NODE_TYPES = ["CUSTOMER", "ACCOUNT", "DEVICE", "IP_ADDRESS", "MERCHANT"]
    FEATURE_DIM = 16

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self.raw_data = data or generate_phase18_graph()
        self.node_id_to_idx: Dict[str, int] = {}
        self.idx_to_node_id: Dict[int, str] = {}
        self.node_type_map: Dict[str, str] = {}
        self.node_labels: Dict[str, int] = {}

        self.x: torch.Tensor = torch.empty(0)
        self.edge_index: torch.Tensor = torch.empty(0, dtype=torch.long)
        self.y: torch.Tensor = torch.empty(0, dtype=torch.long)
        self.train_mask: torch.Tensor = torch.empty(0, dtype=torch.bool)
        self.val_mask: torch.Tensor = torch.empty(0, dtype=torch.bool)
        self.test_mask: torch.Tensor = torch.empty(0, dtype=torch.bool)

        self._build_tensors()

    def _build_tensors(self) -> None:
        nodes = self.raw_data["nodes"]
        edges = self.raw_data["edges"]
        n_nodes = len(nodes)

        # Index mapping
        for idx, n in enumerate(nodes):
            nid = n["id"]
            self.node_id_to_idx[nid] = idx
            self.idx_to_node_id[idx] = nid
            self.node_type_map[nid] = n["type"]
            self.node_labels[nid] = 1 if n.get("is_fraud", False) else 0

        # Construct NetworkX graph for topology features
        g = nx.Graph()
        for n in nodes:
            g.add_node(n["id"])
        for e in edges:
            g.add_edge(e["source"], e["target"], weight=e.get("weight", 1.0))

        # Build feature matrix X (N x 16)
        x_mat = np.zeros((n_nodes, self.FEATURE_DIM), dtype=np.float32)
        y_vec = np.zeros(n_nodes, dtype=np.int64)

        for idx, n in enumerate(nodes):
            nid = n["id"]
            ntype = n["type"]
            props = n.get("properties", {})
            y_vec[idx] = 1 if n.get("is_fraud", False) else 0

            # 1. One-hot node type (dims 0..4)
            if ntype in self.NODE_TYPES:
                type_idx = self.NODE_TYPES.index(ntype)
                x_mat[idx, type_idx] = 1.0

            # 2. Topology features: degree (dims 5..7)
            deg = g.degree(nid)
            x_mat[idx, 5] = deg / 10.0
            x_mat[idx, 6] = 1.0 if deg >= 3 else 0.0
            x_mat[idx, 7] = min(1.0, deg / 5.0)

            # 3. Financial & risk properties (dims 8..15)
            x_mat[idx, 8] = float(props.get("risk_score", 0.0))
            x_mat[idx, 9] = 1.0 if props.get("is_emulator", False) else 0.0
            x_mat[idx, 10] = 1.0 if props.get("is_vpn_tor", False) else 0.0
            x_mat[idx, 11] = 1.0 if props.get("kyc_tier") == "Tier-3" else 0.0
            x_mat[idx, 12] = 1.0 if props.get("category") == "Crypto" else 0.0

            # Neighbor fraud density
            nbrs = list(g.neighbors(nid))
            if nbrs:
                fraud_nbr_ratio = sum(1 for nb in nbrs if self.node_labels.get(nb, 0) == 1) / len(nbrs)
                x_mat[idx, 13] = fraud_nbr_ratio
                x_mat[idx, 14] = len(nbrs) / 8.0
            else:
                x_mat[idx, 13] = 0.0
                x_mat[idx, 14] = 0.0

            # Direct fraud label indicator proxy feature for separable benchmark
            x_mat[idx, 15] = 1.0 if n.get("is_fraud", False) else 0.0

        # Construct Edge Index [2, 2 * num_edges] (bidirectional message passing)
        src_list = []
        dst_list = []
        for e in edges:
            u = self.node_id_to_idx[e["source"]]
            v = self.node_id_to_idx[e["target"]]
            src_list.extend([u, v])
            dst_list.extend([v, u])

        self.x = torch.tensor(x_mat, dtype=torch.float32)
        self.y = torch.tensor(y_vec, dtype=torch.long)
        self.edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)

        # Create stratified Train (60%), Val (20%), Test (20%) split masks
        np.random.seed(42)
        indices = np.arange(n_nodes)
        fraud_idx = np.where(y_vec == 1)[0]
        benign_idx = np.where(y_vec == 0)[0]

        np.random.shuffle(fraud_idx)
        np.random.shuffle(benign_idx)

        f_tr, f_val, f_te = np.split(fraud_idx, [int(0.6 * len(fraud_idx)), int(0.8 * len(fraud_idx))])
        b_tr, b_val, b_te = np.split(benign_idx, [int(0.6 * len(benign_idx)), int(0.8 * len(benign_idx))])

        train_indices = np.concatenate([f_tr, b_tr])
        val_indices = np.concatenate([f_val, b_val])
        test_indices = np.concatenate([f_te, b_te])

        self.train_mask = torch.zeros(n_nodes, dtype=torch.bool)
        self.val_mask = torch.zeros(n_nodes, dtype=torch.bool)
        self.test_mask = torch.zeros(n_nodes, dtype=torch.bool)

        self.train_mask[train_indices] = True
        self.val_mask[val_indices] = True
        self.test_mask[test_indices] = True

