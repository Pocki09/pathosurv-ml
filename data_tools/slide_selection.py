"""Pick one diagnostic WSI per patient from TCGA slide barcodes."""

from __future__ import annotations


def slide_selection_rank(slide_id: str) -> tuple[int, int, str]:
    """
    Lower rank = preferred diagnostic slide.

    Prefers primary tumor sample (01), then DX1, then other tumor sections.
    Deprioritizes normal tissue (11).
    """
    parts = slide_id.split("-")
    sample = parts[3] if len(parts) > 3 else "99"
    portion = parts[5].lower() if len(parts) > 5 else ""

    if sample == "11":
        sample_rank = 10
    elif sample == "01":
        sample_rank = 0
    elif sample == "02":
        sample_rank = 1
    elif sample == "06":
        sample_rank = 2
    else:
        sample_rank = 5

    if "dx1" in portion:
        type_rank = 0
    elif portion.startswith("ts") or "tsa" in portion:
        type_rank = 1
    elif "bs" in portion:
        type_rank = 2
    else:
        type_rank = 3

    return (sample_rank, type_rank, slide_id)
