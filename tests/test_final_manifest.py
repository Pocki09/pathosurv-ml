"""Unit tests for slide selection and final manifest validation."""

import pandas as pd

from data_tools.create_patient_splits import assign_patient_splits
from data_tools.build_final_manifest import select_one_slide_per_case
from data_tools.slide_selection import slide_selection_rank
from data_tools.validate_final_manifest import validate_final_manifest_df


def test_slide_rank_prefers_dx1_over_recurrence():
    dx = slide_selection_rank("TCGA-XX-1234-01Z-00-DX1")
    bs = slide_selection_rank("TCGA-XX-1234-01A-02-BS2")
    assert dx < bs


def test_select_one_slide_per_case():
    matched = pd.DataFrame(
        [
            {
                "case_id": "c1",
                "slide_id": "TCGA-AB-1234-01A-02-BS2",
                "id": "a",
                "filename": "a.svs",
                "OS_time": 100.0,
                "OS_event": 1,
            },
            {
                "case_id": "c1",
                "slide_id": "TCGA-AB-1234-01Z-00-DX1",
                "id": "b",
                "filename": "b.svs",
                "OS_time": 100.0,
                "OS_event": 1,
            },
        ]
    )
    selected, excluded = select_one_slide_per_case(matched)
    assert len(selected) == 1
    assert selected.iloc[0]["slide_id"].endswith("DX1")
    assert len(excluded) == 1
    assert excluded[0]["reason"] == "duplicate_patient_not_selected"


def test_validate_final_manifest_rejects_bad_event():
    df = pd.DataFrame(
        [
            {
                "case_id": "c1",
                "slide_id": "s1",
                "wsi_path": "data/raw_slides/x/a.svs",
                "survival_time_days": 10.0,
                "event_status": 2,
                "split": "",
            }
        ]
    )
    errors = validate_final_manifest_df(df)
    assert any("event_status" in e for e in errors)


def test_patient_splits_reproducible_and_cover_all_cases():
    df = pd.DataFrame(
        {
            "case_id": [f"c{i}" for i in range(40)],
            "slide_id": [f"s{i}" for i in range(40)],
            "wsi_path": [f"p{i}.svs" for i in range(40)],
            "survival_time_days": [100.0] * 40,
            "event_status": [i % 2 for i in range(40)],
            "split": [""] * 40,
        }
    )
    a = assign_patient_splits(df, seed=42, test_ratio=0.15, validation_ratio=0.15)
    b = assign_patient_splits(df, seed=42, test_ratio=0.15, validation_ratio=0.15)
    assert a["split"].tolist() == b["split"].tolist()
    assert set(a["split"]) == {"train", "validation", "test"}
    assert a["case_id"].nunique() == len(a)
    assert validate_final_manifest_df(a, require_split_assigned=True) == []
