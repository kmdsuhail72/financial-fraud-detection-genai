"""Phase 18 — PyTorch GraphSAGE Implementation, Link Predictor & Explainability Module."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from gnn.models import ExplainableIndicator, GNNRiskLevel

logger = logging.getLogger("finguard-gnn")


class SAGEConv(nn.Module):
    """
    GraphSAGE convolution with Mean Aggregator:
        h_N(v) = MEAN_{u in N(v)} (h_u)
        h_v = sigma( W_self * h_v + W_neigh * h_N(v) + b )
    """

    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features

        self.lin_self = nn.Linear(in_features, out_features, bias=bias)
        self.lin_neigh = nn.Linear(in_features, out_features, bias=False)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.lin_self.weight)
        nn.init.xavier_uniform_(self.lin_neigh.weight)
        if self.lin_self.bias is not None:
            nn.init.zeros_(self.lin_self.bias)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        x: [N, in_features]
        edge_index: [2, E]
        """
        num_nodes = x.size(0)
        src, dst = edge_index[0], edge_index[1]

        # Mean aggregation over neighbors
        neigh_sum = torch.zeros(num_nodes, self.in_features, device=x.device, dtype=x.dtype)
        deg = torch.zeros(num_nodes, 1, device=x.device, dtype=x.dtype)

        # Scatter add source features to destination nodes
        neigh_sum.index_add_(0, dst, x[src])
        deg.index_add_(0, dst, torch.ones((src.size(0), 1), device=x.device, dtype=x.dtype))

        # Avoid division by zero for isolated nodes
        deg_clamped = torch.clamp(deg, min=1.0)
        neigh_mean = neigh_sum / deg_clamped

        # Combine self and neighborhood
        out = self.lin_self(x) + self.lin_neigh(neigh_mean)
        return out


class GraphSAGE(nn.Module):
    """
    2-Layer GraphSAGE Architecture for Fraud Risk Classification:
      Input (16) -> SAGEConv(16 -> 64) -> ReLU -> Dropout -> SAGEConv(64 -> 64) -> Linear(64 -> 2)
    """

    def __init__(
        self,
        in_dim: int = 16,
        hidden_dim: int = 64,
        out_dim: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.out_dim = out_dim
        self.dropout_rate = dropout

        self.conv1 = SAGEConv(in_dim, hidden_dim)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)

        self.classifier = nn.Linear(hidden_dim, out_dim)

        # Link prediction MLP decoder
        self.link_predictor = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def encode(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """Computes latent node representations (embeddings)."""
        h = self.conv1(x, edge_index)
        h = self.norm1(h)
        h = F.relu(h)
        h = F.dropout(h, p=self.dropout_rate, training=self.training)

        h = self.conv2(h, edge_index)
        h = self.norm2(h)
        h = F.relu(h)
        return h  # [N, hidden_dim]

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            logits: [N, out_dim]
            embeddings: [N, hidden_dim]
        """
        embeddings = self.encode(x, edge_index)
        logits = self.classifier(embeddings)
        return logits, embeddings

    def predict_link(self, z_src: torch.Tensor, z_dst: torch.Tensor) -> float:
        """Evaluates probability/strength of association between two node embeddings."""
        combined = torch.cat([z_src, z_dst], dim=-1)
        raw_score = self.link_predictor(combined).squeeze()
        prob = torch.sigmoid(raw_score).item()
        return round(float(prob), 4)


class ExplainabilityEngine:
    """Computes gradient-based feature attribution and neighborhood risk indicators."""

    FEATURE_NAMES = [
        "entity_type_customer",
        "entity_type_account",
        "entity_type_device",
        "entity_type_ip",
        "entity_type_merchant",
        "normalized_degree",
        "high_connectivity_hub",
        "transfer_fan_ratio",
        "prior_risk_score",
        "emulator_device_flag",
        "vpn_tor_proxy_flag",
        "high_risk_kyc_tier",
        "crypto_merchant_flag",
        "neighborhood_fraud_density",
        "degree_scale",
        "direct_fraud_indicator",
    ]

    FEATURE_DESCRIPTIONS = {
        "emulator_device_flag": "Physical device identified as rooted hardware emulator.",
        "vpn_tor_proxy_flag": "Network traffic routed via anonymizing Tor or VPN exit proxy.",
        "high_risk_kyc_tier": "Unverified or suspicious customer KYC registration tier.",
        "crypto_merchant_flag": "Destination identified as high-risk crypto cash-out gateway.",
        "neighborhood_fraud_density": "Immediate 1-hop and 2-hop graph neighbors exhibit elevated fraud rates.",
        "high_connectivity_hub": "Abnormally high fan-out relationship degree in transaction topology.",
        "prior_risk_score": "Historical behavioral baseline risk anomaly score.",
        "direct_fraud_indicator": "Direct syndicate association with confirmed fraud ring accounts.",
    }

    @classmethod
    def explain_node(
        cls,
        model: GraphSAGE,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        node_idx: int,
    ) -> List[ExplainableIndicator]:
        """Calculates input saliency gradients for the predicted fraud class."""
        model.eval()
        x_clone = x.clone().detach().requires_grad_(True)

        logits, _ = model(x_clone, edge_index)
        fraud_score = logits[node_idx, 1]

        # Compute gradient
        model.zero_grad()
        fraud_score.backward()

        if x_clone.grad is not None:
            grads = x_clone.grad[node_idx].detach().cpu().numpy()
            x_vals = x[node_idx].detach().cpu().numpy()
            importances = grads * x_vals
        else:
            importances = x[node_idx].detach().cpu().numpy()

        indicators: List[ExplainableIndicator] = []
        # Rank by importance
        ranked_indices = sorted(
            range(len(importances)),
            key=lambda i: abs(importances[i]),
            reverse=True,
        )

        for idx in ranked_indices:
            feat_name = cls.FEATURE_NAMES[idx]
            val = float(importances[idx])
            if abs(val) > 0.01:
                desc = cls.FEATURE_DESCRIPTIONS.get(
                    feat_name,
                    f"Topological feature '{feat_name}' influenced GNN risk decision.",
                )
                indicators.append(
                    ExplainableIndicator(
                        feature_name=feat_name,
                        attribution_score=round(val, 4),
                        description=desc,
                    )
                )

        return indicators[:4]

