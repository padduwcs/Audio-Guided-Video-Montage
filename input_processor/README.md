# Input Processor

Module Stage 1 — chuẩn hóa media đầu vào và tạo metadata dùng chung.

## Trách nhiệm

- Kiểm tra và trích metadata video/audio thô.
- Chuẩn hóa media; gán `video_id`, `audio_id` ổn định.
- Xuất `media_metadata.json` và `input_processing_log.json`.

## Dữ liệu vào

```text
data/raw/video_*.mp4
data/raw/video_*.mov
data/raw/video_*.mkv
data/raw/voiceover.*
```

## Dữ liệu ra

```text
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
data/normalized/video_*.mp4
data/normalized/voiceover.wav
```

## Tài liệu

- Data Contract: `docs/details/02_data_contract.md`
- Stage spec: `docs/details/03_stage_1_input_processing.md`
- Schema: `docs/schemas/media_metadata.schema.md`
- Mẫu: `docs/samples/media_metadata_sample.json`

## Ranh giới

- Không chạy ASR hoặc tách clip candidate.
- Không cắt khoảng lặng voice-over theo cách làm thay đổi timestamp.
