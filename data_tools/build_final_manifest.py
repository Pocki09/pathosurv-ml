"""Build final_manifest.csv (one diagnostic WSI per patient) and dataset audit."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data_tools.slide_selection import slide_selection_rank
from data_tools.validate_final_manifest import (
    FINAL_MANIFEST_COLUMNS,
    validate_final_manifest_df,
)
from data_tools.wsi_paths import wsi_path_for_manifest
from pathosurv.config import data_config, load_yaml
from pathosurv.paths import project_root

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def select_one_slide_per_case(matched: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Return selected rows and audit entries for excluded slides."""
    excluded: list[dict] = []
    selected_rows: list[pd.Series] = []

    for case_id, group in matched.groupby("case_id", sort=False):
        group = group.copy()
        group["_rank"] = group["slide_id"].map(slide_selection_rank)
        group = group.sort_values("_rank")
        chosen = group.iloc[0]
        selected_rows.append(chosen)
        for _, row in group.iloc[1:].iterrows():
            excluded.append(
                {
                    "case_id": case_id,
                    "slide_id": row["slide_id"],
                    "filename": row["filename"],
                    "reason": "duplicate_patient_not_selected",
                    "selected_slide_id": chosen["slide_id"],
                }
            )

    selected = pd.DataFrame(selected_rows).drop(columns=["_rank"], errors="ignore")
    return selected, excluded


def build_final_manifest(
    matched_path: Path,
    download_dir: Path,
    *,
    base: Path | None = None,
) -> pd.DataFrame:
    matched = pd.read_csv(matched_path)
    selected, _ = select_one_slide_per_case(matched)
    root = base or project_root()

    records = []
    for _, row in selected.iterrows():
        records.append(
            {
                "case_id": row["case_id"],
                "slide_id": row["slide_id"],
                "wsi_path": wsi_path_for_manifest(
                    download_dir,
                    str(row["id"]),
                    str(row["filename"]),
                    base=root,
                ),
                "survival_time_days": float(row["OS_time"]),
                "event_status": int(row["OS_event"]),
                "split": "",
            }
        )
    return pd.DataFrame(records, columns=list(FINAL_MANIFEST_COLUMNS))


def build_dataset_audit(
    matched_path: Path,
    final_df: pd.DataFrame,
    excluded: list[dict],
    validation_errors: list[str],
    cohort: str,
) -> dict:
    matched = pd.read_csv(matched_path)
    events = int(final_df["event_status"].sum()) if len(final_df) else 0
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cohort": cohort,
        "endpoint": load_yaml("project.yaml").get("endpoint"),
        "input_matched_rows": len(matched),
        "final_manifest_rows": len(final_df),
        "unique_cases": int(final_df["case_id"].nunique()) if len(final_df) else 0,
        "event_count": events,
        "censored_count": int((final_df["event_status"] == 0).sum()) if len(final_df) else 0,
        "excluded_count": len(excluded),
        "excluded": excluded,
        "validation": {"ok": len(validation_errors) == 0, "errors": validation_errors},
        "notes": [
            "One diagnostic WSI per case_id (see slide_selection.py).",
            "split is empty until patient-level splits are assigned.",
            "wsi_path may not exist on disk until WSI download completes.",
        ],
    }


def run_build(
    matched_path: Path,
    download_dir: Path,
    final_path: Path,
    audit_path: Path,
    cohort: str,
) -> dict:
    matched = pd.read_csv(matched_path)
    selected, excluded = select_one_slide_per_case(matched)
    final_df = build_final_manifest(matched_path, download_dir)
    errors = validate_final_manifest_df(final_df, require_wsi_on_disk=False)

    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(final_path, index=False)
    audit = build_dataset_audit(matched_path, final_df, excluded, errors, cohort)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    if errors:
        logger.error("Final manifest validation failed: %s", errors)
        raise SystemExit(1)

    logger.info(
        "Wrote %s (%d rows, %d excluded) → audit %s",
        final_path,
        len(final_df),
        len(excluded),
        audit_path,
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build final survival manifest (one slide per patient)")
    parser.add_argument("--matched", type=Path)
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()

    cfg = data_config()
    matched_path = args.matched or Path(cfg["matched_cohort_path"])
    download_dir = args.download_dir or Path(cfg["wsi_download_dir"])
    final_path = args.output or Path(cfg["final_manifest_path"])
    audit_path = args.audit or Path(cfg["dataset_audit_path"])

    run_build(
        matched_path,
        download_dir,
        final_path,
        audit_path,
        str(cfg.get("cohort", "")),
    )


if __name__ == "__main__":
    main()
