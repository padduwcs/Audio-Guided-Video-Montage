# Timeline Planner

Module Stage 6 — tạo timeline dựng video ban đầu.

## Trách nhiệm

- Chọn visual items cho từng audio segment từ matching candidates.
- Copy `text` chính xác từ `audio_segments.json`.
- Điền metadata timeline (`audio_id`, `render_settings`, `candidates_ref`, flags mặc định).
- Xử lý chênh lệch duration; gán speed, transition, crop mặc định.
- Xuất `timeline.json`.

## Dữ liệu vào

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/media_metadata.json
```

## Dữ liệu ra

```text
data/intermediate/timeline.json
data/intermediate/timeline_planning_log.json   (optional)
```

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/08_stage_6_timeline_planning.md`
- Schema: `docs/schemas/timeline.schema.md`
- Mẫu: `docs/samples/timeline_sample.json`

## Ranh giới

- Không chạy ASR, scene detection, embedding hoặc matching model.
- Không sửa audio segments hoặc render video cuối.
