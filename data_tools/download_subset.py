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


def filter_matched_to_final_manifest_slides(
    matched: pd.DataFrame,
    final_manifest_path: Path,
) -> pd.DataFrame:
    """Keep only matched rows whose slide_id is the canonical slide in final_manifest."""
    final = pd.read_csv(final_manifest_path)
    for col in ("slide_id",):
        if col not in final.columns:
            raise ValueError(f"final_manifest missing column: {col}")
    if "slide_id" not in matched.columns:
        raise ValueError("matched cohort missing column: slide_id")
    allowed = set(final["slide_id"].astype(str))
    filtered = matched[matched["slide_id"].astype(str).isin(allowed)].copy()
    if filtered.empty:
        raise ValueError(
            f"No matched cohort rows left after restricting to slide_id in {final_manifest_path}"
        )
    dropped = len(matched) - len(filtered)
    if dropped:
        logger.info(
            "Restricted matched cohort to final_manifest slide_id (%d -> %d rows)",
            len(matched),
            len(filtered),
        )
    return filtered


def build_subset_manifest(
    matched_csv: Path,
    full_manifest_path: Path,
    output_manifest: Path,
    num_samples: int,
    seed: int,
    *,
    final_manifest_path: Path | None = None,
    case_ids: list[str] | None = None,
) -> pd.DataFrame:
    matched = pd.read_csv(matched_csv)
    if len(matched) == 0:
        raise ValueError(f"No rows in {matched_csv}")

    if final_manifest_path is not None:
        matched = filter_matched_to_final_manifest_slides(matched, final_manifest_path)

    if case_ids:
        if "case_id" not in matched.columns:
            raise ValueError("matched cohort missing column: case_id")
        allowed_cases = {str(c) for c in case_ids}
        matched = matched[matched["case_id"].astype(str).isin(allowed_cases)].copy()
        if matched.empty:
            raise ValueError(f"No rows for case_id in {allowed_cases}")

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
    parser.add_argument(
        "--from-final-manifest",
        action="store_true",
        help="Restrict subset to slide_id values selected in final_manifest.csv before top-n",
    )
    parser.add_argument(
        "--final-manifest",
        type=Path,
        help="Path to final_manifest.csv (default: configs/data.yaml final_manifest_path)",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        default=None,
        help="Limit to one or more case_id values (after optional final_manifest filter)",
    )
    args = parser.parse_args()

    cfg = data_config()
    n = args.num_samples or int(cfg.get("smoke_test_wsi_count", 3))
    matched = args.matched or Path(cfg["matched_cohort_path"])
    full_manifest = args.manifest or Path(cfg["manifest_path"])
    out_manifest = args.output_manifest or Path(cfg["subset_manifest_path"])
    download_dir = args.download_dir or Path(cfg["wsi_download_dir"])
    seed = int(cfg.get("random_seed", 42))
    final_manifest_path: Path | None = None
    if args.from_final_manifest:
        final_manifest_path = args.final_manifest or Path(cfg["final_manifest_path"])

    build_subset_manifest(
        matched,
        full_manifest,
        out_manifest,
        n,
        seed,
        final_manifest_path=final_manifest_path,
        case_ids=args.case_id,
    )
    if not args.no_download:
        run_gdc_client(out_manifest, download_dir)
    else:
        logger.info("Skipped download (--no-download)")


if __name__ == "__main__":
    main()
