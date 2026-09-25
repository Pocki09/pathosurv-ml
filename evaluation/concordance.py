"""Harrell C-index via scikit-survival (higher risk = shorter survival)."""

from __future__ import annotations

import numpy as np
from sksurv.metrics import concordance_index_censored


def harrell_c_index(
    event: np.ndarray,
    time: np.ndarray,
    risk: np.ndarray,
) -> float:
    """``event``: bool or 0/1, ``time`` > 0, ``risk``: higher = worse prognosis."""
    y = np.array(
        [(bool(e), float(t)) for e, t in zip(event, time, strict=True)],
        dtype=[("event", "?"), ("time", "<f8")],
    )
    return float(concordance_index_censored(y["event"], y["time"], risk)[0])
