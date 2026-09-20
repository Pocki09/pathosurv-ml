"""Unit tests for slide selection and final manifest validation."""

import pandas as pd

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
