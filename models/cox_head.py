"""Linear Cox head producing a scalar log-risk score."""

from __future__ import annotations

import torch
from torch import nn


class CoxHead(nn.Module):
    def __init__(self, in_features: int) -> None:
        super().__init__()
        self.linear = nn.Linear(in_features, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x).squeeze(-1)
