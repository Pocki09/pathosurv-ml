"""
Create a GDC subset manifest and optionally invoke gdc-client.

Download 3–10 WSI for smoke test before full cohort download.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from data_tools.gdc_manifest import GDC_MANIFEST_COLUMNS, read_gdc_manifest
from pathosurv.config import data_config
from pathosurv.seed import set_seed

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_subset_manifest(
    matched_csv: Path,
    full_manifest_path: Path,
    output_manifest: Path,
    num_samples: int,
    seed: int,
) -> pd.DataFrame:
    matched = pd.read_csv(matched_csv)
    if len(matched) == 0:
        raise ValueError(f"No rows in {matched_csv}")

    set_seed(seed)
    n = min(num_samples, len(matched))
    # Deterministic: sort by file id then take head (reproducible without random shuffle)
    subset = matched.sort_values("id").head(n)

    full = read_gdc_manifest(full_manifest_path)
    ids = set(subset["id"])
    manifest_subset = full[full["id"].isin(ids)][list(GDC_MANIFEST_COLUMNS)]

    if len(manifest_subset) != n:
        missing = n - len(manifest_subset)
        logger.warning("%d ids from matched cohort not found in GDC manifest", missing)

    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest_subset.to_csv(output_manifest, sep="\t", index=False)
    logger.info("Wrote subset manifest (%d files) → %s", len(manifest_subset), output_manifest)
    return manifest_subset


def run_gdc_client(manifest_path: Path, download_dir: Path) -> None:
    gdc = shutil.which("gdc-client")
    if not gdc:
        logger.warning(
            "gdc-client not on PATH. Install GDC Data Transfer Tool, then run:\n"
            "  gdc-client download -m %s -d %s",
            manifest_path,
            download_dir,
        )
        return

    download_dir.mkdir(parents=True, exist_ok=True)
    cmd = [gdc, "download", "-m", str(manifest_path), "-d", str(download_dir)]
    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and optionally download WSI smoke subset")
    parser.add_argument("-n", "--num-samples", type=int, default=None)
    parser.add_argument("--no-download", action="store_true", help="Only write subset manifest")
    parser.add_argument("--matched", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-manifest", type=Path)
    parser.add_argument("--download-dir", type=Path)
    args = parser.parse_args()

    cfg = data_config()
    n = args.num_samples or int(cfg.get("smoke_test_wsi_count", 3))
    matched = args.matched or Path(cfg["matched_cohort_path"])
    full_manifest = args.manifest or Path(cfg["manifest_path"])
    out_manifest = args.output_manifest or Path(cfg["subset_manifest_path"])
    download_dir = args.download_dir or Path(cfg["wsi_download_dir"])
    seed = int(cfg.get("random_seed", 42))

    build_subset_manifest(matched, full_manifest, out_manifest, n, seed)
    if not args.no_download:
        run_gdc_client(out_manifest, download_dir)
    else:
        logger.info("Skipped download (--no-download)")


if __name__ == "__main__":
    main()
