# Renderer

Module Stage 8 — xuất video cuối từ timeline.

## Trách nhiệm

- Validate timeline và media source.
- Cắt, scale/crop, chỉnh speed, ghép clip và transition.
- Dùng voice-over làm audio chính.
- Fail nếu segment có `visual_items = []`.
- Xuất `final_video.mp4` và `render_log.json`.

## Dữ liệu vào

```text
data/intermediate/timeline.json
data/intermediate/media_metadata.json
data/intermediate/clip_metadata.json          (khuyến nghị)
data/intermediate/render_config.json          (optional)
```

Media: video từ `timeline.items[].visual_items[].source_path`; voice-over theo thứ tự CLI → `render_config` → `media_metadata` (Stage 8).

## Dữ liệu ra

```text
data/final/final_video.mp4
data/intermediate/render_log.json
```

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/10_stage_8_rendering.md`
- Schema: `docs/schemas/timeline.schema.md`, `render_config.schema.md`, `render_log.schema.md`
- Mẫu: `docs/samples/timeline_sample.json`, `media_metadata_sample.json`, `render_config_sample.json`, `render_log_sample.json`

## Ranh giới

- Không chọn hoặc xếp hạng clip.
- Render đúng timeline sau khi validation đạt.
