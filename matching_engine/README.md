# Matching Engine

Module Stage 5 — truy xuất và xếp hạng top-k clip cho mỗi audio segment.

## Trách nhiệm

- Tính độ tương đồng ngữ nghĩa và kết hợp score phụ (duration, quality, continuity, diversity, penalty).
- Chọn clip mặc định; xuất `matching_candidates.json` (`top_k = 5`).
- Xuất `matching_engine_log.json`.

## Cấu trúc module

```text
matching_engine/
├── __init__.py       Package marker
├── config.py         Config nội bộ (weights, penalties, thresholds)
├── io_utils.py       Load/validate input, ghi output
├── scorer.py         Hàm tính score (semantic, duration_fit, final_score, confidence)
├── engine.py         Logic chính (load embedding, filter, score, top-k, fallback)
└── main.py           Entry point + CLI argparse
```

## Dữ liệu vào

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/embeddings/
data/intermediate/index/
```

## Dữ liệu ra

```text
data/intermediate/matching_candidates.json
data/intermediate/matching_engine_log.json
```

## Cách chạy

```bash
python -m matching_engine.main \
  --audio-segments data/intermediate/audio_segments.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --embedding-metadata data/intermediate/embedding_metadata.json \
  --output-dir data/intermediate \
  --top-k 5
```

Tùy chọn:
- `--overwrite`: Ghi đè output nếu đã tồn tại.
- `--config path/to/config.json`: Override config mặc định.
- `--top-k N`: Đổi số lượng candidate (default: 5).

## Cách test

Test với dữ liệu mẫu (cần có embedding `.npy` files):

```bash
# Chạy Embedding Indexer trước để tạo embeddings
python -m embedding_indexer.main \
  --audio-segments docs/samples/audio_segments_sample.json \
  --clip-metadata docs/samples/clip_metadata_sample.json \
  --output-dir data/intermediate \
  --embedding-dir data/intermediate/embeddings \
  --index-dir data/intermediate/index \
  --overwrite --fake

# Chạy Matching Engine
python -m matching_engine.main \
  --audio-segments docs/samples/audio_segments_sample.json \
  --clip-metadata docs/samples/clip_metadata_sample.json \
  --embedding-metadata data/intermediate/embedding_metadata.json \
  --output-dir data/intermediate \
  --overwrite
```

Validate schema:

```bash
python scripts/validate_json.py --input-dir data/intermediate
```

## Thư viện cần cài

```text
numpy
```

`faiss-cpu` optional — module dùng trực tiếp `.npy` vectors, không bắt buộc FAISS index.

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/07_stage_5_matching_engine.md`
- Schema: `docs/schemas/matching_candidates.schema.md`
- Mẫu: `docs/samples/matching_candidates_sample.json`

## Ranh giới

- Không tạo `timeline.json` hoặc render video.
- Không sửa `clip_metadata.json`.
- Không tạo embedding mới — chỉ đọc output Stage 4.

## Giới hạn hiện tại

- `continuity_score` và `diversity_score` chưa triển khai (output `null`).
- Chưa dùng FAISS index search (brute-force tất cả vectors).
- Repetition penalty chỉ track segment liền trước.
