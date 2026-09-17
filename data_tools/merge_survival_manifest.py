"""Merge WSI manifest rows with clinical survival table (patient barcode join)."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from data_tools.gdc_manifest import filter_wsi_rows, read_gdc_manifest
from pathosurv.config import data_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def merge_manifest_and_clinical(
    manifest_path: Path,
    clinical_csv: Path,
    output_path: Path,
) -> pd.DataFrame:
    logger.info("Matching WSI manifest with clinical metadata")
    wsi_df = filter_wsi_rows(read_gdc_manifest(manifest_path))
    clinical_df = pd.read_csv(clinical_csv)
    if "submitter_id" not in clinical_df.columns:
        raise ValueError(f"Clinical CSV missing submitter_id: {clinical_csv}")

    matched = pd.merge(wsi_df, clinical_df, on="submitter_id", how="inner")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    matched.to_csv(output_path, index=False)
    logger.info("Matched %d WSI rows with survival labels → %s", len(matched), output_path)
    return matched


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge GDC WSI manifest with clinical CSV")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--clinical", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cfg = data_config()
    manifest_path = args.manifest or Path(cfg["manifest_path"])
    clinical_path = args.clinical or Path(cfg["output_csv"])
    output_path = args.output or Path(cfg["matched_cohort_path"])

    merge_manifest_and_clinical(manifest_path, clinical_path, output_path)


if __name__ == "__main__":
    main()
