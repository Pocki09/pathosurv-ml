# Workflow tổng thể — PathoSurv ML (PathoSurv Lite)

> Cohort hiện tại: **TCGA-BLCA** · Endpoint: **Overall Survival (OS)** · Trạng thái code: **Phase 0–4 đã implement**, Phase 5+ (TRIDENT, training) theo `plan/pathosurv_training_ai_requirement.md`.

## 1. Sơ đồ end-to-end

```text
GDC Portal (thủ công)
 ├─ Cases JSON ──────────────→ data/clinical.json
 └─ File Manifest (.txt) ────→ data/gdc_manifest.<version>.txt
                                  │ + configs/data.yaml (manifest_path)
                                  ▼
Phase 2 — scripts/run_phase2_pipeline.py (8 bước, chạy theo thứ tự)
 1. cohort_comparison      → docs/feasibility/cohort_comparison.json
 2. register_manifest       → data/manifest_registry.json (sha256)
 3. build_clinical_manifest → data/processed_metadata.csv (OS_time/OS_event)
 4. build_slide_manifest    → data/wsi_manifest.csv (.svs only)
 5. merge_survival_manifest → data/matched_cohort.csv (join submitter_id)
 6. validate_manifest       → data/phase2_validation.json
 7. download_subset --no-download → data/subset_manifest.txt
 8. verify_downloads        → data/download_audit.json (lúc này ok_count=0)
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
        download_subset (gọi gdc-client)   preprocessing.validate_wsi (OpenSlide)
         → data/raw_slides/<uuid>/*.svs    → data/wsi_open_test.json
         → verify_downloads (md5 check)
                                  │
                                  ▼
Phase 3 — scripts/run_phase3_pipeline.py (cần matched_cohort.csv)
 1. build_final_manifest    → data/final_manifest.csv (1 dòng / case_id)
                           → data/dataset_audit.json
 2. validate_final_manifest → kiểm tra schema; Phase 4 thêm `--require-split`

Phase 4 — scripts/run_phase4_pipeline.py
 1. create_patient_splits     → data/splits.json + cột split trong final_manifest.csv
 2. validate_final_manifest --require-split

Phase 5 — scripts/run_phase5_pipeline.py (cần `pip install -e ".[wsi]"` + WSI smoke)
 1. preprocessing.run_trident   → data/preprocessed/<slide_id>/… + phase5_preprocessing_audit.json
 2. preprocessing.validate_patches → phase5_patch_verify.json

Phase 6+ (chưa code): encoder (TITAN) → embeddings → Cox MIL training
```

Nguyên tắc môi trường: **local** giữ toàn bộ source/config/test; **Colab** (`notebooks/00_colab_smoke_test.ipynb`) chỉ dùng cho GPU/compute nặng, mount Drive **chỉ để chứa data + checkpoint**, không chứa source.

## 2. Nền tảng: config + paths + seed

| Thành phần | File | Vai trò |
|---|---|---|
| Path resolution | `pathosurv/paths.py` | `project_root()` (ưu tiên `$env:PATHOSURV_ROOT`), `resolve_path()` — mọi path trong `configs/data.yaml` là tương đối so với root |
| Config loader | `pathosurv/config.py` | `data_config()` resolve tất cả key `*_path`, `*_dir`, `manifest_path`, `clinical_path`, `output_csv`, … thành absolute path |
| Seed | `pathosurv/seed.py` | `set_seed(42)` cho `random` + `numpy` + `torch` (torch optional) |
| Cohort/endpoint | `configs/data.yaml`, `configs/project.yaml` | `cohort: TCGA-BLCA`, `random_seed: 42`, `smoke_test_wsi_count: 3`; endpoint `overall_survival → survival_time_days / event_status` |
| Tương lai | `configs/encoder.yaml` (TITAN, `pending_access`), `configs/model.yaml` (`attention_mil_cox` + `mean_pooling_cox` baseline), `configs/training.yaml` (AdamW, early-stop theo `validation_c_index`, 100 epochs) | Chưa dùng ở Phase 2–3 |

Lưu ý quan trọng: `manifest_path` trong `data.yaml` là **tên file có version** (`data/gdc_manifest.2026-09-14.222309.txt`). Thêm manifest mới → đổi key này rồi chạy `register_manifest`.

## 3. Đầu vào thủ công từ GDC Portal

Theo `docs/GDC_DATA_GUIDE.md`:

1. **Clinical:** Portal → Projects → TCGA-BLCA → add Cases to cart → download JSON → lưu `data/clinical.json` (mảng các case).
2. **WSI manifest:** filter `Data Category=Biospecimen`, `Data Type=Slide Image`, `Experimental Strategy=Diagnostic Slide`, `Access=open` → add files to cart → download Manifest → lưu `data/gdc_manifest.YYYY-MM-DD.HHMMSS.txt` → cập nhật `configs/data.yaml` → `python -m data_tools.register_manifest`.

