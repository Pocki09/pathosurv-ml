# Hướng dẫn làm tại nhà — đóng Phase 2 & chuẩn bị Phase 3

Tài liệu này dành cho buổi làm **trên máy cá nhân**: cài môi trường, tải WSI smoke test, kiểm tra output. **Ngày hôm sau** trên máy công (hoặc tiếp tục ở nhà) bạn có thể chuyển sang **Phase 3** (manifest survival chuẩn).

**Liên quan:** [GDC_DATA_GUIDE.md](GDC_DATA_GUIDE.md) · [feasibility/FEASIBILITY_REPORT.md](feasibility/FEASIBILITY_REPORT.md) · [PHASE1_PHASE2_REVIEW.md](PHASE1_PHASE2_REVIEW.md)

---

## 1. Mục tiêu buổi tối

| # | Việc | Pass khi |
|---|------|----------|
| A | Python + venv + cài package | `python -m pytest -q` → tất cả pass (không skip `test_env` vì thiếu torch) |
| B | Pipeline dữ liệu Phase 2 | `data/phase2_validation.json` → `"ok": true` |
| C | GDC Tool + tải 3 WSI | `data/download_audit.json` → `ok_count` = 3 |
| D | Mở WSI (OpenSlide) | `data/wsi_open_test.json` → có ≥ 1 slide, `openslide_available: true` |
| E | (Khuyến nghị) Feasibility + Colab smoke | Điền template + notebook chạy import/pytest |

**Không bắt buộc tối nay:** tải full cohort, train model, Phase 3 code.

---

## 2. Lấy code từ Git

### Nếu repo đã push từ máy công

```powershell
cd C:\Users\YourName\projects   # thư mục bạn thích
git clone <URL-remote-của-pathosurv-ml>
cd pathosurv-ml
git pull
```

### Nếu chưa push — copy folder

Copy cả thư mục `pathosurv-ml` (USB / OneDrive). **Không** cần copy `data/raw_slides/` nếu chưa tải WSI ở công ty.

**Lưu ý:** File WSI **không** đi qua Git. Máy nhà phải **tải lại** bằng `gdc-client` (hoặc copy `data/raw_slides/` thủ công nếu đã tải ở nơi khác).

---

## 3. Cài Python (quan trọng)

Dùng **Python 3.10, 3.11 hoặc 3.12** (khuyến nghị **3.11**).

- Tránh **3.14** trên Windows: `scikit-survival` / `ecos` thường không cài được (lỗi build C++).

Kiểm tra:

```powershell
py -3.11 --version
# hoặc
python --version
```

Tạo venv:

```powershell
cd pathosurv-ml
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

**Output mong đợi:** không lỗi đỏ; cuối cùng có `torch`, `scikit-survival`, `pytest`.

Kiểm tra môi trường:

```powershell
python -m pytest -q
```

**Output mong đợi:**

```text
.......                                                                  [100%]
7 passed
```

(Nếu thấy `1 skipped` ở `test_env` → torch/sksurv chưa cài đúng, quay lại bước `pip install -e ".[dev]"`.)

---

## 4. Cài GDC Data Transfer Tool

1. Tải từ: [GDC Data Transfer Tool](https://gdc.cancer.gov/access-data/gdc-data-transfer-tool).
2. Cài bản Windows; thêm thư mục chứa `gdc-client.exe` vào **PATH** (hoặc dùng full path trong lệnh).
3. Kiểm tra:

```powershell
gdc-client --version
```

**Output mong đợi:** hiện version (ví dụ `1.6.x`), không báo “command not found”.

**GDC Tool không push lên Git** — máy nhà cài một lần, máy công cài lại nếu cần.

---

## 5. Kiểm tra dữ liệu đã có trong repo

Trong `data/` cần có (đã có trên branch hiện tại nếu bạn pull đủ commit):

| File | Mô tả |
|------|--------|
| `clinical.json` | Cases JSON từ GDC |
| `gdc_manifest.2026-09-14.222309.txt` | Manifest GDC (tab-separated) |
| `configs/data.yaml` | `manifest_path` trùng tên file trên |

Nếu thiếu `clinical.json` hoặc manifest → làm theo [GDC_DATA_GUIDE.md](GDC_DATA_GUIDE.md) (tải từ portal, đặt vào `data/`, sửa `configs/data.yaml`).

---

## 6. Chạy pipeline Phase 2 (local)

```powershell
cd pathosurv-ml
.\.venv\Scripts\Activate.ps1
python scripts/run_phase2_pipeline.py
```

**Output mong đợi (cuối log):**

```text
Phase 2 pipeline finished. Download WSI with:
  python -m data_tools.download_subset
