# Workflow — PathoSurv ML (PathoSurv Lite)

> Cohort: **TCGA-BLCA** · Endpoint: **Overall Survival (OS)** · Pipeline: GDC ETL → final manifest → splits → WSI preprocess → embeddings → Cox/MIL training → model package.

Đọc thêm: [README.md](../README.md) · [GDC_DATA_GUIDE.md](GDC_DATA_GUIDE.md) · [HUONG_DAN_HUAN_LUYEN.md](HUONG_DAN_HUAN_LUYEN.md)

## 1. Sơ đồ end-to-end

```text
GDC Portal (thủ công)
 ├─ Cases JSON ──────────────→ data/clinical.json
 └─ File Manifest (.txt) ────→ data/gdc_manifest.<version>.txt
                                  │ + configs/data.yaml (manifest_path)
                                  ▼
GDC cohort — scripts/run_gdc_cohort_pipeline.py
 1. cohort_comparison      → data/cohort_comparison.json
 2. register_manifest       → data/manifest_registry.json (sha256)
 3. build_clinical_manifest → data/processed_metadata.csv (OS_time/OS_event)
 4. build_slide_manifest    → data/wsi_manifest.csv (.svs only)
 5. merge_survival_manifest → data/matched_cohort.csv (join submitter_id)
 6. validate_manifest       → data/cohort_validation.json
 7. download_subset --no-download → data/subset_manifest.txt
 8. verify_downloads        → data/download_audit.json
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
        download_subset (gdc-client)   preprocessing.validate_wsi (OpenSlide)
         → data/raw_slides/<uuid>/*.svs    → data/wsi_open_test.json
         → verify_downloads (md5 check)
                                  │
                                  ▼
Final manifest — scripts/run_final_manifest_pipeline.py
 1. build_final_manifest    → data/final_manifest.csv (1 dòng / case_id)
                           → data/dataset_audit.json
 2. validate_final_manifest

Patient splits — scripts/run_patient_splits_pipeline.py
 1. create_patient_splits     → data/splits.json + cột split
 2. validate_final_manifest --require-split

WSI preprocess — scripts/run_wsi_preprocess_pipeline.py (cần `[wsi]` + WSI on disk)
 1. preprocessing.run_trident   → data/preprocessed/<slide_id>/… + wsi_preprocessing_audit.json
 2. preprocessing.validate_patches → patch_verify.json

Embeddings + training
  extract_embeddings → data/features/<slide_id>.pt
  training.train → checkpoints
  evaluation + packaging → data/model_packages/
```

Colab: mount Drive **chỉ** cho `data/` + checkpoints; source code clone từ Git.

## 2. Config và paths

| Thành phần | File | Vai trò |
|---|---|---|
| Path resolution | `pathosurv/paths.py` | `PATHOSURV_ROOT`, `resolve_path()` |
| Config | `pathosurv/config.py` | `data_config()` resolve `*_path`, `*_dir` |
| Seed | `pathosurv/seed.py` | `set_seed(42)` |
| Cohort | `configs/data.yaml`, `configs/project.yaml` | TCGA-BLCA, smoke_test_wsi_count, manifest paths |

`manifest_path` phải khớp file manifest GDC trên đĩa; đổi manifest → cập nhật YAML → `register_manifest`.

## 3. Artifact chính (`data/`)

| File | Sinh bởi | Ý nghĩa |
|---|---|---|
| `clinical.json`, `gdc_manifest.*.txt` | GDC Portal | Input gốc |
| `processed_metadata.csv` | `build_clinical_manifest` | OS theo patient |
| `matched_cohort.csv` | `merge_survival_manifest` | WSI + survival |
| `cohort_validation.json` | `validate_manifest` | Pass/fail ETL |
| `final_manifest.csv` | `build_final_manifest` | 1 slide/patient |
| `splits.json` | `create_patient_splits` | Train/val/test |
| `wsi_preprocessing_audit.json` | `run_trident` | Preprocess smoke |
| `data/raw_slides/` | `gdc-client` | `.svs` gitignored |

## 4. Lệnh nhanh

```bash
pip install -e ".[dev]"
pip install -e ".[wsi]"
pytest
python scripts/run_gdc_cohort_pipeline.py
python -m data_tools.download_subset -n 3
python -m data_tools.verify_downloads
python -m preprocessing.validate_wsi
python scripts/run_final_manifest_pipeline.py
python scripts/run_patient_splits_pipeline.py
python scripts/run_wsi_preprocess_pipeline.py
python scripts/run_training_smoke.py
```

## 5. Test

- `tests/test_manifest.py` cần artifact GDC thật trong `data/`.
- Unit không cần WSI: `tests/test_final_manifest.py`, `tests/test_gdc_manifest_unit.py`.
- Python 3.10–3.13; `pytest` là cổng kiểm tra duy nhất.
