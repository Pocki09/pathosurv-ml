from pathlib import Path

import pandas as pd

from data_tools.gdc_manifest import filter_wsi_rows, read_gdc_manifest
from data_tools.validate_manifest import (
    validate_clinical_csv,
    validate_gdc_manifest,
    validate_matched_cohort,
)
from pathosurv.config import data_config
from pathosurv.paths import project_root


def test_gdc_manifest_in_repo():
    cfg = data_config()
    path = Path(cfg["manifest_path"])
    assert path.is_file()
    assert validate_gdc_manifest(path) == []


def test_clinical_csv_valid():
    cfg = data_config()
    path = Path(cfg["output_csv"])
    assert path.is_file()
    assert validate_clinical_csv(path) == []
    df = pd.read_csv(path)
    assert df["OS_event"].sum() > 0, "expected at least one OS event in TCGA-BLCA clinical export"


def test_matched_cohort_valid():
    cfg = data_config()
    path = Path(cfg["matched_cohort_path"])
    assert path.is_file()
    assert validate_matched_cohort(path) == []


def test_wsi_filter_extracts_submitter_id():
    cfg = data_config()
    mdf = read_gdc_manifest(cfg["manifest_path"])
    wsi = filter_wsi_rows(mdf)
    assert len(wsi) > 0
    sample = wsi.iloc[0]
    assert sample["submitter_id"].startswith("TCGA-")


def test_matched_cohort_has_survival_columns():
    cfg = data_config()
    df = pd.read_csv(cfg["matched_cohort_path"])
    assert (df["OS_time"] > 0).all()
    assert set(df["OS_event"].unique()).issubset({0, 1})
