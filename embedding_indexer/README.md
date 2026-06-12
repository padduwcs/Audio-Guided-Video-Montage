# Embedding Indexer

Module Stage 4 — embedding text/visual và index truy xuất.

## Trách nhiệm

- Text embedding cho mỗi segment (`source_text` ưu tiên `translated_query`).
- Visual embedding cho clip/keyframe (`status` = `usable` hoặc `low_quality`).
- Lưu vector và index; xuất `embedding_metadata.json`.

## Dữ liệu vào

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/keyframes/*.jpg
```

## Dữ liệu ra

```text
data/intermediate/embedding_metadata.json
data/intermediate/embeddings/
data/intermediate/index/
data/intermediate/embedding_indexing_log.json
```

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/06_stage_4_embedding_indexing.md`
- Schema: `docs/schemas/embedding_metadata.schema.md`
- Mẫu: `docs/samples/embedding_metadata_sample.json`, `docs/samples/embedding_index_sample/`

## Cách test (sẽ bổ sung khi có code)

- Input mẫu: `docs/samples/audio_segments_sample.json`, `clip_metadata_sample.json`
- Output mẫu: `docs/samples/embedding_metadata_sample.json`
- Validate: `python scripts/validate_json.py --input-dir data/intermediate`

## Ranh giới

- Không sửa transcript/query.
- Không xếp hạng clip hoặc tạo `matching_candidates.json`.
