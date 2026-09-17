"""Open one or more local WSI files (requires openslide optional dependency)."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pathosurv.config import data_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def try_import_openslide():
    try:
        import openslide  # noqa: F401

        return openslide
    except ImportError:
        return None


def inspect_wsi(path: Path, openslide_module) -> dict:
    slide = openslide_module.OpenSlide(str(path))
    props = {
        "path": str(path),
        "vendor": slide.properties.get(openslide_module.PROPERTY_NAME_VENDOR),
        "objective": slide.properties.get(openslide_module.PROPERTY_NAME_OBJECTIVE_POWER),
        "dimensions": slide.dimensions,
        "level_count": slide.level_count,
        "level_dimensions": slide.level_dimensions,
    }
    slide.close()
    return props


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test opening WSI files with OpenSlide")
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--manifest", type=Path, help="Subset manifest (tab-separated)")
    parser.add_argument("--report", type=Path, default=Path("data/wsi_open_test.json"))
    args = parser.parse_args()

    openslide = try_import_openslide()
    cfg = data_config()
    download_dir = args.download_dir or Path(cfg["wsi_download_dir"])
    manifest = args.manifest or Path(cfg["subset_manifest_path"])

    report = {
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "openslide_available": openslide is not None,
        "slides": [],
        "errors": [],
    }

    if openslide is None:
        report["errors"].append(
            "openslide-python not installed. Install with: pip install pathosurv[wsi]"
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.error(report["errors"][0])
        raise SystemExit(2)

    if not manifest.is_file():
        report["errors"].append(f"Manifest not found: {manifest}")
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise SystemExit(1)

    df = pd.read_csv(manifest, sep="\t")
    for _, row in df.iterrows():
        fn = row["filename"]
        fid = row["id"]
        candidates = [download_dir / fn, download_dir / fid / fn]
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            report["errors"].append(f"File not found: {fn}")
            continue
        try:
            report["slides"].append(inspect_wsi(path, openslide))
        except Exception as exc:
            report["errors"].append(f"{fn}: {exc}")

    report["ok"] = len(report["slides"]) > 0 and not report["errors"]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if report["slides"]:
        logger.info("Opened %d slide(s). Report: %s", len(report["slides"]), args.report)
    else:
        logger.warning("No slides opened. See %s", args.report)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
