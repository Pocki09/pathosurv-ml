# GDC data acquisition

## 1. Cohort

PathoSurv Lite v1 uses **TCGA-BLCA**. Rationale: `data/cohort_comparison.json` (generate with `python -m data_tools.cohort_comparison`).

## 2. Clinical metadata

1. Open [GDC Data Portal](https://portal.gdc.cancer.gov/) → Projects → **TCGA-BLCA**.
2. Add **Cases** to cart (all cases or filtered set).
3. Download **JSON** (Cases) → save as `data/clinical.json`.

## 3. WSI manifest

1. In the same project, filter:
   - **Data Category**: Biospecimen  
   - **Data Type**: Slide Image  
   - **Experimental Strategy**: Diagnostic Slide  
   - **Access**: open  
2. Add files to cart → **Manifest** download.
3. Save as a versioned name, e.g. `data/gdc_manifest.YYYY-MM-DD.HHMMSS.txt`.
4. Update `manifest_path` in `configs/data.yaml`.
5. Register checksum: `python -m data_tools.register_manifest`.

## 4. Build derived tables (local)

```bash
pip install -e ".[dev]"
python scripts/run_gdc_cohort_pipeline.py
```

Or step by step:

```bash
python -m data_tools.build_clinical_manifest
python -m data_tools.merge_survival_manifest
python -m data_tools.validate_manifest
```

## 5. Smoke-test download (3–10 WSI)

Install [GDC Data Transfer Tool](https://gdc.cancer.gov/access-data/gdc-data-transfer-tool) (`gdc-client` on PATH).

```bash
python -m data_tools.download_subset -n 3
python -m data_tools.verify_downloads
pip install openslide-python  # or pip install -e ".[wsi]"
python -m preprocessing.validate_wsi
```

WSI files land under `data/raw_slides/` (gitignored).

## 6. Traceability

| Artifact | Purpose |
|----------|---------|
| `data/manifest_registry.json` | sha256 of GDC manifest |
| `data/subset_manifest.txt` | UUID/md5 for smoke subset |
| `data/download_audit.json` | per-file md5 after download |
| `data/cohort_validation.json` | cohort ETL validation summary |

See also [WORKFLOW.md](WORKFLOW.md) and [README.md](../README.md).
