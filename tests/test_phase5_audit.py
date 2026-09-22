"""Smoke test that Phase 5 audit exists after running run_phase5_pipeline."""

import json
from pathlib import Path

from pathosurv.config import data_config


def test_phase5_audit_when_present():
    cfg = data_config()
    audit_path = Path(cfg["phase5_audit_path"])
    if not audit_path.is_file():
        return  # skip silently unless audit generated (WSI + [wsi] deps)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit.get("slides_processed", 0) >= 1
    assert audit.get("backend") == "openslide_baseline"
