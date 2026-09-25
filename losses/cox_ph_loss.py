"""Cox partial likelihood loss (higher risk score = shorter survival)."""

from __future__ import annotations

import torch


def cox_ph_loss(
    risk: torch.Tensor,
    time: torch.Tensor,
    event: torch.Tensor,
) -> torch.Tensor:
    """
    Negative Cox partial log-likelihood normalized by number of events.

    ``risk``: shape (B,), unconstrained log-risk scores.
    ``time``: shape (B,), survival time > 0.
    ``event``: shape (B,), 1 if event observed else 0.
    """
    if risk.ndim != 1 or time.shape != risk.shape or event.shape != risk.shape:
        raise ValueError("risk, time, event must be 1D tensors of equal length")
    if risk.numel() == 0:
        raise ValueError("empty batch")
    event_count = event.sum()
    if event_count <= 0:
        raise ValueError("batch must contain at least one event for Cox loss")

    order = torch.argsort(time, descending=True)
    risk = risk[order]
    event = event[order]
    log_cumsum = torch.logcumsumexp(risk, dim=0)
    loss = -(event * (risk - log_cumsum)).sum() / event_count
    return loss
