"""Extract patch embeddings from Phase 5 patch_coordinates + local WSI."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import torch
from PIL import Image
from torchvision import transforms

from data_tools.wsi_paths import resolve_wsi_file
from models.encoder import encode_patches, load_encoder
from pathosurv.config import data_config, load_yaml
from preprocessing.wsi_preprocess import load_preprocessing_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def preprocessing_hash(cfg_path: str = "configs/preprocessing.yaml") -> str:
    raw = (Path(__file__).resolve().parent.parent / "configs" / "preprocessing.yaml").read_bytes()
    return hashlib.sha256(raw).hexdigest()[:16]


def read_patch_tensor(slide, row, max_read_size: int) -> torch.Tensor | None:
    import openslide

    x, y = int(row["x"]), int(row["y"])
    level = int(row["level"])
    read_size = int(row.get("read_size_at_level", row["patch_size"]))
    read_size = min(read_size, max_read_size)
    tile = slide.read_region((x, y), level, (read_size, read_size)).convert("RGB")
    return transforms.functional.pil_to_tensor(tile)


def extract_slide(
    slide_path: Path,
    patch_csv: Path,
    output_path: Path,
    *,
    batch_size: int = 16,
    max_patches: int | None = 100,
) -> dict:
    import openslide

    model, info = load_encoder()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    df = pd.read_csv(patch_csv)
    accepted = df[df["status"] == "accepted"]
    if max_patches:
        accepted = accepted.head(max_patches)
    slide = openslide.OpenSlide(str(slide_path))
    embeddings_list = []
    coords_list = []
    try:
        batch_tensors = []
        batch_coords = []
        for _, row in accepted.iterrows():
            t = read_patch_tensor(slide, row, max_read_size=512)
            if t is None:
                continue
            pil = transforms.functional.to_pil_image(t)
            pil = info.transform(pil)
            batch_tensors.append(pil)
            batch_coords.append([int(row["x"]), int(row["y"])])
            if len(batch_tensors) >= batch_size:
                batch = torch.stack(batch_tensors)
                emb = encode_patches(model, info, batch)
                embeddings_list.append(emb.cpu())
                coords_list.extend(batch_coords)
                batch_tensors, batch_coords = [], []
        if batch_tensors:
            batch = torch.stack(batch_tensors)
            emb = encode_patches(model, info, batch)
            embeddings_list.append(emb.cpu())
            coords_list.extend(batch_coords)
    finally:
        slide.close()

    if not embeddings_list:
        raise ValueError(f"No embeddings extracted for {slide_path}")
    embeddings = torch.cat(embeddings_list, dim=0)
    coordinates = torch.tensor(coords_list, dtype=torch.long)
    payload = {
        "embeddings": embeddings,
        "coordinates": coordinates,
        "slide_id": patch_csv.parent.name,
        "encoder_id": info.encoder_id,
        "encoder_version": info.encoder_version,
        "preprocessing_hash": preprocessing_hash(),
        "patch_count": int(embeddings.shape[0]),
        "embedding_dim": int(embeddings.shape[1]),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, output_path)
    return payload


def run_extraction(
    *,
    preprocessed_dir: Path,
    download_dir: Path,
    features_dir: Path,
    subset_manifest: Path,
    max_patches: int | None,
) -> dict:
    subset = pd.read_csv(subset_manifest, sep="\t")
    slides = []
    errors = []
    for _, row in subset.iterrows():
        fid, fn = str(row["id"]), str(row["filename"])
        slide_id = fn.split(".")[0]
        slide_dir = preprocessed_dir / slide_id
        patch_csv = slide_dir / "patch_coordinates.csv"
        if not patch_csv.is_file():
            errors.append(f"missing patch csv: {slide_id}")
            continue
        wsi = resolve_wsi_file(download_dir, fid, fn)
        if wsi is None:
            errors.append(f"missing wsi: {fn}")
            continue
        out = features_dir / f"{slide_id}.pt"
        try:
            meta = extract_slide(wsi, patch_csv, out, max_patches=max_patches)
            slides.append({"slide_id": slide_id, **meta, "path": str(out)})
            logger.info("Saved %s (%d patches, D=%d)", out, meta["patch_count"], meta["embedding_dim"])
        except Exception as exc:
            errors.append(f"{slide_id}: {exc}")

    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "slides": slides,
        "errors": errors,
        "ok": len(slides) >= 1 and not errors,
    }
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-patches", type=int, default=100)
    args = parser.parse_args()
    cfg = data_config()
    pre = load_preprocessing_config()
    audit = run_extraction(
        preprocessed_dir=Path(cfg["preprocessed_dir"]),
        download_dir=Path(cfg["wsi_download_dir"]),
        features_dir=Path(cfg["features_dir"]),
        subset_manifest=Path(cfg["subset_manifest_path"]),
        max_patches=args.max_patches or pre.max_patches_per_slide,
    )
    out = Path(cfg["embedding_audit_path"])
    out.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    if not audit["ok"]:
        raise SystemExit(1)
    logger.info("Embedding audit: %s", out)


if __name__ == "__main__":
    main()
