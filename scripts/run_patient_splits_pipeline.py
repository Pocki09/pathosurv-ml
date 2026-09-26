"""Assign patient-level train/val/test splits on final_manifest.csv."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS = [
    [sys.executable, "-m", "data_tools.create_patient_splits"],
    [sys.executable, "-m", "data_tools.validate_final_manifest", "--require-split"],
]


def main() -> None:
    for cmd in STEPS:
        print("\n>>>", " ".join(cmd))
        subprocess.run(cmd, cwd=ROOT, check=True)
    print("\nSplits assigned. Next: WSI preprocessing (run_wsi_preprocess_pipeline).")


if __name__ == "__main__":
    main()
