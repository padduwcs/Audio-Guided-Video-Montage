# Matching Engine

Module Stage 5 — truy xuất và xếp hạng top-k clip cho mỗi audio segment.

## Trách nhiệm

- Tính độ tương đồng ngữ nghĩa và kết hợp score phụ (duration, quality, continuity, diversity, penalty).
- Chọn clip mặc định; xuất `matching_candidates.json` (`top_k = 5`).
- Xuất `matching_engine_log.json`.

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

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/07_stage_5_matching_engine.md`
- Schema: `docs/schemas/matching_candidates.schema.md`
- Mẫu: `docs/samples/matching_candidates_sample.json`

## Ranh giới

- Không tạo `timeline.json` hoặc render video.
- Không sửa `clip_metadata.json`.
