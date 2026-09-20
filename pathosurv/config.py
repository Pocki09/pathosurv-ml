"""Load YAML configuration relative to the repository root."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pathosurv.paths import project_root, resolve_path


def load_yaml(name: str) -> dict[str, Any]:
    path = project_root() / "configs" / name
    if not path.is_file():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def data_config() -> dict[str, Any]:
    cfg = load_yaml("data.yaml")
    resolved: dict[str, Any] = {}
    for key, value in cfg.items():
        if key.endswith("_path") or key.endswith("_dir") or key in (
            "manifest_path",
            "clinical_path",
            "output_csv",
            "matched_cohort_path",
            "final_manifest_path",
            "dataset_audit_path",
            "wsi_manifest_path",
            "wsi_download_dir",
            "subset_manifest_path",
            "download_audit_path",
            "manifest_registry_path",
        ):
            if isinstance(value, str):
                resolved[key] = str(resolve_path(value))
            else:
                resolved[key] = value
        else:
            resolved[key] = value
    return resolved
