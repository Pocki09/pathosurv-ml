# PathoSurv Lite — Feasibility report (Phase 0)

**Updated:** 2026-09-20 (machine: local Windows, repo `D:\pathosurv-ml`)

```text
selected_cohort:              TCGA-BLCA
estimated_case_count:         359 (processed_metadata.csv)
estimated_wsi_count:          926 (wsi_manifest.csv); 810 matched with survival
estimated_wsi_storage:        ~2.3 GB for 3-slide smoke subset; full matched cohort not downloaded
estimated_embedding_storage:  TBD after encoder dim + patch count (Phase 6)
selected_encoder:             TITAN (target per configs/encoder.yaml)
encoder_access_status:        pending — confirm Hugging Face / license before Phase 6
colab_gpu_test:               not run on 2026-09-20 — use notebooks/00_colab_smoke_test.ipynb
selected_fallback_encoder:    TBD if TITAN unavailable (e.g. UNI); document in encoder.yaml
```

## Local checks (2026-09-20)

| Check | Result |
|-------|--------|
| `pytest -q` | 9 passed |
| `python scripts/run_phase2_pipeline.py` | OK |
| `download_audit.json` | `ok_count`: 3 / 3 (MD5 match) |
| `wsi_open_test.json` | 3 slides opened, OpenSlide available |
| `phase2_validation.json` | `ok`: true (after nested WSI path fix) |
| `gdc-client` | 2.3 |

Smoke subset on disk: **3** `.svs` files under `data/raw_slides/` (~**2.15 GB** total).

## Pass / fail before large download

| Check | Pass criteria | Status |
|-------|----------------|--------|
| GDC manifest registered | `data/manifest_registry.json` has sha256 entry | **Pass** |
| Clinical JSON present | `data/clinical.json` | **Pass** |
| Matched cohort | `python -m data_tools.validate_manifest` exits 0 | **Pass** |
| Subset manifest | `data/subset_manifest.txt` has 3–10 rows | **Pass** (3 rows) |
| WSI open (after download) | `python -m preprocessing.validate_wsi` opens ≥1 slide | **Pass** (3/3) |
| Colab import | Notebook `notebooks/00_colab_smoke_test.ipynb` runs | **Pending** (run before Phase 6) |

## Gate to Phase 3

Phase 2 data artifacts and WSI smoke are **complete**. Next milestone: **Phase 3** — `final_manifest.csv`, `dataset_audit.json`, manifest validation tests.
