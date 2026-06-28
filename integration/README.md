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

## Cách chạy

```powershell
python -m integration.run_pipeline --use-sample-data --to-stage 6 --overwrite
python -m integration.run_pipeline --from-stage 6 --validate-only
python -m integration.run_pipeline --validate-only --input-dir data/intermediate
```

Chạy pipeline thật từ raw media:

```powershell
python -m integration.run_pipeline `
  --project-id demo_01 `
  --videos data/raw/video_01.mp4 `
  --audio data/raw/voiceover.wav `
  --overwrite `
  --fake-embeddings `
  --video-method fixed_window `
  --skip-ui `
  --to-stage 8
```

Chi tiết môi trường, tham số và quy trình debug: `docs/current_pipeline_runbook.md`.

## Cách test

```powershell
python scripts/validate_json.py
python scripts/validate_json.py --input-dir data/intermediate
.\scripts\run_demo.ps1
```

## Tài liệu

- `docs/details/01_system_architecture.md`
- `docs/details/02_data_contract.md`
- `docs/details/12_integration_plan.md`

## Kiểm tra trước khi chạy

```powershell
python scripts/validate_json.py
python scripts/validate_json.py --input-dir data/intermediate
```

## Ranh giới

- Không đổi schema trong code tích hợp.
- Không bỏ qua lỗi validation.

## Giới hạn hiện tại

- `--use-sample-data` chỉ là chế độ contract/demo: Stage 1-5 dùng JSON mẫu,
  Stage 6 chạy planner thật. Render sample chỉ chạy khi path media mẫu tồn tại.
- Stage 7 mặc định chạy validate non-interactive; dùng `--launch-ui` để mở
  Gradio UI.
- Stage 8 đã được gọi từ integration, nhưng MVP ổn định nhất với transition
  `cut`.
