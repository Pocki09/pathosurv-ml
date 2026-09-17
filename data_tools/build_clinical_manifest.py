"""
Build patient-level clinical table with overall survival fields from GDC Cases JSON.

Phase 2: produces ``processed_metadata.csv`` with OS_time / OS_event for merging with WSI.
Phase 3 will rename columns to survival_time_days / event_status in final_manifest.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from pathosurv.config import data_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_clinical_json(json_path: Path) -> pd.DataFrame:
    logger.info("Reading clinical data from %s", json_path)
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected top-level JSON array of cases")

    records: list[dict] = []
    skipped = 0
    for case in data:
        case_id = case.get("case_id")
        submitter_id = case.get("submitter_id")
        demographic = case.get("demographic") or {}
        vital_status = demographic.get("vital_status")

        diagnoses = case.get("diagnoses") or []
        if not diagnoses:
            skipped += 1
            continue

        diag = next(
            (d for d in diagnoses if d.get("diagnosis_is_primary_disease") == "true"),
            diagnoses[0],
        )

        # GDC stores days_to_death on demographic; follow-up often on primary diagnosis
        if vital_status == "Dead":
            raw_time = demographic.get("days_to_death")
            if raw_time is None:
                raw_time = diag.get("days_to_death")
            event = 1
        elif vital_status == "Alive":
            raw_time = diag.get("days_to_last_follow_up")
            if raw_time is None:
                raw_time = demographic.get("days_to_last_follow_up")
            event = 0
        else:
            skipped += 1
            continue

        if raw_time is None:
            skipped += 1
            continue
        time = float(raw_time)

        if time <= 0:
            skipped += 1
            continue

        records.append(
            {
                "case_id": case_id,
                "submitter_id": submitter_id,
                "OS_time": time,
                "OS_event": event,
                "vital_status": vital_status,
            }
        )

    df = pd.DataFrame(records)
    logger.info("Parsed %d survival rows (%d cases skipped)", len(df), skipped)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Build clinical manifest from GDC JSON")
    parser.add_argument("--clinical", type=Path, help="Override clinical JSON path")
    parser.add_argument("--output", type=Path, help="Override output CSV path")
    args = parser.parse_args()

    cfg = data_config()
    clinical_path = args.clinical or Path(cfg["clinical_path"])
    output_path = args.output or Path(cfg["output_csv"])

    df = parse_clinical_json(clinical_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("Wrote %s (%d rows)", output_path, len(df))


if __name__ == "__main__":
    main()
