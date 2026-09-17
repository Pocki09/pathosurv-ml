"""Record versioned GDC manifest metadata for traceability (UUID / checksum log)."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pathosurv.config import data_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def register_manifest(manifest_path: Path, registry_path: Path, cohort: str) -> dict:
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    entry = {
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "cohort": cohort,
        "manifest_path": str(manifest_path),
        "manifest_basename": manifest_path.name,
        "sha256": file_sha256(manifest_path),
        "size_bytes": manifest_path.stat().st_size,
    }

    registry: list = []
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        if not isinstance(registry, list):
            registry = []

    registry.append(entry)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    logger.info("Registered manifest %s (sha256=%s…)", manifest_path.name, entry["sha256"][:12])
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Register GDC manifest in manifest_registry.json")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    cfg = data_config()
    manifest_path = args.manifest or Path(cfg["manifest_path"])
    registry_path = Path(cfg["manifest_registry_path"])
    register_manifest(manifest_path, registry_path, cfg.get("cohort", "unknown"))


if __name__ == "__main__":
    main()
