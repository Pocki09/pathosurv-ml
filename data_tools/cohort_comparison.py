"""
Document TCGA cohort trade-offs for PathoSurv Lite v1 cohort selection.

Estimates are indicative (GDC portal counts change over time). Re-run GDC filters
to refresh before production downloads.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Rough planning figures for first prototype (not live GDC API calls)
COHORT_PROFILES = [
    {
        "project_id": "TCGA-BLCA",
        "cancer": "Bladder urothelial carcinoma",
        "approx_cases_with_wsi": 412,
        "approx_wsi_count": 450,
        "avg_wsi_gb": 0.35,
        "survival_endpoint": "OS from days_to_death / days_to_last_follow_up",
        "approx_event_rate": 0.35,
        "colab_free_fit": "good",
        "notes": "Selected for v1: manageable size, clear OS fields, diagnostic SVS available.",
        "selected": True,
    },
    {
        "project_id": "TCGA-LUAD",
        "cancer": "Lung adenocarcinoma",
        "approx_cases_with_wsi": 500,
        "approx_wsi_count": 1050,
        "avg_wsi_gb": 0.45,
        "survival_endpoint": "OS",
        "approx_event_rate": 0.40,
        "colab_free_fit": "moderate",
        "notes": "More slides per patient; larger storage.",
        "selected": False,
    },
    {
        "project_id": "TCGA-BRCA",
        "cancer": "Breast invasive carcinoma",
        "approx_cases_with_wsi": 1100,
        "approx_wsi_count": 1200,
        "avg_wsi_gb": 0.5,
        "survival_endpoint": "OS",
        "approx_event_rate": 0.15,
        "colab_free_fit": "poor_for_full_cohort",
        "notes": "Large cohort; low event rate for OS in short follow-up.",
        "selected": False,
    },
    {
        "project_id": "TCGA-KIRC",
        "cancer": "Kidney renal clear cell carcinoma",
        "approx_cases_with_wsi": 520,
        "approx_wsi_count": 580,
        "avg_wsi_gb": 0.4,
        "survival_endpoint": "OS",
        "approx_event_rate": 0.30,
        "colab_free_fit": "moderate",
        "notes": "Solid alternative if BLCA access issues.",
        "selected": False,
    },
]


def build_report() -> dict:
    selected = next(c for c in COHORT_PROFILES if c.get("selected"))
    return {
        "selected_cohort": selected["project_id"],
        "comparison": COHORT_PROFILES,
        "recommendation": (
            "Use TCGA-BLCA for PathoSurv Lite v1: balance of WSI availability, "
            "OS endpoint quality, and storage fit for smoke test + Colab training."
        ),
        "gdc_filters_hint": {
            "project_id": "TCGA-BLCA",
            "data_category": "Biospecimen",
            "data_type": "Slide Image",
            "experimental_strategy": "Diagnostic Slide",
            "access": "open",
        },
    }


def main() -> None:
    from pathosurv.config import data_config

    parser = argparse.ArgumentParser(description="Write cohort comparison JSON")
    cfg = data_config()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(cfg["cohort_comparison_path"]),
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
