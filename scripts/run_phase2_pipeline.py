"""Run Phase 2 data steps in order (local)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS = [
    [sys.executable, "-m", "data_tools.cohort_comparison"],
    [sys.executable, "-m", "data_tools.register_manifest"],
    [sys.executable, "-m", "data_tools.build_clinical_manifest"],
    [sys.executable, "-m", "data_tools.build_slide_manifest"],
    [sys.executable, "-m", "data_tools.merge_survival_manifest"],
    [sys.executable, "-m", "data_tools.validate_manifest"],
    [sys.executable, "-m", "data_tools.download_subset", "--no-download"],
    [sys.executable, "-m", "data_tools.verify_downloads"],
]


def main() -> None:
    for cmd in STEPS:
        print("\n>>>", " ".join(cmd))
        subprocess.run(cmd, cwd=ROOT, check=True)
    print("\nPhase 2 pipeline finished. Download WSI with:")
    print("  python -m data_tools.download_subset")
    print("Then verify and open slides:")
    print("  python -m data_tools.verify_downloads")
    print("  python -m preprocessing.validate_wsi")


if __name__ == "__main__":
    main()
