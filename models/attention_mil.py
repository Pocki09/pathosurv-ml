"""Attention-based MIL aggregator + Cox head."""

from __future__ import annotations

import torch
from torch import nn

from models.cox_head import CoxHead


class AttentionMILCox(nn.Module):
    def __init__(self, embedding_dim: int, hidden_dim: int = 256) -> None:
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )
        self.head = CoxHead(embedding_dim)

    def forward(self, embeddings: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns slide log-risk and attention weights (N_patches,) summing to 1."""
        scores = self.attention(embeddings).squeeze(-1)
        weights = torch.softmax(scores, dim=0)
        slide = (weights.unsqueeze(1) * embeddings).sum(dim=0)
        risk = self.head(slide.unsqueeze(0)).squeeze(0)
        return risk, weights
