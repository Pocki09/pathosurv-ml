"""Run Phase 4: patient-level splits on final_manifest.csv."""

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
    print("\nPhase 4 finished. Next: Phase 5 WSI preprocessing smoke test (TRIDENT).")


if __name__ == "__main__":
    main()