## 4. Phase 2 — pipeline dữ liệu (chi tiết từng bước)

Chạy gộp: `python scripts/run_phase2_pipeline.py`. Chạy lẻ từng module bằng `python -m data_tools.<tên>`. **Không đảo thứ tự** vì mỗi bước đọc output của bước trước.

### 4.1 `cohort_comparison`
So sánh BLCA / LUAD / BRCA / KIRC bằng số liệu ước tính cứng trong code (không gọi GDC API). Ghi `docs/feasibility/cohort_comparison.json`, chốt `TCGA-BLCA` (412 case, ~450 WSI, event ~0.35, vừa Colab Free).

### 4.2 `register_manifest`
Tính `sha256` + `size_bytes` của manifest GDC, append vào `data/manifest_registry.json` (list). Mục đích traceability: biết chính xác manifest version nào sinh ra dataset.

### 4.3 `build_clinical_manifest` → `processed_metadata.csv`
Đọc `clinical.json` (list case), với mỗi case:
- Lấy `diagnoses`, ưu tiên `diagnosis_is_primary_disease == "true"`, fallback phần tử đầu.
- `Dead` → `OS_event=1`, `OS_time = demographic.days_to_death` (fallback `diag.days_to_death`).
- `Alive` → `OS_event=0`, `OS_time = diag.days_to_last_follow_up` (fallback demographic).
- Bỏ qua nếu thiếu `diagnoses`, `vital_status` lạ, thiếu time, hoặc `time <= 0`.
- Output cột: `case_id, submitter_id (TCGA-XX-XXXX), OS_time, OS_event, vital_status`.

### 4.4 `build_slide_manifest` → `wsi_manifest.csv`
Dùng `gdc_manifest.read_gdc_manifest` (đọc TSV, bắt buộc cột `id, filename, md5, size, state`) + `filter_wsi_rows` (giữ `filename endswith .svs`, parse từ tên file):
- `submitter_id` = 3 phần đầu (`TCGA-CF-A9FM`), dùng để join với clinical.
- `slide_id` = phần trước dấu `.` đầu tiên (barcode slide đầy đủ, vd `TCGA-XX-1234-01Z-00-DX1`).

### 4.5 `merge_survival_manifest` → `matched_cohort.csv`
`inner join` WSI rows với clinical trên `submitter_id`. Slide nào không khớp patient có survival hợp lệ thì bị loại ở đây.

### 4.6 `validate_manifest` → `phase2_validation.json`
Kiểm tra 3 artifact: manifest (không rỗng, không trùng `id`), clinical (`OS_event ∈ {0,1}`, `OS_time > 0`, đủ cột), matched cohort (đủ cột `id, filename, md5, submitter_id, case_id, OS_time, OS_event`). Đếm `clinical_rows/events/censored`, `matched_wsi_rows`, số WSI đã có trên đĩa (chấp nhận 2 layout của `gdc-client`: `raw_slides/<file>` hoặc `raw_slides/<uuid>/<file>`). Chưa tải WSI → chỉ warning, `ok` vẫn `true` nếu schema đúng.

### 4.7 `download_subset` → `subset_manifest.txt`
Chọn `n` file (mặc định `smoke_test_wsi_count=3`): sort `matched_cohort.csv` theo cột `id` rồi lấy head (deterministic, không shuffle). Lọc lại các dòng tương ứng từ manifest full, ghi TSV. Nếu không có `--no-download`, gọi `gdc-client download -m <manifest> -d <dir>` qua `shutil.which` — **không có gdc-client thì chỉ warning, không fail**. File nằm ở `data/raw_slides/`.

### 4.8 `verify_downloads` → `download_audit.json`
Đọc `subset_manifest.txt`, với mỗi file tìm local path (thử flat rồi uuid-subdir), tính `md5` và so với `expected_md5`. Trạng thái mỗi file: `ok / missing / md5_mismatch`. Ghi `file_count, ok_count, files[]`.

### 4.9 `preprocessing.validate_wsi` → `wsi_open_test.json`
Smoke test ngoài pipeline script: cần `pip install -e ".[wsi]"` (trên Windows có thể thiếu DLL OpenSlide → dùng WSL). Mở từng file trong subset manifest bằng OpenSlide, ghi `dimensions, level_count, level_dimensions, vendor`. Pass khi mở được ≥ 1 slide.

## 5. Phase 3 — manifest survival chuẩn

Yêu cầu: đã có `data/matched_cohort.csv`. Chạy: `python scripts/run_phase3_pipeline.py`.

