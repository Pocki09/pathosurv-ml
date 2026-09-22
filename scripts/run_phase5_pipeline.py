"""Run Phase 5 WSI preprocessing smoke test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS = [
    [sys.executable, "-m", "preprocessing.run_trident"],
    [sys.executable, "-m", "preprocessing.validate_patches"],
]


def main() -> None:
    for cmd in STEPS:
        print("\n>>>", " ".join(cmd))
        subprocess.run(cmd, cwd=ROOT, check=True)
    print("\nPhase 5 finished. Next: Phase 6 encoder smoke test and embedding extraction.")


if __name__ == "__main__":
    main()
