"""Cross-check random patch coordinates by re-reading regions from the WSI."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from data_tools.wsi_paths import resolve_wsi_file
from pathosurv.config import data_config
from preprocessing.wsi_preprocess import rgb_white_fraction

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def verify_slide(slide_path: Path, manifest_csv: Path, sample_n: int = 5) -> dict:
    import numpy as np
    import openslide

    df = pd.read_csv(manifest_csv)
    accepted = df[df["status"] == "accepted"]
    if accepted.empty:
        return {"ok": False, "error": "no accepted patches"}
    sample = accepted.sample(n=min(sample_n, len(accepted)), random_state=42)
    slide = openslide.OpenSlide(str(slide_path))
    checks = []
    try:
        for _, row in sample.iterrows():
            x, y = int(row["x"]), int(row["y"])
            ps0 = int(row["patch_size"])
            level = int(row["level"])
            read_size = int(row.get("read_size_at_level", ps0))
            if "read_size_at_level" not in row:
                ds = slide.level_downsamples[level]
                read_size = max(1, int(round(ps0 / ds)))
            tile = np.array(slide.read_region((x, y), level, (read_size, read_size)).convert("RGB"))
            checks.append(
                {
                    "x": x,
                    "y": y,
                    "level": level,
                    "shape": list(tile.shape),
                    "white_fraction": round(rgb_white_fraction(tile), 4),
                }
            )
    finally:
        slide.close()
    return {"ok": True, "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify patch coordinates against OpenSlide")
    parser.add_argument("--preprocessed-dir", type=Path)
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--report", type=Path, default=Path("data/phase5_patch_verify.json"))
    args = parser.parse_args()

    cfg = data_config()
    pre_root = args.preprocessed_dir or Path(cfg["preprocessed_dir"])
    download_dir = args.download_dir or Path(cfg["wsi_download_dir"])

    results = []
    for slide_dir in sorted(pre_root.iterdir()) if pre_root.is_dir() else []:
        if not slide_dir.is_dir():
            continue
        manifest = slide_dir / "patch_coordinates.csv"
        if not manifest.is_file():
            continue
        slide_id = slide_dir.name
        # locate WSI from subset manifest by slide_id prefix
        subset = pd.read_csv(cfg["subset_manifest_path"], sep="\t")
        match = subset[subset["filename"].str.startswith(slide_id + ".")]
        if match.empty:
            continue
        row = match.iloc[0]
        wsi = resolve_wsi_file(download_dir, str(row["id"]), str(row["filename"]))
        if wsi is None:
            continue
        results.append(
            {"slide_id": slide_id, **verify_slide(wsi, manifest)}
        )

    report = {"slides": results, "ok": all(r.get("ok") for r in results) and len(results) > 0}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["ok"]:
        raise SystemExit(1)
    logger.info("Patch verify OK → %s", args.report)


if __name__ == "__main__":
    main()
