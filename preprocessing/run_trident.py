"""
Phase 5 entry point for WSI preprocessing.

Uses OpenSlide + OpenCV baseline (`backend: openslide_baseline` in configs/preprocessing.yaml).
When TRIDENT is installed and validated, this module can delegate to TRIDENT without
changing downstream manifest schema.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from pathosurv.config import data_config
from preprocessing.wsi_preprocess import load_preprocessing_config, run_smoke_preprocessing

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5 WSI preprocessing smoke test")
    parser.add_argument("--manifest", type=Path, help="Subset GDC manifest (tab-separated)")
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()

    cfg_data = data_config()
    subset = args.manifest or Path(cfg_data["subset_manifest_path"])
    download_dir = args.download_dir or Path(cfg_data["wsi_download_dir"])
    pre_cfg = load_preprocessing_config()
    output_root = args.output_dir or Path(cfg_data["preprocessed_dir"])
    audit_path = args.audit or Path(cfg_data["phase5_audit_path"])
    final_manifest = Path(cfg_data.get("final_manifest_path", ""))

    audit = run_smoke_preprocessing(
        subset_manifest=subset,
        download_dir=download_dir,
        output_root=output_root,
        cfg=pre_cfg,
        final_manifest=final_manifest if final_manifest.is_file() else None,
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    if not audit["ok"]:
        logger.error("Phase 5 preprocessing incomplete: %s", audit["errors"])
        raise SystemExit(1)
    logger.info("Phase 5 audit written: %s (%d slides)", audit_path, audit["slides_processed"])


if __name__ == "__main__":
    main()
