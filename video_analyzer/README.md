# Video Analyzer

Module Stage 3 — tạo tập clip candidate từ video nguồn.

## Trách nhiệm

- Đọc video qua `media_metadata.json` → `videos[*].normalized_path`.
- Chỉ xử lý video có `status` là `ready` hoặc `warning`.
- Phát hiện scene/shot, tạo clip, trích keyframe, tính quality score.
- Xuất `clip_metadata.json` với `status` và `source_path` trên mỗi clip.
- Xuất `video_analysis_log.json` và ảnh keyframe.

## Dữ liệu vào

```text
data/intermediate/media_metadata.json
```

## Dữ liệu ra

```text
data/intermediate/clip_metadata.json
data/intermediate/video_analysis_log.json
data/keyframes/*.jpg
```

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/05_stage_3_video_analysis.md`
- Schema: `docs/schemas/clip_metadata.schema.md`
- Mẫu: `docs/samples/clip_metadata_sample.json`

## Cách test (sẽ bổ sung khi có code)

- Input mẫu: `docs/samples/media_metadata_sample.json`
- Output mẫu: `docs/samples/clip_metadata_sample.json`
- Validate: `python scripts/validate_json.py --input-dir data/intermediate`

## Ranh giới

- Không matching ngữ nghĩa với audio.
- Không tạo embedding hoặc `timeline.json`.
