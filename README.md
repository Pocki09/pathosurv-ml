# PathoSurv ML

Research pipeline for **PathoSurv Lite**: TCGA whole-slide images → survival risk modeling (MergeSurv-inspired scope).

**Current milestone:** Phase 1–5 (through WSI preprocessing smoke test). Phase 6+ (encoder, training) follow `plan/pathosurv_training_ai_requirement.md`.

**Làm tại nhà (đóng Phase 2):** xem [docs/HUONG_DAN_LAM_TAI_NHA.md](docs/HUONG_DAN_LAM_TAI_NHA.md) — lệnh từng bước và output mong đợi.

## Requirements

- Python 3.10–3.13 (3.14+ may fail on `scikit-survival` / `ecos` wheels)
- Windows, WSL, or Google Colab
- [GDC Data Transfer Tool](https://gdc.cancer.gov/access-data/gdc-data-transfer-tool) for WSI download (`gdc-client`)
- Optional: OpenSlide (`pip install -e ".[wsi]"`) to open `.svs` locally

## Setup (local)

```powershell
cd pathosurv-ml
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Optional: point to a non-default repo root:

```powershell
$env:PATHOSURV_ROOT = "C:\path\to\pathosurv-ml"
```

## Verify environment

```bash
pytest
python -m pathosurv  # via import in tests
```

Or:

```bash
python tests/test_env.py  # legacy smoke (prefer pytest)
```

## Phase 2 — data pipeline

1. Place GDC artifacts (see [docs/GDC_DATA_GUIDE.md](docs/GDC_DATA_GUIDE.md)):
   - `data/clinical.json`
   - `data/gdc_manifest.<version>.txt` (update `configs/data.yaml`)
2. Run:

```bash
python scripts/run_phase2_pipeline.py
```

3. Download smoke subset:

```bash
python -m data_tools.download_subset -n 3
python -m data_tools.verify_downloads
python -m preprocessing.validate_wsi
```

## Phase 3 — final survival manifest

Requires Phase 2 artifacts (`matched_cohort.csv`).

```bash
python scripts/run_phase3_pipeline.py
```

Outputs:

| File | Role |
|------|------|
| `data/final_manifest.csv` | One diagnostic WSI per patient; `split` assigned in Phase 4 |
| `data/dataset_audit.json` | Excluded duplicate slides + validation summary |

Validate only:

```bash
python -m data_tools.validate_final_manifest
python -m data_tools.validate_final_manifest --require-split
python -m data_tools.validate_final_manifest --require-wsi  # all wsi_path must exist on disk
```

## Phase 4 — patient-level splits

Requires `data/final_manifest.csv` from Phase 3.

```bash
python scripts/run_phase4_pipeline.py
```

Outputs:

| File | Role |
|------|------|
| `data/splits.json` | Train/validation/test case lists + event counts per split |
| `data/final_manifest.csv` | Updated `split` column (stratified on `event_status`, seed from `configs/data.yaml`) |

Ratios in `configs/training.yaml` → `split.test_ratio` / `split.validation_ratio` (default 15% / 15%).

## Phase 5 — WSI preprocessing smoke test

Requires OpenSlide + OpenCV (`pip install -e ".[wsi]"`) and WSI files from Phase 2 smoke download.

```bash
python scripts/run_phase5_pipeline.py
```

| Output | Role |
|--------|------|
| `data/preprocessed/<slide_id>/` | Thumbnail, tissue mask, `patch_coordinates.csv`, `slide_report.json` |
| `data/phase5_preprocessing_audit.json` | Per-slide accepted/rejected counts |
| `data/phase5_patch_verify.json` | OpenSlide re-read check on sample coordinates |

Config: `configs/preprocessing.yaml` (`backend: openslide_baseline`; TRIDENT can replace runner later).

## Google Colab

Open [notebooks/00_colab_smoke_test.ipynb](notebooks/00_colab_smoke_test.ipynb): clone this repo, `pip install -e .`, run the same validation commands. Mount Google Drive only for **data and checkpoints**, not for source code.

## Configuration

| File | Role |
|------|------|
| `configs/data.yaml` | Cohort, paths, smoke-test size |
| `configs/project.yaml` | Project metadata & endpoint names |

## Project layout (Phase 1–2)

```text
pathosurv/          # importable package (config, paths, seed)
data_tools/         # GDC manifests, merge, download, validation
preprocessing/      # WSI smoke tests (OpenSlide)
configs/
data/               # manifests & derived CSV (WSI binaries gitignored)
docs/
notebooks/
scripts/
tests/
```

## License & data

TCGA data use is subject to [GDC data access policies](https://gdc.cancer.gov/access-data/data-access-policies). Do not commit raw WSI files or credentials.
