"""Extract WSI rows from a versioned GDC manifest."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from data_tools.gdc_manifest import filter_wsi_rows, read_gdc_manifest
from pathosurv.config import data_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def build_slide_manifest(manifest_path: Path, output_path: Path) -> pd.DataFrame:
    manifest_df = read_gdc_manifest(manifest_path)
    wsi_df = filter_wsi_rows(manifest_df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wsi_df.to_csv(output_path, index=False)
    logger.info(
        "WSI rows: %d / %d manifest entries → %s",
        len(wsi_df),
        len(manifest_df),
        output_path,
    )
    return wsi_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Build WSI-only manifest from GDC file")
    parser.add_argument("--manifest", type=Path, help="GDC manifest .txt path")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV (default: data/wsi_manifest.csv)",
    )
    args = parser.parse_args()

    cfg = data_config()
    manifest_path = args.manifest or Path(cfg["manifest_path"])
    output_path = args.output or Path(cfg.get("wsi_manifest_path", "data/wsi_manifest.csv"))

    build_slide_manifest(manifest_path, output_path)


if __name__ == "__main__":
    main()
