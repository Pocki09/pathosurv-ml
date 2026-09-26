"""Validate ``final_manifest.csv`` schema and consistency rules."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from pathosurv.paths import project_root, resolve_path

FINAL_MANIFEST_COLUMNS = (
    "case_id",
    "slide_id",
    "wsi_path",
    "survival_time_days",
    "event_status",
    "split",
)

ALLOWED_SPLITS = frozenset({"train", "validation", "test"})


def validate_final_manifest_df(
    df: pd.DataFrame,
    *,
    download_dir: Path | None = None,
    require_wsi_on_disk: bool = False,
    require_split_assigned: bool = False,
) -> list[str]:
    errors: list[str] = []
    for col in FINAL_MANIFEST_COLUMNS:
        if col not in df.columns:
            errors.append(f"Missing column: {col}")

    if errors:
        return errors

    if df.empty:
        errors.append("final_manifest is empty")
        return errors

    if df["case_id"].isna().any():
        errors.append("Null case_id")
    if df["slide_id"].isna().any():
        errors.append("Null slide_id")
    if df["wsi_path"].isna().any() or (df["wsi_path"].astype(str).str.strip() == "").any():
        errors.append("Empty wsi_path")

    if (df["survival_time_days"] <= 0).any():
        errors.append("survival_time_days must be > 0")
    bad_event = ~df["event_status"].isin([0, 1])
    if bad_event.any():
        errors.append(f"Invalid event_status values: {int(bad_event.sum())}")

    if df["slide_id"].duplicated().any():
        errors.append("Duplicate slide_id in final manifest")
    if df["case_id"].duplicated().any():
        errors.append("Duplicate case_id in final manifest (expected one slide per patient)")

    if require_split_assigned:
        blank = df["split"].astype(str).str.strip() == ""
        if blank.any():
            errors.append(f"split must be assigned: {int(blank.sum())} blank rows")
        bad_split = ~df["split"].isin(ALLOWED_SPLITS)
        if bad_split.any():
            errors.append(f"Invalid split labels: {int(bad_split.sum())} row(s)")

    if require_wsi_on_disk:
        root = project_root()
        missing = 0
        for _, row in df.iterrows():
            wsi = resolve_path(row["wsi_path"], base=root)
            if not wsi.is_file():
                missing += 1
        if missing:
            errors.append(f"wsi_path missing on disk: {missing} row(s)")

    return errors


def validate_final_manifest_file(
    path: Path,
    *,
    download_dir: Path | None = None,
    require_wsi_on_disk: bool = False,
    require_split_assigned: bool = False,
) -> list[str]:
    if not path.is_file():
        return [f"final_manifest not found: {path}"]
    df = pd.read_csv(path)
    return validate_final_manifest_df(
        df,
        download_dir=download_dir,
        require_wsi_on_disk=require_wsi_on_disk,
        require_split_assigned=require_split_assigned,
    )


def main() -> None:
    import argparse

    from pathosurv.config import data_config

    parser = argparse.ArgumentParser(description="Validate final_manifest.csv")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--require-wsi", action="store_true")
    parser.add_argument("--require-split", action="store_true")
    args = parser.parse_args()

    cfg = data_config()
    path = args.manifest or Path(cfg["final_manifest_path"])
    errors = validate_final_manifest_file(
        path,
        download_dir=Path(cfg["wsi_download_dir"]),
        require_wsi_on_disk=args.require_wsi,
        require_split_assigned=args.require_split,
    )
    if errors:
        for err in errors:
            logging.error("%s", err)
        raise SystemExit(1)
    logging.info("Final manifest OK: %s", path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
