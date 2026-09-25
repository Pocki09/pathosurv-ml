"""Mean-pooled slide embedding + Cox head (baseline)."""

from __future__ import annotations

import torch
from torch import nn

from models.cox_head import CoxHead


class MeanPoolingCox(nn.Module):
    def __init__(self, embedding_dim: int) -> None:
        super().__init__()
        self.head = CoxHead(embedding_dim)

    def forward(self, embeddings: torch.Tensor) -> tuple[torch.Tensor, None]:
        """
        ``embeddings``: (N_patches, D)
        Returns slide log-risk and ``None`` attention weights.
        """
        if embeddings.ndim != 2:
            raise ValueError("expected (N, D) patch embeddings")
        slide = embeddings.mean(dim=0)
        return self.head(slide.unsqueeze(0)).squeeze(0), None
