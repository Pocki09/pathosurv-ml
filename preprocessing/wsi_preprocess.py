"""OpenSlide + OpenCV WSI preprocessing baseline."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
from PIL import Image

from data_tools.wsi_paths import resolve_wsi_file
from pathosurv.config import load_yaml

logger = logging.getLogger(__name__)


@dataclass
class PreprocessConfig:
    backend: str
    patch_size: int
    stride: int
    target_magnification: int
    tissue_downsample: int
    tissue_saturation_min: int
    tissue_value_max: int
    morph_kernel: int
    max_white_fraction: float
    min_tissue_fraction: float
    max_patches_per_slide: int
    max_slides: int
    output_subdir: str

    @classmethod
    def from_yaml(cls, name: str = "preprocessing.yaml") -> PreprocessConfig:
        raw = load_yaml(name)
        return cls(
            backend=str(raw.get("backend", "openslide_baseline")),
            patch_size=int(raw["patch_size"]),
            stride=int(raw["stride"]),
            target_magnification=int(raw.get("target_magnification", 20)),
            tissue_downsample=int(raw.get("tissue_downsample", 32)),
            tissue_saturation_min=int(raw.get("tissue_saturation_min", 20)),
            tissue_value_max=int(raw.get("tissue_value_max", 240)),
            morph_kernel=int(raw.get("morph_kernel", 5)),
            max_white_fraction=float(raw.get("max_white_fraction", 0.85)),
            min_tissue_fraction=float(raw.get("min_tissue_fraction", 0.15)),
            max_patches_per_slide=int(raw.get("max_patches_per_slide", 200)),
            max_slides=int(raw.get("max_slides", 3)),
            output_subdir=str(raw.get("output_subdir", "preprocessed")),
        )


def load_preprocessing_config() -> PreprocessConfig:
    return PreprocessConfig.from_yaml()


def rgb_white_fraction(tile: np.ndarray) -> float:
    """Fraction of near-white pixels (RGB all > 220)."""
    if tile.size == 0:
        return 1.0
    white = np.all(tile > 220, axis=-1)
    return float(white.mean())


def tissue_mask_from_rgb(rgb: np.ndarray, cfg: PreprocessConfig) -> np.ndarray:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    mask = (sat >= cfg.tissue_saturation_min) & (val <= cfg.tissue_value_max)
    mask_u8 = (mask.astype(np.uint8)) * 255
    k = max(1, cfg.morph_kernel)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, kernel)
    mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, kernel)
    return mask_u8


def choose_read_level(slide, target_mag: int) -> tuple[int, float]:
    """Return (level, scale) where scale multiplies level-0 coords to read at chosen level."""
    objective = slide.properties.get("openslide.objective-power")
    try:
        obj = float(objective)
    except (TypeError, ValueError):
        return 0, 1.0
    if obj <= 0:
        return 0, 1.0
    desired_downsample = obj / float(target_mag)
    best_level = 0
    best_diff = float("inf")
    for level in range(slide.level_count):
        ds = slide.level_downsamples[level]
        diff = abs(ds - desired_downsample)
        if diff < best_diff:
            best_diff = diff
            best_level = level
    ds = slide.level_downsamples[best_level]
    scale = ds  # level-0 pixel = scale * level pixel at read level
    return best_level, scale


def process_one_slide(
    slide_path: Path,
    output_dir: Path,
    cfg: PreprocessConfig,
    *,
    slide_id: str,
    case_id: str | None = None,
) -> dict[str, Any]:
    import openslide

    output_dir.mkdir(parents=True, exist_ok=True)
    slide = openslide.OpenSlide(str(slide_path))
    try:
        w0, h0 = slide.dimensions
        thumb_level = slide.get_best_level_for_downsample(cfg.tissue_downsample)
        tw, th = slide.level_dimensions[thumb_level]
        thumb_rgb = np.array(slide.read_region((0, 0), thumb_level, (tw, th)).convert("RGB"))
        mask_thumb = tissue_mask_from_rgb(thumb_rgb, cfg)
        Image.fromarray(thumb_rgb).save(output_dir / "thumbnail.jpg", quality=90)
        Image.fromarray(mask_thumb).save(output_dir / "tissue_mask.png")

        read_level, scale = choose_read_level(slide, cfg.target_magnification)
        patch_at_level = max(1, int(round(cfg.patch_size / scale)))

        scale_x = w0 / mask_thumb.shape[1]
        scale_y = h0 / mask_thumb.shape[0]

        ys_idx, xs_idx = np.where(mask_thumb > 127)
        if len(xs_idx) == 0:
            raise ValueError("Empty tissue mask — check saturation thresholds")
        x_min = int(xs_idx.min() * scale_x)
        x_max = int(min(w0, (xs_idx.max() + 1) * scale_x))
        y_min = int(ys_idx.min() * scale_y)
        y_max = int(min(h0, (ys_idx.max() + 1) * scale_y))

        records: list[dict[str, Any]] = []
        accepted = 0
        rejected = 0

        for y in range(y_min, y_max - cfg.patch_size + 1, cfg.stride):
            if accepted >= cfg.max_patches_per_slide:
                break
            for x in range(x_min, x_max - cfg.patch_size + 1, cfg.stride):
                if accepted >= cfg.max_patches_per_slide:
                    break
                mx0 = int(x / scale_x)
                my0 = int(y / scale_y)
                mx1 = int((x + cfg.patch_size) / scale_x)
                my1 = int((y + cfg.patch_size) / scale_y)
                mx0 = min(max(mx0, 0), mask_thumb.shape[1] - 1)
                mx1 = min(max(mx1, mx0 + 1), mask_thumb.shape[1])
                my0 = min(max(my0, 0), mask_thumb.shape[0] - 1)
                my1 = min(max(my1, my0 + 1), mask_thumb.shape[0])
                tissue_frac = float(mask_thumb[my0:my1, mx0:mx1].mean() / 255.0)

                reject_reason = ""
                status = "accepted"
                if tissue_frac < cfg.min_tissue_fraction:
                    status = "rejected"
                    reject_reason = "low_tissue_fraction"
                else:
                    tile = np.array(
                        slide.read_region(
                            (x, y),
                            read_level,
                            (patch_at_level, patch_at_level),
                        ).convert("RGB")
                    )
                    if tile.shape[0] != patch_at_level or tile.shape[1] != patch_at_level:
                        status = "rejected"
                        reject_reason = "read_size_mismatch"
                    else:
                        wf = rgb_white_fraction(tile)
                        if wf > cfg.max_white_fraction:
                            status = "rejected"
                            reject_reason = "high_white_fraction"

                if status == "accepted":
                    accepted += 1
                    records.append(
                        {
                            "slide_id": slide_id,
                            "case_id": case_id or "",
                            "x": x,
                            "y": y,
                            "level": read_level,
                            "patch_size": cfg.patch_size,
                            "read_size_at_level": patch_at_level,
                            "tissue_fraction": round(tissue_frac, 4),
                            "status": status,
                            "reject_reason": reject_reason,
                        }
                    )
                else:
                    rejected += 1

        manifest_path = output_dir / "patch_coordinates.csv"
        pd.DataFrame(records).to_csv(manifest_path, index=False)
        report = {
            "slide_id": slide_id,
            "case_id": case_id,
            "wsi_path": str(slide_path),
            "backend": cfg.backend,
            "read_level": read_level,
            "objective_power": slide.properties.get("openslide.objective-power"),
            "dimensions_level0": [w0, h0],
            "patch_size": cfg.patch_size,
            "target_magnification": cfg.target_magnification,
            "accepted_patches": accepted,
            "rejected_patches": rejected,
            "patch_manifest": str(manifest_path.name),
            "thumbnail": "thumbnail.jpg",
            "tissue_mask": "tissue_mask.png",
        }
        (output_dir / "slide_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return report
    finally:
        slide.close()


def run_smoke_preprocessing(
    *,
    subset_manifest: Path,
    download_dir: Path,
    output_root: Path,
    cfg: PreprocessConfig | None = None,
    final_manifest: Path | None = None,
) -> dict[str, Any]:
    cfg = cfg or load_preprocessing_config()
    df = pd.read_csv(subset_manifest, sep="\t")
    case_by_slide: dict[str, str] = {}
    if final_manifest and final_manifest.is_file():
        fdf = pd.read_csv(final_manifest)
        if "slide_id" in fdf.columns and "case_id" in fdf.columns:
            case_by_slide = dict(zip(fdf["slide_id"].astype(str), fdf["case_id"].astype(str)))

    slide_reports = []
    errors: list[str] = []
    for i, row in df.iterrows():
        if i >= cfg.max_slides:
            break
        fid = str(row["id"])
        fn = str(row["filename"])
        slide_id = fn.split(".")[0]
        local = resolve_wsi_file(download_dir, fid, fn)
        if local is None:
            errors.append(f"WSI missing: {fn}")
            continue
        out = output_root / slide_id
        try:
            report = process_one_slide(
                local,
                out,
                cfg,
                slide_id=slide_id,
                case_id=case_by_slide.get(slide_id),
            )
            slide_reports.append(report)
            logger.info(
                "Processed %s: accepted=%d rejected=%d",
                slide_id,
                report["accepted_patches"],
                report["rejected_patches"],
            )
        except Exception as exc:
            errors.append(f"{slide_id}: {exc}")
            logger.exception("Failed %s", slide_id)

    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backend": cfg.backend,
        "config_file": "configs/preprocessing.yaml",
        "slides_requested": min(len(df), cfg.max_slides),
        "slides_processed": len(slide_reports),
        "slides": slide_reports,
        "errors": errors,
        "ok": len(slide_reports) >= min(3, cfg.max_slides) and not errors,
    }
    return audit
