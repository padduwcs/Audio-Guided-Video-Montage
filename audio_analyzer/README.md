# Audio Analyzer

Module Stage 2 — phân tích audio thuyết minh.

## Trách nhiệm

- Đọc voice-over qua `media_metadata.json` → `audio.normalized_path`.
- Chỉ chạy khi `audio.status` là `ready` hoặc `warning`.
- Chạy ASR hoặc nạp transcript có sẵn.
- Tạo audio segment có timestamp, `query`, `translated_query`.
- Đánh dấu segment cần review khi ASR không chắc chắn.
- Xuất `audio_segments.json` và `audio_analysis_log.json`.

## Dữ liệu vào

```text
data/intermediate/media_metadata.json
```

## Dữ liệu ra

```text
data/intermediate/audio_segments.json
data/intermediate/audio_analysis_log.json
```

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/04_stage_2_audio_analysis.md`
- Schema: `docs/schemas/audio_segments.schema.md`
- Mẫu: `docs/samples/audio_segments_sample.json`

## Cách test (sẽ bổ sung khi có code)

- Input mẫu: `docs/samples/media_metadata_sample.json`
- Output mẫu: `docs/samples/audio_segments_sample.json`
- Validate: `python scripts/validate_json.py --input-dir data/intermediate`

## Ranh giới

- Không phân tích video nguồn.
- Không chọn clip hoặc tạo `matching_candidates.json` / `timeline.json`.
