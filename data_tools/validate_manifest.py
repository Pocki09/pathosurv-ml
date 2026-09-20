"""Validate Phase 2 artifacts (GDC manifest, clinical CSV, matched cohort)."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from data_tools.gdc_manifest import GDC_MANIFEST_COLUMNS, read_gdc_manifest
from pathosurv.config import data_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def validate_gdc_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        df = read_gdc_manifest(path)
    except (FileNotFoundError, ValueError) as exc:
        return [str(exc)]
    if len(df) == 0:
        errors.append("GDC manifest is empty")
    dup_ids = df["id"].duplicated().sum()
    if dup_ids:
        errors.append(f"Duplicate file ids in manifest: {dup_ids}")
    return errors


def validate_clinical_csv(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Clinical CSV not found: {path}"]
    df = pd.read_csv(path)
    for col in ("case_id", "submitter_id", "OS_time", "OS_event"):
        if col not in df.columns:
            errors.append(f"Missing column: {col}")
    if "OS_event" in df.columns:
        bad = ~df["OS_event"].isin([0, 1])
        if bad.any():
            errors.append(f"Invalid OS_event values: {bad.sum()}")
    if "OS_time" in df.columns:
        if (df["OS_time"] <= 0).any():
            errors.append("OS_time must be > 0")
    if df["case_id"].isna().any():
        errors.append("Null case_id in clinical CSV")
    return errors


def validate_matched_cohort(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Matched cohort not found: {path}"]
    df = pd.read_csv(path)
    for col in ("id", "filename", "md5", "submitter_id", "case_id", "OS_time", "OS_event"):
        if col not in df.columns:
            errors.append(f"Matched cohort missing column: {col}")
    if "OS_event" in df.columns and (~df["OS_event"].isin([0, 1])).any():
        errors.append("Invalid OS_event in matched cohort")
    if "OS_time" in df.columns and (df["OS_time"] <= 0).any():
        errors.append("OS_time <= 0 in matched cohort")
    return errors


def run_validation(cfg: dict) -> dict:
    manifest_path = Path(cfg["manifest_path"])
    clinical_path = Path(cfg["output_csv"])
    matched_path = Path(cfg["matched_cohort_path"])
    wsi_dir = Path(cfg["wsi_download_dir"])

    report = {
        "cohort": cfg.get("cohort"),
        "manifest_path": str(manifest_path),
        "clinical_path": str(clinical_path),
        "matched_cohort_path": str(matched_path),
        "errors": [],
        "warnings": [],
        "counts": {},
    }

    for err in validate_gdc_manifest(manifest_path):
        report["errors"].append(f"gdc_manifest: {err}")
    try:
        mdf = read_gdc_manifest(manifest_path)
        report["counts"]["gdc_manifest_rows"] = len(mdf)
        report["counts"]["wsi_rows"] = int(mdf["filename"].str.endswith(".svs", na=False).sum())
    except Exception:
        pass

    for err in validate_clinical_csv(clinical_path):
        report["errors"].append(f"clinical: {err}")
    if clinical_path.is_file():
        cdf = pd.read_csv(clinical_path)
        report["counts"]["clinical_rows"] = len(cdf)
        if "OS_event" in cdf.columns:
            report["counts"]["clinical_events"] = int(cdf["OS_event"].sum())
            report["counts"]["clinical_censored"] = int((cdf["OS_event"] == 0).sum())

    for err in validate_matched_cohort(matched_path):
        report["errors"].append(f"matched: {err}")
    if matched_path.is_file():
        mcoh = pd.read_csv(matched_path)
        report["counts"]["matched_wsi_rows"] = len(mcoh)
        if wsi_dir.is_dir():
            on_disk = 0
            for _, row in mcoh.iterrows():
                fn = row["filename"]
                fid = row["id"]
                if (wsi_dir / fn).is_file() or (wsi_dir / fid / fn).is_file():
                    on_disk += 1
            subset_path = Path(cfg.get("subset_manifest_path", "data/subset_manifest.txt"))
            smoke_on_disk = 0
            if subset_path.is_file():
                sub = pd.read_csv(subset_path, sep="\t")
                for _, row in sub.iterrows():
                    fn, fid = row["filename"], row["id"]
                    if (wsi_dir / fn).is_file() or (wsi_dir / fid / fn).is_file():
                        smoke_on_disk += 1
                report["counts"]["smoke_wsi_on_disk"] = smoke_on_disk
            if on_disk:
                report["counts"]["wsi_files_on_disk"] = on_disk
            elif smoke_on_disk:
                report["counts"]["wsi_files_on_disk"] = smoke_on_disk
            else:
                report["warnings"].append(
                    "No WSI files in wsi_download_dir yet — run download_subset after gdc-client"
                )

    report["ok"] = len(report["errors"]) == 0
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Phase 2 data artifacts")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON report (default: data/phase2_validation.json)",
    )
    args = parser.parse_args()

    cfg = data_config()
    report = run_validation(cfg)
    out = args.report or Path("data/phase2_validation.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if report["ok"]:
        logger.info("Validation passed. Report: %s", out)
    else:
        logger.error("Validation failed: %s", report["errors"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
