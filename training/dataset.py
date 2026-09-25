"""Slide-level embedding bags for survival training."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import torch


def feature_path(features_dir: Path, slide_id: str) -> Path:
    return features_dir / f"{slide_id}.pt"


def list_available_slides(manifest_path: Path, features_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(manifest_path)
    rows = []
    for _, row in df.iterrows():
        sid = str(row["slide_id"])
        fp = feature_path(features_dir, sid)
        if fp.is_file():
            rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)


class SurvivalBagDataset:
    def __init__(
        self,
        manifest_path: Path,
        features_dir: Path,
        *,
        split: str | None = None,
    ) -> None:
        df = list_available_slides(manifest_path, features_dir)
        if split is not None:
            df = df[df["split"].astype(str) == split].reset_index(drop=True)
        self.df = df
        self.features_dir = features_dir

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, index: int) -> dict:
        row = self.df.iloc[index]
        return {
            "slide_id": str(row["slide_id"]),
            "case_id": str(row["case_id"]),
            "time": float(row["survival_time_days"]),
            "event": int(row["event_status"]),
            "feature_path": str(feature_path(self.features_dir, row["slide_id"])),
        }


def load_bag(item: dict) -> dict:
    data = torch.load(item["feature_path"], map_location="cpu", weights_only=False)
    return {
        **item,
        "embeddings": data["embeddings"],
        "coordinates": data.get("coordinates"),
    }
