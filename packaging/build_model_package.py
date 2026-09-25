"""Build deployable model package from checkpoint + configs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import torch
import yaml

from evaluation.evaluate import evaluate_checkpoint
from evaluation.reference_statistics import build_reference_statistics
from pathosurv.config import data_config, load_yaml


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_package(
    checkpoint_path: Path,
    output_dir: Path,
    *,
    manifest_path: Path,
    features_dir: Path,
) -> Path:
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.pth"
    torch.save(ckpt["state_dict"], model_path)

    ref = build_reference_statistics(checkpoint_path, manifest_path, features_dir)
    (output_dir / "reference_statistics.json").write_text(json.dumps(ref, indent=2), encoding="utf-8")

    test_metrics = evaluate_checkpoint(checkpoint_path, manifest_path, features_dir, "test")
    (output_dir / "metrics.json").write_text(json.dumps(test_metrics, indent=2), encoding="utf-8")

    for name in ("model.yaml", "encoder.yaml", "preprocessing.yaml"):
        shutil.copy2(Path("configs") / name, output_dir / name.replace(".yaml", "_config.yaml"))

    (output_dir / "model_config.yaml").write_text(
        yaml.safe_dump(
            {
                "model_name": ckpt["model_name"],
                "embedding_dim": ckpt["embedding_dim"],
            }
        ),
        encoding="utf-8",
    )

    manifest = {
        "package_version": "1.0.0",
        "model_contract_version": "pathosurv-lite-v1",
        "model_name": ckpt["model_name"],
        "checkpoint_sha256": sha256_file(model_path),
        "encoder_id": ckpt.get("encoder_id"),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "model_card.md").write_text(
        "# PathoSurv Lite model (research prototype)\n\n"
        "Not for clinical use. Risk scores are relative rankings only.\n",
        encoding="utf-8",
    )
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    cfg = data_config()
    from evaluation.evaluate import resolve_manifest

    manifest = resolve_manifest(args.manifest)
    out = args.output or Path(cfg["model_package_dir"]) / "pathosurv-model-v1"
    build_package(
        args.checkpoint,
        out,
        manifest_path=manifest,
        features_dir=Path(cfg["features_dir"]),
    )
    print(f"Package written to {out}")


if __name__ == "__main__":
    main()
