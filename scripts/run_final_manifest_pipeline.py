"""Build final survival manifest and dataset audit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS = [
    [sys.executable, "-m", "data_tools.build_final_manifest"],
    [sys.executable, "-m", "data_tools.validate_final_manifest"],
]


def main() -> None:
    for cmd in STEPS:
        print("\n>>>", " ".join(cmd))
        subprocess.run(cmd, cwd=ROOT, check=True)
    print("\nFinal manifest ready. Next: patient-level splits (create_patient_splits).")


if __name__ == "__main__":
    main()
