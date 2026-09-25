# Hướng dẫn huấn luyện PathoSurv Lite

Tài liệu này mô tả **train thật trên cohort** (Colab + GPU) và **smoke train local** đã có trong repo.

## Tóm tắt pipeline sau Phase 5

```text
Phase 6  → extract_embeddings (ResNet50 frozen; thay TITAN khi có quyền)
Phase 7  → pytest test_cox_loss.py
Phase 8  → train mean_pooling_cox
Phase 9  → train attention_mil_cox
Phase 10 → evaluation.evaluate (C-index, scikit-survival)
Phase 12 → reference_statistics.json (validation split)
Phase 13 → packaging.build_model_package
```

Chạy smoke end-to-end (local, không cần full WSI cohort):

```powershell
cd pathosurv-ml
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,wsi]"
python scripts/run_phases_6_14_smoke.py
```

Smoke train dùng **`--synthetic-demo`** (40 case giả có event/censor) để kiểm tra Cox + MIL + checkpoint + model package.  
Embedding **thật** vẫn được trích từ **3 WSI smoke** (Phase 5) vào `data/features/*.pt`.

---

## Điều kiện train cohort thật (TCGA-BLCA)

1. **WSI on disk** — hiện repo chỉ có 3 slide smoke; cohort đủ 359 case cần tải WSI theo `final_manifest.csv` (`gdc-client` + đủ dung lượng ổ).
2. **Preprocessing** — chạy Phase 5 cho từng slide (hoặc TRIDENT khi tích hợp), tạo `patch_coordinates.csv`.
3. **Encoder** — cập nhật `configs/encoder.yaml`:
   - `fallback_encoder_id: resnet50_imagenet` (mặc định, smoke)
   - Khi có TITAN: đổi encoder trong Colab, **cập nhật `embedding_dim`** trong `configs/model.yaml` cho khớp.
4. **Không leakage** — luôn dùng `split` trong `final_manifest.csv`; **không** dùng test để chọn checkpoint.

---

## Local — embedding từ WSI đã preprocess

```powershell
python -m preprocessing.extract_embeddings --max-patches 200
python -m preprocessing.validate_embeddings
```

Output: `data/features/<slide_id>.pt`, audit `data/embedding_audit.json`.

**Lưu ý:** 3 slide smoke trong manifest đều **censored** (`event_status=0`) → **không đủ event** để Cox loss. Train cohort thật bắt buộc có nhiều case + event (train split).

---

## Local / Colab — train Mean Pooling + Cox (Phase 8)

```powershell
python -m training.train --model mean_pooling_cox
```

Yêu cầu: embedding file tồn tại cho mọi dòng train/val trong manifest.

Hyperparameters: `configs/training.yaml` (`learning_rate`, `batch_size`, `patience`, `max_epochs`).

Checkpoint: `data/checkpoints/mean_pooling_cox_best.pt`

---

## Train Attention MIL + Cox (Phase 9)

```powershell
python -m training.train --model attention_mil_cox
```

Checkpoint: `data/checkpoints/attention_mil_cox_best.pt`

So sánh validation C-index với baseline Mean Pooling.

---

## Đánh giá (Phase 10)

```powershell
python -m evaluation.evaluate --checkpoint data/checkpoints/attention_mil_cox_best.pt --split test --output data/metrics_test.json
```

C-index tính bằng **scikit-survival**; score **cao hơn = nguy cơ cao hơn** (thời gian sống ngắn hơn).

---

## Reference statistics + model package (Phase 12–13)

```powershell
python -m evaluation.reference_statistics --checkpoint data/checkpoints/attention_mil_cox_best.pt
python -m packaging.build_model_package --checkpoint data/checkpoints/attention_mil_cox_best.pt
```

Package: `data/model_packages/pathosurv-model-v1/` (weights, metrics, reference stats, model card).

---

## Google Colab — quy trình đề xuất

1. **Clone repo** (source trên GitHub, **không** copy code chỉ trên Drive).
2. Mount Drive cho `data/` và `data/checkpoints/`:

   ```python
   from google.colab import drive
   drive.mount("/content/drive")
   %cd /content/pathosurv-ml
   !pip install -e ".[dev,wsi]"
   ```

3. Copy hoặc sync `data/clinical.json`, manifest GDC, `final_manifest.csv`, WSI vào `data/raw_slides/`.
4. Chạy lần lượt Phase 2→5 (hoặc sync artifact từ máy local).
5. `python -m preprocessing.extract_embeddings` — nên chạy **theo batch slide** (tránh timeout); lưu `.pt` lên Drive.
6. `python -m training.train --model mean_pooling_cox` rồi `attention_mil_cox`.
7. Evaluate + `build_model_package`; tải package về cho PathoSurv Lite web sau này.

Colab Free: giảm `max_patches_per_slide` trong `configs/preprocessing.yaml`, train với `max_epochs` nhỏ trước khi chạy đủ 100 epoch.

---

## Kiểm tra chất lượng

| Bước | Lệnh |
|------|------|
| Cox loss | `pytest tests/test_cox_loss.py -q` |
| Model shapes | `pytest tests/test_model_shapes.py -q` |
| C-index | `pytest tests/test_cindex.py -q` |
| Full unit | `pytest -q` |

---

## Giới hạn nghiên cứu

- ResNet50 ImageNet **không** phải pathology foundation model; chỉ dùng smoke / fallback.
- Metric trên 3 slide hoặc synthetic demo **không** đại diện hiệu năng BLCA.
- PathoSurv Lite web cần model package + cùng preprocessing contract.

Liên quan: [WORKFLOW.md](WORKFLOW.md), [pathosurv_training_ai_requirement.md](../plan/pathosurv_training_ai_requirement.md).
