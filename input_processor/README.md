# Input Processor

Stage 1 normalize raw media va tao metadata dung chung cho cac stage sau.

## Input

```text
data/raw/*.mp4|*.mov|*.mkv
data/raw/*.mp3|*.wav|*.m4a
```

## Output

```text
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
data/normalized/*
```

Tat ca path ghi vao JSON la relative path trong repo.

## Chay Doc Lap

```powershell
python -m input_processor.main --project-id demo_01 --videos data/raw/my_video.mp4 --audio data/raw/my_voice.mp3 --output-dir data --overwrite
```

Tham so huu ich:

- `--ffmpeg-path`, `--ffprobe-path`: chi ro binary neu khong nam tren PATH.
- `--target-fps`, `--audio-sample-rate`, `--audio-channels`: cau hinh normalize.
- `--no-normalize-video`, `--no-normalize-audio`: debug nhanh khi media da san sang.

## Test / Validation

```powershell
python -m integration.run_pipeline --from-stage 1 --to-stage 1 --videos data/raw/my_video.mp4 --audio data/raw/my_voice.mp3 --overwrite
python scripts/validate_json.py --input-dir data/intermediate
```

## Tai Lieu

- `docs/details/03_stage_1_input_processing.md`
- `docs/details/02_data_contract.md`
- `docs/schemas/media_metadata.schema.md`
- `docs/samples/media_metadata_sample.json`
