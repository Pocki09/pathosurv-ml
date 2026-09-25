"""Validate embedding artifact schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from pathosurv.config import data_config


def validate_file(path: Path) -> list[str]:
    errors = []
    if not path.is_file():
        return [f"missing: {path}"]
    data = torch.load(path, map_location="cpu", weights_only=False)
    emb = data.get("embeddings")
    if emb is None:
        errors.append("missing embeddings tensor")
        return errors
    if torch.isnan(emb).any() or torch.isinf(emb).any():
        errors.append("NaN/Inf in embeddings")
    if emb.numel() > 0 and emb.abs().sum() == 0:
        errors.append("all-zero embeddings")
    coords = data.get("coordinates")
    if coords is not None and len(coords) != len(emb):
        errors.append("coordinates length mismatch")
    for key in ("encoder_id", "encoder_version", "embedding_dim"):
        if key not in data:
            errors.append(f"missing metadata: {key}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-dir", type=Path)
    args = parser.parse_args()
    cfg = data_config()
    features_dir = args.features_dir or Path(cfg["features_dir"])
    all_errors = []
    for pt in sorted(features_dir.glob("*.pt")):
        all_errors.extend(f"{pt.name}: {e}" for e in validate_file(pt))
    report = {"ok": not all_errors, "errors": all_errors}
    print(json.dumps(report, indent=2))
    if all_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
