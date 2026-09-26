"""Unit tests for preprocessing helpers."""

import numpy as np

from preprocessing.wsi_preprocess import (
    load_preprocessing_config,
    rgb_white_fraction,
    tissue_mask_from_rgb,
)


def test_rgb_white_fraction_all_white():
    tile = np.full((32, 32, 3), 240, dtype=np.uint8)
    assert rgb_white_fraction(tile) == 1.0


def test_tissue_mask_detects_colored_region():
    cfg = load_preprocessing_config()
    img = np.full((64, 64, 3), 230, dtype=np.uint8)
    img[20:40, 20:40] = [120, 40, 40]
    mask = tissue_mask_from_rgb(img, cfg)
    assert mask[30, 30] > 0
    assert mask[5, 5] == 0


def test_preprocessing_config_loads():
    cfg = load_preprocessing_config()
    assert cfg.patch_size == 256
    assert cfg.backend == "openslide_baseline"
