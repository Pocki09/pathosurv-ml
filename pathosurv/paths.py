"""Project root and path resolution (no machine-specific defaults)."""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """Repository root (parent of the ``pathosurv`` package)."""
    env = os.environ.get("PATHOSURV_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def resolve_path(path: str | Path, *, base: Path | None = None) -> Path:
    """Resolve ``path`` relative to project root unless already absolute."""
    p = Path(path)
    if p.is_absolute():
        return p
    root = base if base is not None else project_root()
    return (root / p).resolve()
