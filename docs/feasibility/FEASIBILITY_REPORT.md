# PathoSurv Lite — Feasibility report (Phase 0 template)

Fill this after local disk/GPU checks and encoder access review.

```text
selected_cohort:              TCGA-BLCA
estimated_case_count:         (from GDC / matched_cohort)
estimated_wsi_count:          (from wsi_manifest.csv)
estimated_wsi_storage:        GB
estimated_embedding_storage:  GB
selected_encoder:             TITAN or fallback (document)
encoder_access_status:        granted / pending / using fallback
colab_gpu_test:               pass / fail (date, GPU model)
selected_fallback_encoder:    e.g. UNI / ResNet50-baseline (Phase 6 only)
```

## Pass / fail before large download

| Check | Pass criteria |
|-------|----------------|
| GDC manifest registered | `data/manifest_registry.json` has sha256 entry |
| Clinical JSON present | `data/clinical.json` |
| Matched cohort | `python -m data_tools.validate_manifest` exits 0 |
| Subset manifest | `data/subset_manifest.txt` has 3–10 rows |
| WSI open (after download) | `python -m preprocessing.validate_wsi` opens ≥1 slide |
| Colab import | Notebook `notebooks/00_colab_smoke_test.ipynb` runs |
