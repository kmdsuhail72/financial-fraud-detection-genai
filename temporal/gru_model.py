"""PyTorch GRU Sequence Classification Model for Real-Time Temporal Fraud Detection."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger("finguard-temporal-gru")


class TemporalGRUClassifier(nn.Module):
    """
    2-Layer GRU Sequence Classifier:
        Input: [Batch, Sequence_Length (T), Feature_Dim (12)]
        GRU: 12 -> 64 (2 layers, batch_first=True, dropout=0.2)
        Linear Head: 64 -> 32 -> ReLU -> 2 (Binary Fraud Logits)
    """

    def __init__(
        self,
        input_dim: int = 12,
        hidden_dim: int = 64,
        num_layers: int = 2,
        num_classes: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.num_classes = num_classes

        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.LayerNorm(32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes),
        )

    def forward(
        self,
        x: torch.Tensor,
        h0: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x: [B, T, D]
        Returns:
            logits: [B, num_classes]
            hn: [num_layers, B, hidden_dim]
        """
        # Out: [B, T, hidden_dim]
        out, hn = self.gru(x, h0)
        # Take representation at last time-step T
        last_step = out[:, -1, :]
        logits = self.fc(last_step)
        return logits, hn

    def predict_probability(self, x: torch.Tensor) -> float:
        """Evaluates single sequence [1, T, D] or [T, D] and returns scalar fraud probability."""
        self.eval()
        with torch.no_grad():
            if x.dim() == 2:
                x = x.unsqueeze(0)
            logits, _ = self.forward(x)
            probs = F.softmax(logits, dim=-1)
            fraud_prob = float(probs[0, 1].item())
        return round(fraud_prob, 4)
