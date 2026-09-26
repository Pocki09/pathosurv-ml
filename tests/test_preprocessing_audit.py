"""Smoke test that WSI preprocessing audit exists after running run_wsi_preprocess_pipeline."""

from pathlib import Path

import pytest

from pathosurv.config import data_config


def test_wsi_preprocessing_audit_when_present():
    cfg = data_config()
    audit_path = Path(cfg["wsi_preprocessing_audit_path"])
    if not audit_path.is_file():
        pytest.skip("no preprocessing audit on disk")
    assert audit_path.stat().st_size > 0
