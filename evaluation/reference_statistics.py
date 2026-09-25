"""Reference risk distribution from validation split (for percentile / risk groups)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

from evaluation.evaluate import build_model, predict_split, resolve_manifest
from pathosurv.config import data_config
from training.dataset import SurvivalBagDataset


def build_reference_statistics(
    checkpoint_path: Path,
    manifest_path: Path,
    features_dir: Path,
    *,
    reference_split: str = "validation",
) -> dict:
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = build_model(ckpt["model_name"], int(ckpt["embedding_dim"]))
    model.load_state_dict(ckpt["state_dict"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    ds = SurvivalBagDataset(manifest_path, features_dir, split=reference_split)
    risk, _, _ = predict_split(model, ds, device)
    if len(risk) == 0:
        raise ValueError(f"No cases in reference split: {reference_split}")
    qs = np.quantile(risk, [0.0, 0.25, 0.5, 0.75, 1.0])
    return {
        "reference_split": reference_split,
        "sample_count": int(len(risk)),
        "risk_score_summary": {
            "min": float(qs[0]),
            "p25": float(qs[1]),
            "median": float(qs[2]),
            "p75": float(qs[3]),
            "max": float(qs[4]),
        },
        "risk_group_thresholds": {
            "method": "validation_quantiles",
            "low_to_medium": float(qs[1]),
            "medium_to_high": float(qs[3]),
        },
        "model_name": ckpt["model_name"],
        "encoder_id": ckpt.get("encoder_id"),
    }


def resolve_manifest(explicit: Path | None) -> Path:
    cfg = data_config()
    if explicit and explicit.is_file():
        return explicit
    synthetic = Path(cfg["features_dir"]) / "synthetic_manifest.csv"
    if synthetic.is_file():
        return synthetic
    return Path(cfg["final_manifest_path"])


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/reference_statistics.json"))
    args = parser.parse_args()
    cfg = data_config()
    manifest = resolve_manifest(args.manifest)
    stats = build_reference_statistics(
        args.checkpoint,
        manifest,
        Path(cfg["features_dir"]),
    )
    args.output.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
