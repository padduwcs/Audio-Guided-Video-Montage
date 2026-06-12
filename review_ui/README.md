# Review UI

Module Stage 7 — review và chỉnh timeline trước khi render.

## Trách nhiệm

- Hiển thị segment, transcript, clip đang chọn, score, confidence và top-k candidate.
- Cho phép đổi clip và chỉnh tham số timeline được phép.
- Ghi đè `timeline.json` (cập nhật `updated_at`).

## Dữ liệu vào

```text
data/intermediate/timeline.json
data/intermediate/matching_candidates.json
data/intermediate/clip_metadata.json
data/intermediate/audio_segments.json
data/intermediate/media_metadata.json
```

Media preview: voice-over từ `media_metadata.audio.normalized_path`; video từ `visual_items[].source_path`.

## Dữ liệu ra

```text
data/intermediate/timeline.json
data/intermediate/review_ui_log.json          (optional)
data/intermediate/timeline.before_review.json (backup, optional)
```

MVP ghi đè `timeline.json` tại cùng path.

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/09_stage_7_review_ui.md`
- Schema: `docs/schemas/timeline.schema.md`
- Mẫu: `docs/samples/timeline_sample.json` và các sample liên quan trong `docs/samples/`

## Cách test (sẽ bổ sung khi có code)

- Input mẫu: `docs/samples/timeline_sample.json`, `matching_candidates_sample.json`, `clip_metadata_sample.json`, `audio_segments_sample.json`, `media_metadata_sample.json`
- Validate timeline sau chỉnh: `python scripts/validate_json.py --input-dir data/intermediate`

## Ranh giới

- Không render video, không sửa schema timeline.
- Không sửa `matching_candidates.json`, `clip_metadata.json`, `audio_segments.json`.
- Không chạy lại ASR, video analysis, embedding hoặc matching.
