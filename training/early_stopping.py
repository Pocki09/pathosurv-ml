"""Early stopping on validation metric (higher C-index is better)."""

from __future__ import annotations


class EarlyStopping:
    def __init__(self, patience: int = 10, min_delta: float = 0.0) -> None:
        self.patience = patience
        self.min_delta = min_delta
        self.best: float | None = None
        self.counter = 0
        self.should_stop = False

    def step(self, metric: float) -> bool:
        if self.best is None or metric > self.best + self.min_delta:
            self.best = metric
            self.counter = 0
            return True
        self.counter += 1
        if self.counter >= self.patience:
            self.should_stop = True
        return False
