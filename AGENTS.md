# AGENTS.md

## Setup
- Python `3.10–3.13` only (`scikit-survival` / `ecos` wheels break on 3.14+).
- `pip install -e ".[dev]"`; add WSI support with `pip install -e ".[wsi]"` (OpenSlide).
- `pytest` uses `testpaths=["tests"]`, `pythonpath=["."]` — run from repo root.
- Optional root override: `$env:PATHOSURV_ROOT="C:\path\to\pathosurv-ml"`; otherwise root = parent of `pathosurv/`.

## Paths & config
- All paths in `configs/data.yaml` are relative to repo root and resolved via `pathosurv/paths.py:resolve_path` + `pathosurv/config.py:data_config`. Never hardcode `data/...` paths in new code — read them from `data_config()`.
- `manifest_path` in `configs/data.yaml` is a **versioned filename** (`data/gdc_manifest.<version>.txt`). When adding a new GDC manifest, update that key.
- `smoke_test_wsi_count` (default 3) and `random_seed: 42` live in `configs/data.yaml`.

## Pipelines (order matters)
- GDC cohort: `python scripts/run_gdc_cohort_pipeline.py` (runs `cohort_comparison → register_manifest → build_clinical_manifest → build_slide_manifest → merge_survival_manifest → validate_manifest → download_subset --no-download → verify_downloads`). Then real download: `python -m data_tools.download_subset --from-final-manifest -n 3`, `python -m data_tools.verify_downloads`, `python -m preprocessing.validate_wsi`.
- Final manifest (needs `data/matched_cohort.csv`): `python scripts/run_final_manifest_pipeline.py` → `data/final_manifest.csv` (one row per `case_id`, `split` empty until splits) + `data/dataset_audit.json`. Validate-only: `python -m data_tools.validate_final_manifest [--require-wsi]`.
- Patient splits: `python scripts/run_patient_splits_pipeline.py` → assigns `split` in `final_manifest.csv` + `data/splits.json`. Validate: `python -m data_tools.validate_final_manifest --require-split`.
- WSI preprocessing: `pip install -e ".[wsi]"` then `python scripts/run_wsi_preprocess_pipeline.py` → `data/wsi_preprocessing_audit.json` + artifacts under `data/preprocessed/` (gitignored). OpenSlide baseline until TRIDENT is wired in `preprocessing/run_trident.py`.
- Training smoke: `python scripts/run_training_smoke.py` (embeddings + synthetic Cox/MIL train + package). Full cohort: [docs/HUONG_DAN_HUAN_LUYEN.md](docs/HUONG_DAN_HUAN_LUYEN.md).
- Do not run pipeline modules out of order; each step expects the previous step's CSV artifact. `download_subset --no-download` only writes `data/subset_manifest.txt`; without the flag it shells out to external `gdc-client` (warns and skips if not on PATH).

## Domain rules
- One diagnostic slide per patient: rank in `data_tools/slide_selection.py:slide_selection_rank` prefers sample `01 > 02 > 06`, deprioritizes normal `11`; portion `DX1 > TSA/TS > BS`. Excluded slides go to audit with `reason=duplicate_patient_not_selected`.
- Survival columns: `matched_cohort.csv` uses `OS_time (>0)` / `OS_event (0/1)`; `final_manifest.csv` uses `survival_time_days (>0)` / `event_status (0/1)`, one row per `case_id`.

## Tests
- `pytest` (full) vs focused: `pytest tests/test_final_manifest.py tests/test_gdc_manifest_unit.py` run without data; `pytest tests/test_manifest.py` requires real GDC artifacts (`data/clinical.json`, versioned `gdc_manifest*.txt`, `processed_metadata.csv`, `matched_cohort.csv`, `final_manifest.csv`) and fails without them. Single test: `pytest tests/test_manifest.py::test_final_manifest_valid -q`.
- `tests/test_env.py` skips if `torch`/`sksurv` missing (`pytest.importorskip`).

## Gotchas
- `data/raw_slides/`, `data/features/`, `*.svs` are gitignored. Never commit WSI binaries or credentials; TCGA use is under GDC data-access policies.
- No lint/typecheck/CI config in repo — `pytest` is the only verification gate.
- Colab (`notebooks/00_colab_smoke_test.ipynb`): mount Drive for data/checkpoints only, never source code.
