"""Run Phases 6–14 smoke path (real embeddings on subset + synthetic train/demo package)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> None:
    print("\n>>>", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    py = sys.executable
    run([py, "-m", "pytest", "tests/test_cox_loss.py", "tests/test_model_shapes.py", "tests/test_cindex.py", "-q"])
    run([py, "-m", "preprocessing.extract_embeddings", "--max-patches", "50"])
    run([py, "-m", "preprocessing.validate_embeddings"])
    ckpt = ROOT / "data" / "checkpoints" / "attention_mil_cox_best.pt"
    manifest = str(ROOT / "data" / "features" / "synthetic_manifest.csv")
    run([py, "-m", "training.train", "--model", "mean_pooling_cox", "--synthetic-demo"])
    run([py, "-m", "training.train", "--model", "attention_mil_cox", "--synthetic-demo"])
    run([
        py, "-m", "evaluation.evaluate",
        "--checkpoint", str(ckpt),
        "--manifest", manifest,
        "--split", "test",
        "--output", "data/metrics_test.json",
    ])
    run([py, "-m", "evaluation.reference_statistics", "--checkpoint", str(ckpt), "--manifest", manifest])
    run([py, "-m", "packaging.build_model_package", "--checkpoint", str(ckpt), "--manifest", manifest])
    print("\nPhases 6–14 smoke finished. See docs/HUONG_DAN_HUAN_LUYEN.md for full cohort / Colab training.")


if __name__ == "__main__":
    main()
