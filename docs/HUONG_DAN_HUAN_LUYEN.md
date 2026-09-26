# Hướng dẫn huấn luyện PathoSurv Lite

Tài liệu mô tả **train trên cohort đủ WSI** (Colab + GPU) và **smoke train local** có sẵn trong repo.

## Tóm tắt sau WSI preprocessing

```text
extract_embeddings   → ResNet50 frozen (thay TITAN khi có quyền)
pytest test_cox_loss → kiểm tra Cox partial likelihood
train mean_pooling_cox
train attention_mil_cox
evaluation.evaluate  → C-index (scikit-survival)
reference_statistics → percentile nguy cơ trên validation
build_model_package  → pathosurv-model-v1/
```

Smoke end-to-end (local):

```powershell
cd pathosurv-ml
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,wsi]"
python scripts/run_training_smoke.py
```

Smoke train dùng **`--synthetic-demo`** (40 case giả có event/censor) vì 3 WSI smoke thường toàn censored. Embedding **thật** vẫn trích từ WSI đã preprocess vào `data/features/*.pt`.

---

## Điều kiện train cohort thật (TCGA-BLCA)

1. **WSI on disk** — tải theo `final_manifest.csv` (`gdc-client`, đủ dung lượng).
2. **Preprocessing** — `scripts/run_wsi_preprocess_pipeline.py` (hoặc TRIDENT khi tích hợp).
3. **Encoder** — `configs/encoder.yaml`; đồng bộ `embedding_dim` trong `configs/model.yaml` khi đổi encoder.
4. **Không leakage** — chỉ dùng `split` trong manifest; không chọn checkpoint theo test.

---

## Embedding

```powershell
python -m preprocessing.extract_embeddings --max-patches 200
python -m preprocessing.validate_embeddings
```

Output: `data/features/<slide_id>.pt`, `data/embedding_audit.json`.

---

## Train Mean Pooling + Cox

```powershell
python -m training.train --model mean_pooling_cox
```

Checkpoint: `data/checkpoints/mean_pooling_cox_best.pt` · Hyperparameters: `configs/training.yaml`.

---

## Train Attention MIL + Cox

```powershell
python -m training.train --model attention_mil_cox
```

Checkpoint: `data/checkpoints/attention_mil_cox_best.pt`

---

## Đánh giá

```powershell
python -m evaluation.evaluate --checkpoint data/checkpoints/attention_mil_cox_best.pt --split test --output data/metrics_test.json
```

Score **cao hơn = nguy cơ cao hơn** (thời gian sống ngắn hơn).

---

## Reference statistics + model package

```powershell
python -m evaluation.reference_statistics --checkpoint data/checkpoints/attention_mil_cox_best.pt
python -m packaging.build_model_package --checkpoint data/checkpoints/attention_mil_cox_best.pt
```

Package: `data/model_packages/pathosurv-model-v1/`

---

## Google Colab

1. Clone repo (source trên Git, không chỉ Drive).
2. Mount Drive cho `data/` và `data/checkpoints/`.
3. Sync `clinical.json`, manifest GDC, `final_manifest.csv`, WSI vào `data/raw_slides/`.
4. Chạy pipeline theo [WORKFLOW.md](WORKFLOW.md) hoặc sync artifact từ máy local.
5. `extract_embeddings` theo batch; train hai model; evaluate + package.

---

## Kiểm tra chất lượng

| Bước | Lệnh |
|------|------|
| Cox loss | `pytest tests/test_cox_loss.py -q` |
| Model shapes | `pytest tests/test_model_shapes.py -q` |
| C-index | `pytest tests/test_cindex.py -q` |
| Full unit | `pytest -q` |

---

## Giới hạn

- ResNet50 ImageNet không phải pathology foundation model; smoke / fallback.
- Metric trên subset nhỏ hoặc synthetic demo không đại diện BLCA đủ cohort.
- Web PathoSurv Lite dùng model package + cùng preprocessing contract.

Liên quan: [WORKFLOW.md](WORKFLOW.md), [README.md](../README.md).
