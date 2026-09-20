"""Resolve local paths for GDC-downloaded WSI files (flat or uuid subdirectory)."""

from __future__ import annotations

from pathlib import Path


def resolve_wsi_file(download_dir: Path, file_id: str, filename: str) -> Path | None:
    for candidate in (download_dir / filename, download_dir / file_id / filename):
        if candidate.is_file():
            return candidate
    return None


def expected_wsi_path(download_dir: Path, file_id: str, filename: str) -> Path:
    """Path where ``gdc-client`` typically stores a file (uuid folder)."""
    return download_dir / file_id / filename


def wsi_path_for_manifest(
    download_dir: Path,
    file_id: str,
    filename: str,
    *,
    base: Path,
) -> str:
    """Relative POSIX path for CSV manifests (portable across machines)."""
    local = resolve_wsi_file(download_dir, file_id, filename)
    path = local if local is not None else expected_wsi_path(download_dir, file_id, filename)
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()
