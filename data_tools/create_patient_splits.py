"""Fixed patient-level train / validation / test splits for final_manifest.csv."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from data_tools.validate_final_manifest import validate_final_manifest_df
from pathosurv.config import data_config, load_yaml
from pathosurv.seed import set_seed

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SPLIT_NAMES = ("train", "validation", "test")


def _split_summary(df: pd.DataFrame, split_name: str) -> dict:
    part = df[df["split"] == split_name]
    events = int(part["event_status"].sum())
    return {
        "case_count": len(part),
        "event_count": events,
        "censored_count": int((part["event_status"] == 0).sum()),
        "case_ids": part["case_id"].astype(str).tolist(),
    }


def assign_patient_splits(
    df: pd.DataFrame,
    *,
    seed: int,
    test_ratio: float,
    validation_ratio: float,
) -> pd.DataFrame:
    if df["case_id"].duplicated().any():
        raise ValueError("final_manifest must have one row per case_id before splitting")
    if not 0 < test_ratio < 1 or not 0 < validation_ratio < 1:
        raise ValueError("split ratios must be between 0 and 1")
    if test_ratio + validation_ratio >= 1:
        raise ValueError("test_ratio + validation_ratio must be < 1")

    out = df.copy()
    out["split"] = ""  # ensure object column (empty CSV cells may load as NaN/float)
    stratify = out["event_status"]
    train_val, test = train_test_split(
        out,
        test_size=test_ratio,
        random_state=seed,
        stratify=stratify,
    )
    val_share_of_train_val = validation_ratio / (1.0 - test_ratio)
    train, validation = train_test_split(
        train_val,
        test_size=val_share_of_train_val,
        random_state=seed,
        stratify=train_val["event_status"],
    )

    for part, name in ((train, "train"), (validation, "validation"), (test, "test")):
        out.loc[part.index, "split"] = name

    if out["split"].astype(str).str.strip().eq("").any():
        raise RuntimeError("Some rows were not assigned a split")
    return out


def build_splits_report(
    df: pd.DataFrame,
    *,
    seed: int,
    test_ratio: float,
    validation_ratio: float,
    cohort: str,
) -> dict:
    train_ratio = 1.0 - test_ratio - validation_ratio
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cohort": cohort,
        "seed": seed,
        "ratios": {
            "train": train_ratio,
            "validation": validation_ratio,
            "test": test_ratio,
        },
        "total_cases": len(df),
        "splits": {name: _split_summary(df, name) for name in SPLIT_NAMES},
        "notes": [
            "Patient-level split; one row per case_id in final_manifest.",
            "Stratified on event_status; fixed seed for reproducibility.",
        ],
    }


def run_create_splits(
    final_path: Path,
    splits_path: Path,
    *,
    seed: int,
    test_ratio: float,
    validation_ratio: float,
    cohort: str,
) -> dict:
    df = pd.read_csv(final_path)
    df["split"] = ""

    set_seed(seed)
    assigned = assign_patient_splits(
        df,
        seed=seed,
        test_ratio=test_ratio,
        validation_ratio=validation_ratio,
    )
    errors = validate_final_manifest_df(assigned, require_split_assigned=True)
    if errors:
        raise ValueError(f"Split assignment failed validation: {errors}")

    report = build_splits_report(
        assigned,
        seed=seed,
        test_ratio=test_ratio,
        validation_ratio=validation_ratio,
        cohort=cohort,
    )
    final_path.parent.mkdir(parents=True, exist_ok=True)
    assigned.to_csv(final_path, index=False)
    splits_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info(
        "Wrote splits → %s; updated %s (train=%d, validation=%d, test=%d)",
        splits_path,
        final_path,
        report["splits"]["train"]["case_count"],
        report["splits"]["validation"]["case_count"],
        report["splits"]["test"]["case_count"],
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Create patient-level train/val/test splits")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--splits", type=Path)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    cfg = data_config()
    training = load_yaml("training.yaml")
    split_cfg = training.get("split") or {}

    seed = args.seed if args.seed is not None else int(cfg.get("random_seed", 42))
    test_ratio = float(split_cfg.get("test_ratio", 0.15))
    validation_ratio = float(split_cfg.get("validation_ratio", 0.15))

    final_path = args.manifest or Path(cfg["final_manifest_path"])
    splits_path = args.splits or Path(cfg["splits_path"])

    run_create_splits(
        final_path,
        splits_path,
        seed=seed,
        test_ratio=test_ratio,
        validation_ratio=validation_ratio,
        cohort=str(cfg.get("cohort", "")),
    )


if __name__ == "__main__":
    main()
