"""Evaluate checkpoint on a split."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from evaluation.concordance import harrell_c_index
from models.attention_mil import AttentionMILCox
from models.mean_pooling_cox import MeanPoolingCox
from pathosurv.config import data_config, load_yaml
from training.dataset import SurvivalBagDataset, load_bag


def build_model(name: str, embedding_dim: int) -> torch.nn.Module:
    mcfg = load_yaml("model.yaml")
    if name == "mean_pooling_cox":
        return MeanPoolingCox(embedding_dim)
    if name == "attention_mil_cox":
        hidden = int(mcfg.get("attention_hidden_dim", 256))
        return AttentionMILCox(embedding_dim, hidden_dim=hidden)
    raise ValueError(name)


@torch.inference_mode()
def predict_split(
    model: torch.nn.Module,
    dataset: SurvivalBagDataset,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    risks, times, events = [], [], []
    model.eval()
    for i in range(len(dataset)):
        bag = load_bag(dataset[i])
        emb = bag["embeddings"].to(device)
        risk, _ = model(emb)
        risks.append(float(risk.cpu()))
        times.append(float(bag["time"]))
        events.append(int(bag["event"]))
    return np.array(risks), np.array(times), np.array(events)


def evaluate_checkpoint(
    checkpoint_path: Path,
    manifest_path: Path,
    features_dir: Path,
    split: str,
) -> dict:
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model_name = ckpt["model_name"]
    dim = int(ckpt["embedding_dim"])
    model = build_model(model_name, dim)
    model.load_state_dict(ckpt["state_dict"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    ds = SurvivalBagDataset(manifest_path, features_dir, split=split)
    risk, time, event = predict_split(model, ds, device)
    c_index = harrell_c_index(event, time, risk) if len(ds) > 1 else float("nan")
    return {
        "split": split,
        "model_name": model_name,
        "case_count": len(ds),
        "event_count": int(event.sum()),
        "c_index": c_index,
    }


def resolve_manifest(explicit: Path | None) -> Path:
    cfg = data_config()
    if explicit and explicit.is_file():
        return explicit
    synthetic = Path(cfg["features_dir"]) / "synthetic_manifest.csv"
    if synthetic.is_file():
        return synthetic
    return Path(cfg["final_manifest_path"])


def main() -> None:
    import argparse
    from pathosurv.config import data_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--split", default="test")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cfg = data_config()
    manifest = resolve_manifest(args.manifest)
    result = evaluate_checkpoint(
        args.checkpoint,
        manifest,
        Path(cfg["features_dir"]),
        args.split,
    )
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