...
```

**File tạo / cập nhật:**

| File | Ý nghĩa |
|------|---------|
| `docs/feasibility/cohort_comparison.json` | So sánh cohort (BLCA được chọn) |
| `data/manifest_registry.json` | sha256 manifest GDC (traceability) |
| `data/processed_metadata.csv` | Bệnh nhân + OS_time / OS_event |
| `data/wsi_manifest.csv` | Chỉ dòng `.svs` |
| `data/matched_cohort.csv` | WSI ghép survival |
| `data/subset_manifest.txt` | 3 file cho smoke download |
| `data/phase2_validation.json` | Báo cáo validate |
| `data/download_audit.json` | Trước tải: `ok_count` có thể = 0 |

Mở `data/phase2_validation.json`:

**Pass:**

```json
{
  "ok": true,
  "errors": [],
  "counts": {
    "clinical_rows": ... ,
    "clinical_events": > 0,
    "matched_wsi_rows": ...
  }
}
```

**Warning chấp nhận được trước khi tải WSI:**

```text
"No WSI files in wsi_download_dir yet — run download_subset after gdc-client"
```

Lệnh validate riêng (exit code 0 = pass):

```powershell
python -m data_tools.validate_manifest
```

---

## 7. Tải 3 WSI smoke test

```powershell
python -m data_tools.download_subset -n 3
```

- Lần đầu **không** dùng `--no-download`.
- File lưu tại `data/raw_slides/` (có thể có thư mục con theo UUID của `gdc-client`).

**Output mong đợi:** log `Running: gdc-client download ...`; sau vài phút–vài chục phút có file `.svs` (mỗi file ~200–500 MB+).

Verify checksum:

```powershell
python -m data_tools.verify_downloads
```

Mở `data/download_audit.json`:

**Pass:**

```json
{
  "file_count": 3,
  "ok_count": 3,
  "files": [
    { "status": "ok", "expected_md5": "...", "actual_md5": "..." },
    ...
  ]
}
```

**Fail thường gặp:** `status: "missing"` → download chưa xong hoặc sai thư mục; `md5_mismatch` → tải lại file lỗi.

Chạy lại validate tổng:

```powershell
python -m data_tools.validate_manifest
```

Sau khi có WSI, `phase2_validation.json` có thể thêm `wsi_files_on_disk` > 0 (nếu script đếm được).

---

## 8. Mở WSI với OpenSlide (Windows)

```powershell
pip install openslide-python
# hoặc: pip install -e ".[wsi]"
```

Trên Windows, `openslide-python` đôi khi cần **OpenSlide binary** (DLL). Nếu `import openslide` lỗi:

- Cài OpenSlide for Windows (build phổ biến: [openslide binaries](https://openslide.org/download/)) và thêm DLL vào PATH, **hoặc**
- Dùng WSL2 + `apt install openslide-tools` + chạy `validate_wsi` trong WSL (cùng repo mount).

Chạy:

```powershell
python -m preprocessing.validate_wsi
```

**Output mong đợi:** exit code **0**; file `data/wsi_open_test.json`:

```json
{
  "openslide_available": true,
  "slides": [
    {
      "path": "...",
      "dimensions": [width, height],
      "level_count": ...
    }
  ],
  "errors": []
}
```

**Pass Phase 2 theo review:** ≥ **1** slide mở được (tốt nhất 3/3).

---

## 9. Điền feasibility (Phase 0 — khuyến nghị)

Sửa file [feasibility/FEASIBILITY_REPORT.md](feasibility/FEASIBILITY_REPORT.md) hoặc tạo bản copy có ngày:

- Dung lượng ổ còn trống (GB) trước/sau tải 3 WSI.
- Colab: mở notebook `notebooks/00_colab_smoke_test.ipynb`, chạy clone + `pip install -e ".[dev]"` + `pytest` → ghi **pass/fail**, GPU model nếu có.
- Encoder: TITAN đã xin quyền chưa; nếu chưa → ghi `encoder_access_status: pending`.

Số liệu lấy từ repo:

```powershell
python -c "import pandas as pd; m=pd.read_csv('data/matched_cohort.csv'); print('matched_wsi', len(m)); c=pd.read_csv('data/processed_metadata.csv'); print('cases', len(c), 'events', c.OS_event.sum())"
```

---

## 10. Git: commit gì, không commit gì

### Có thể commit (metadata / audit)

- `data/phase2_validation.json`
- `data/download_audit.json` (sau khi `ok_count` = 3)
- `data/manifest_registry.json`
- `data/processed_metadata.csv`, `matched_cohort.csv`, `wsi_manifest.csv`, `subset_manifest.txt` (nếu thay đổi sau pipeline)
- `docs/feasibility/FEASIBILITY_REPORT.md` (nếu bạn điền)

### Không commit

- `data/raw_slides/**/*.svs`
- `.venv/`
- Token GDC / credential

```powershell
git status
# đảm bảo không thấy *.svs staged
git add data/download_audit.json data/phase2_validation.json docs/feasibility/
git commit -m "Phase 2: WSI smoke download verified at home"
git push
```

(Nếu push fail do mạng công ty — push từ nhà hoặc mang commit sang máy công bằng patch/USB.)

---

## 11. Mang sang ngày mai — checklist “đã xong”

Đánh dấu và (tuỳ chọn) gửi cho mentor/AI:

- [ ] `pytest` → 7 passed (hoặc ghi rõ version Python + lỗi nếu fail)
- [ ] `phase2_validation.json` → `"ok": true`
- [ ] `download_audit.json` → `ok_count: 3`
- [ ] `wsi_open_test.json` → ≥ 1 slide (hoặc ghi “OpenSlide chưa cài — cần WSL”)
- [ ] `git push` đã có audit JSON (không cần WSI trên remote)

**Câu mở Phase 3 ngày mai:**  
*“Phase 2 đã pass ở nhà (đính kèm audit/validation). Triển khai Phase 3: final_manifest.csv, dataset_audit, create_patient_splits.”*

---

## 12. Lỗi thường gặp

| Triệu chứng | Hướng xử lý |
|-------------|-------------|
| `pip install` lỗi `ecos` / MSVC | Dùng Python **3.11**, không dùng 3.14 |
| `gdc-client` not found | Cài GDC Tool, thêm PATH, mở terminal mới |
| Download chậm / timeout | Chạy lại `gdc-client` (resume); tải ban đêm |
| `clinical_events: 0` trong validation | Pull code mới nhất; chạy lại `build_clinical_manifest` |
| OpenSlide import error | Cài DLL Windows hoặc validate trong WSL |
| `pytest` pass nhưng skip `test_env` | `pip install -e ".[dev]"` chưa có torch/sksurv |

---

## 13. Bước tiếp theo (Phase 5)

Phase 4:

```powershell
python scripts/run_phase4_pipeline.py
```

Artifact: `data/splits.json`, cột `split` trong `final_manifest.csv`.

Tiếp theo (Phase 5): TRIDENT smoke test trên WSI đã tải.

---

*Cập nhật: đồng bộ với repo PathoSurv ML Phase 1–2.*
