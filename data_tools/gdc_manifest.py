"""Shared helpers for GDC tab-separated manifest files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

GDC_MANIFEST_COLUMNS = ("id", "filename", "md5", "size", "state")


def read_gdc_manifest(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"GDC manifest not found: {path}")
    df = pd.read_csv(path, sep="\t", dtype={"size": "Int64"})
    missing = [c for c in GDC_MANIFEST_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Manifest {path} missing columns: {missing}")
    return df


def filter_wsi_rows(manifest_df: pd.DataFrame) -> pd.DataFrame:
    wsi = manifest_df[manifest_df["filename"].str.endswith(".svs", na=False)].copy()
    wsi["submitter_id"] = wsi["filename"].map(_submitter_id_from_filename)
    wsi["slide_id"] = wsi["filename"].map(_slide_id_from_filename)
    return wsi


def _submitter_id_from_filename(filename: str) -> str | None:
    if not isinstance(filename, str) or not filename.startswith("TCGA"):
        return None
    parts = filename.split("-")
    if len(parts) < 3:
        return None
    return "-".join(parts[:3])


def _slide_id_from_filename(filename: str) -> str:
    """Stable slide identifier: TCGA barcode prefix before first dot."""
    if not isinstance(filename, str):
        return ""
    return filename.split(".")[0]
