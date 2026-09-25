"""Train Mean Pooling + Cox or Attention MIL + Cox on precomputed embeddings."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from evaluation.concordance import harrell_c_index
from losses.cox_ph_loss import cox_ph_loss
from models.attention_mil import AttentionMILCox
from models.mean_pooling_cox import MeanPoolingCox
from pathosurv.config import data_config, load_yaml
from pathosurv.seed import set_seed
from training.checkpoint import save_checkpoint
from training.dataset import SurvivalBagDataset, load_bag
from training.early_stopping import EarlyStopping
from training.synthetic_demo import write_synthetic_demo_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def collate_bags(batch: list) -> list:
    return batch


def build_model(name: str, dim: int) -> torch.nn.Module:
    mcfg = load_yaml("model.yaml")
    if name == "mean_pooling_cox":
        return MeanPoolingCox(dim)
    if name == "attention_mil_cox":
        return AttentionMILCox(dim, hidden_dim=int(mcfg.get("attention_hidden_dim", 256)))
    raise ValueError(name)


def run_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    *,
    train: bool,
) -> float:
    if train:
        model.train()
    else:
        model.eval()
    losses = []
    for batch in loader:
        if train:
            optimizer.zero_grad()
        risks, times, events = [], [], []
        with torch.set_grad_enabled(train):
            for item in batch:
                bag = load_bag(item)
                risk, _ = model(bag["embeddings"].to(device))
                risks.append(risk)
                times.append(bag["time"])
                events.append(bag["event"])
            risk_t = torch.stack(risks)
            time_t = torch.tensor(times, dtype=torch.float32, device=device)
            event_t = torch.tensor(events, dtype=torch.float32, device=device)
            if event_t.sum() <= 0:
                continue
            loss = cox_ph_loss(risk_t, time_t, event_t)
            if train:
                loss.backward()
                optimizer.step()
            losses.append(float(loss.detach().cpu()))
    return float(np.mean(losses)) if losses else float("nan")


@torch.inference_mode()
def split_c_index(
    model: torch.nn.Module,
    dataset: SurvivalBagDataset,
    device: torch.device,
) -> float:
    if len(dataset) < 2:
        return float("nan")
    risks, times, events = [], [], []
    model.eval()
    for i in range(len(dataset)):
        bag = load_bag(dataset[i])
        risk, _ = model(bag["embeddings"].to(device))
        risks.append(float(risk.cpu()))
        times.append(bag["time"])
        events.append(bag["event"])
    return harrell_c_index(np.array(events), np.array(times), np.array(risks))


def train_model(
    *,
    model_name: str,
    manifest_path: Path,
    features_dir: Path,
    checkpoints_dir: Path,
    tcfg: dict,
) -> Path:
    set_seed(int(tcfg.get("seed", 42)))
    mcfg = load_yaml("model.yaml")
    dim = int(mcfg["embedding_dim"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(model_name, dim).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(tcfg.get("learning_rate", 1e-4)),
        weight_decay=float(tcfg.get("weight_decay", 1e-4)),
    )

    train_ds = SurvivalBagDataset(manifest_path, features_dir, split="train")
    val_ds = SurvivalBagDataset(manifest_path, features_dir, split="validation")
    if len(train_ds) == 0:
        raise ValueError("No training cases with embedding files — run extract_embeddings or --synthetic-demo")

    train_loader = DataLoader(
        train_ds,
        batch_size=int(tcfg.get("batch_size", 8)),
        shuffle=True,
        collate_fn=collate_bags,
    )
    val_loader = DataLoader(val_ds, batch_size=int(tcfg.get("batch_size", 8)), collate_fn=collate_bags)

    early = EarlyStopping(patience=int(tcfg.get("patience", 15)))
    best_path = checkpoints_dir / f"{model_name}_best.pt"
    max_epochs = int(tcfg.get("max_epochs", 100))

    for epoch in range(1, max_epochs + 1):
        train_loss = run_epoch(model, train_loader, optimizer, device, train=True)
        _ = run_epoch(model, val_loader, optimizer, device, train=False)
        val_ci = split_c_index(model, val_ds, device)
        logger.info("epoch %d train_loss=%.4f val_c_index=%.4f", epoch, train_loss, val_ci)
        if not np.isnan(val_ci) and early.step(val_ci):
            payload = {
                "model_name": model_name,
                "embedding_dim": dim,
                "state_dict": model.state_dict(),
                "epoch": epoch,
                "val_c_index": val_ci,
                "encoder_id": load_yaml("encoder.yaml").get("fallback_encoder_id"),
            }
            save_checkpoint(best_path, payload)
        if early.should_stop:
            logger.info("Early stopping at epoch %d", epoch)
            break

    if not best_path.is_file():
        payload = {
            "model_name": model_name,
            "embedding_dim": dim,
            "state_dict": model.state_dict(),
            "epoch": max_epochs,
            "val_c_index": float("nan"),
            "encoder_id": load_yaml("encoder.yaml").get("fallback_encoder_id"),
        }
        save_checkpoint(best_path, payload)
    return best_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["mean_pooling_cox", "attention_mil_cox"], required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--synthetic-demo", action="store_true")
    args = parser.parse_args()

    cfg = data_config()
    tcfg = load_yaml("training.yaml")
    manifest = args.manifest or Path(cfg["final_manifest_path"])
    features_dir = Path(cfg["features_dir"])
    checkpoints_dir = Path(cfg["checkpoints_dir"])

    if args.synthetic_demo:
        demo_manifest = Path(cfg["features_dir"]) / "synthetic_manifest.csv"
        write_synthetic_demo_dataset(demo_manifest, features_dir, embedding_dim=int(load_yaml("model.yaml")["embedding_dim"]))
        manifest = demo_manifest

    path = train_model(
        model_name=args.model,
        manifest_path=manifest,
        features_dir=features_dir,
        checkpoints_dir=checkpoints_dir,
        tcfg=tcfg,
    )
    logger.info("Best checkpoint: %s", path)


if __name__ == "__main__":
    main()
