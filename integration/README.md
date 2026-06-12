# Integration

Lớp điều phối pipeline — nối output các module theo thứ tự đã thống nhất.

## Trách nhiệm

- Chạy module theo pipeline; validate JSON trước mỗi bước phụ thuộc.
- Giữ artifact trong `data/intermediate/`; hỗ trợ chạy demo với sample data.

## Luồng pipeline

```text
Input Processor
→ Audio Analyzer + Video Analyzer
→ Embedding Indexer
→ Matching Engine
→ Timeline Planner
→ Review UI
→ Renderer
```

## Artifact chính

```text
data/intermediate/media_metadata.json
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/timeline.json
data/intermediate/render_log.json
data/final/final_video.mp4
```

Log debug (optional): `*_log.json` từng stage, gồm `timeline_planning_log.json` và `review_ui_log.json`.

`render_config.json` optional nếu tách cấu hình render khỏi `timeline.render_settings`.

## Tài liệu

- `docs/details/01_system_architecture.md`
- `docs/details/02_data_contract.md`
- `docs/details/12_integration_plan.md`

## Cách test (sẽ bổ sung khi có code)

- Validate samples: `python scripts/validate_json.py`
- Validate runtime: `python scripts/validate_json.py --input-dir data/intermediate`

## Kiểm tra trước khi chạy

```bash
python scripts/validate_json.py
# Sau khi có output runtime trong data/intermediate/:
python scripts/validate_json.py --input-dir data/intermediate
```

## Ranh giới

- Không đổi schema trong code tích hợp.
- Không bỏ qua lỗi validation.
