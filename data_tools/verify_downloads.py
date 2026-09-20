"""Verify downloaded WSI files against GDC manifest md5 checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pathosurv.config import data_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def md5_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def verify_subset(manifest_path: Path, download_dir: Path) -> dict:
    df = pd.read_csv(manifest_path, sep="\t")
    results = []
    for _, row in df.iterrows():
        file_id = row["id"]
        filename = row["filename"]
        expected_md5 = str(row["md5"]).lower()
        local = download_dir / filename
        if not local.is_file():
            from data_tools.wsi_paths import resolve_wsi_file

            resolved = resolve_wsi_file(download_dir, file_id, filename)
            local = resolved if resolved is not None else local
        if not local.is_file():
            results.append(
                {
                    "id": file_id,
                    "filename": filename,
                    "status": "missing",
                    "expected_md5": expected_md5,
                }
            )
            continue
        actual = md5_file(local).lower()
        results.append(
            {
                "id": file_id,
                "filename": filename,
                "path": str(local),
                "status": "ok" if actual == expected_md5 else "md5_mismatch",
                "expected_md5": expected_md5,
                "actual_md5": actual,
            }
        )
    ok = sum(1 for r in results if r["status"] == "ok")
    audit = {
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest_path": str(manifest_path),
        "download_dir": str(download_dir),
        "file_count": len(results),
        "ok_count": ok,
        "files": results,
    }
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify WSI downloads against manifest md5")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()

    cfg = data_config()
    manifest = args.manifest or Path(cfg["subset_manifest_path"])
    download_dir = args.download_dir or Path(cfg["wsi_download_dir"])
    audit_path = args.audit or Path(cfg["download_audit_path"])

    audit = verify_subset(manifest, download_dir)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    if audit["ok_count"] == 0:
        logger.warning(
            "No files verified yet. Audit written to %s (missing files expected until download)",
            audit_path,
        )
    else:
        logger.info(
            "Verified %d / %d files. Audit: %s",
            audit["ok_count"],
            audit["file_count"],
            audit_path,
        )


if __name__ == "__main__":
    main()