### 5.1 `build_final_manifest` → `final_manifest.csv` + `dataset_audit.json`
- **Chọn 1 slide / patient** (`slide_selection.slide_selection_rank`, rank thấp = ưu tiên): sample `01 (tumor chính) > 02 > 06 > khác`, loại `11 (mô normal)` xuống cuối; portion `DX1 > TS/TSA > BS > khác`; tie-break bằng chính `slide_id`.
- Schema `final_manifest.csv`: `case_id, slide_id, wsi_path, survival_time_days (=OS_time), event_status (=OS_event), split` — cột `split` **để trống**, Phase 4 mới gán train/val/test.
- `wsi_path` là relative POSIX path (`wsi_paths.wsi_path_for_manifest`): nếu file đã tải thì path thật, chưa tải thì path kỳ vọng `raw_slides/<id>/<filename>` — nên validate `--require-wsi` sẽ fail cho đến khi download xong, đó là hành vi đúng.
- `dataset_audit.json`: `created_at, cohort, endpoint (từ project.yaml), input_matched_rows, final_manifest_rows, unique_cases, event/censored/excluded_count, excluded[] (lý do duplicate_patient_not_selected + selected_slide_id), validation{ok, errors}, notes`.

### 5.2 `validate_final_manifest`
Luật: đủ 6 cột, không rỗng, `case_id/slide_id/wsi_path` không null/rỗng, `survival_time_days > 0`, `event_status ∈ {0,1}`, không trùng `case_id`/`slide_id`. Hai cờ strict tùy chọn: `--require-split` (Phase 4) và `--require-wsi` (mọi `wsi_path` phải tồn tại).

## 6. Phase 4+ — roadmap chưa implement

Theo `plan/pathosurv_training_ai_requirement.md` và `configs/*`: `create_patient_splits` (patient-level, seed cố định, không leakage), TRIDENT (segmentation → patch coordinates), encoder TITAN frozen → embeddings, Mean-Pooling+Cox baseline và Attention-MIL+Cox (AdamW, early-stop theo val C-index, metric `scikit-survival`), đóng gói model + golden-sample parity. Hiện chỉ có config và `training/utils.py` (re-export `set_seed`).

## 7. Bảng artifact trong `data/`

| File | Sinh bởi | Ý nghĩa |
|---|---|---|
| `clinical.json`, `gdc_manifest.*.txt` | thủ công (GDC Portal) | input gốc, không sửa bằng code |
| `processed_metadata.csv` | `build_clinical_manifest` | survival theo patient |
| `wsi_manifest.csv` | `build_slide_manifest` | dòng `.svs` + submitter/slide id |
| `matched_cohort.csv` | `merge_survival_manifest` | WSI đã gắn survival (nhiều slide/patient) |
| `manifest_registry.json` | `register_manifest` | sha256 manifest |
| `subset_manifest.txt` | `download_subset --no-download` | manifest TSV cho smoke test |
| `download_audit.json` | `verify_downloads` | md5 từng file tải |
| `phase2_validation.json` | `validate_manifest` | báo cáo pass/fail Phase 2 |
| `wsi_open_test.json` | `validate_wsi` | OpenSlide có mở được slide không |
| `final_manifest.csv` | `build_final_manifest` | 1 slide/patient, split trống |
| `dataset_audit.json` | `build_final_manifest` | slide bị loại + validation |
| `data/raw_slides/` | `gdc-client` | binary `.svs`, **gitignored** |

## 8. Lệnh chạy nhanh

```bash
pip install -e ".[dev]"                        # base
pip install -e ".[wsi]"                         # OpenSlide (mở .svs)
pytest                                          # full test
pytest tests/test_final_manifest.py tests/test_gdc_manifest_unit.py -q   # test không cần data
pytest tests/test_manifest.py::test_final_manifest_valid -q               # 1 test cần data
python scripts/run_phase2_pipeline.py           # Phase 2 (8 bước)
python -m data_tools.download_subset -n 3       # tải smoke (cần gdc-client trên PATH)
python -m data_tools.verify_downloads
python -m preprocessing.validate_wsi
python scripts/run_phase3_pipeline.py           # Phase 3 (cần matched_cohort.csv)
python -m data_tools.validate_final_manifest --require-wsi
```

## 9. Test & quy ước cần nhớ

- `tests/test_manifest.py` đọc artifact thật trong `data/` nên fail khi thiếu data — đó là tín hiệu thiếu input, không phải bug code. Test thuần unit: `test_final_manifest.py`, `test_gdc_manifest_unit.py`. `test_env.py` dùng `importorskip(torch/sksurv)`.
- Python `3.10–3.13`; `3.14` hay hỏng wheel `scikit-survival/ecos`.
- Không commit `*.svs`, `data/raw_slides/`, credential; metadata/audit CSV+JSON nhỏ thì được commit.
- Không có lint/typecheck/CI — `pytest` là cổng kiểm tra duy nhất.
