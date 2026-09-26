# Repository readiness (Colab + new developers)

Last checked against **origin/main** remote: `https://github.com/Pocki09/pathosurv-ml`

## What a fresh clone gets

| Area | Status |
|------|--------|
| Docs | `README.md`, `docs/WORKFLOW.md`, `docs/GDC_DATA_GUIDE.md`, `docs/HUONG_DAN_HUAN_LUYEN.md`, `AGENTS.md` |
| Orchestration | `scripts/run_gdc_cohort_pipeline.py`, `run_final_manifest_pipeline.py`, `run_patient_splits_pipeline.py`, `run_wsi_preprocess_pipeline.py`, `run_training_smoke.py` |
| GDC artifacts (committed) | `data/clinical.json`, versioned `data/gdc_manifest.*.txt`, `final_manifest.csv`, `splits.json`, cohort CSV/JSON audits |
| WSI / features | **Not in Git** (`.gitignore`: `raw_slides/`, `features/`, `preprocessed/`) |
| Checkpoints / model package | **Not in Git** — regenerate with `python scripts/run_training_smoke.py` or full train + `packaging.build_model_package` |

## Verify after clone

```bash
pip install -e ".[dev]"
pytest tests/test_env.py tests/test_final_manifest.py tests/test_gdc_manifest_unit.py tests/test_manifest.py -q
```

Colab: `notebooks/00_colab_smoke_test.ipynb` — clone from GitHub, install, run the focused pytest cell above.

## WSI download (critical)

Always restrict smoke/full subset to slides selected in `final_manifest.csv`:

```bash
python -m data_tools.download_subset --from-final-manifest -n 3
```

Bare `-n 3` on `matched_cohort.csv` can download the wrong slide per patient.

## Colab training (typical)

1. Clone repo (source on GitHub, not only Drive).
2. `pip install -e ".[dev]"` (GPU for train).
3. Mount Drive → sync `data/features/*.pt` and use committed `final_manifest.csv` / `splits.json`.
4. `python -m training.train --model attention_mil_cox` (no `--synthetic-demo` when using real embeddings).

## Local changes not on GitHub until pushed

Run `git status` — commonly uncommitted: `data_tools/download_subset.py` (`--from-final-manifest`), `data/download_audit.json`.

## Optional untracked helpers

None required for onboarding. Regenerate smoke ML artifacts locally when needed.
