"""Generate synthetic embedding bags for pipeline smoke without full WSI cohort."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from pathosurv.seed import set_seed


def write_synthetic_demo_dataset(
    output_manifest: Path,
    features_dir: Path,
    *,
    n_cases: int = 40,
    embedding_dim: int = 1024,
    seed: int = 42,
) -> Path:
    set_seed(seed)
    features_dir.mkdir(parents=True, exist_ok=True)
    records = []
    splits = (["train"] * 28) + (["validation"] * 6) + (["test"] * 6)
    for i in range(n_cases):
        case_id = f"synthetic-case-{i:03d}"
        slide_id = f"SYN-{i:03d}"
        event = 1 if i % 3 != 0 else 0
        time = float(100 + i * 17 + (10 if event else 200))
        n_patches = int(np.random.randint(20, 80))
        emb = torch.randn(n_patches, embedding_dim)
        torch.save(
            {
                "embeddings": emb,
                "coordinates": torch.zeros(n_patches, 2),
                "slide_id": slide_id,
                "encoder_id": "synthetic_demo",
            },
            features_dir / f"{slide_id}.pt",
        )
        records.append(
            {
                "case_id": case_id,
                "slide_id": slide_id,
                "wsi_path": f"synthetic/{slide_id}.svs",
                "survival_time_days": time,
                "event_status": event,
                "split": splits[i],
            }
        )
    df = pd.DataFrame(records)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_manifest, index=False)
    meta = {"n_cases": n_cases, "embedding_dim": embedding_dim, "seed": seed}
    (features_dir / "synthetic_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return output_manifest
