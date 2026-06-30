# Review UI

Stage 7 validate va review timeline truoc khi render. UI dung Gradio; trong
integration, Stage 7 mac dinh chay validation non-interactive va chi mo UI khi
co `--launch-ui`.

## Input

```text
data/intermediate/timeline.json
data/intermediate/matching_candidates.json
data/intermediate/clip_metadata.json
data/intermediate/audio_segments.json
data/intermediate/media_metadata.json
```

## Output

```text
data/intermediate/timeline.json                 cap nhat khi Save
data/intermediate/timeline.before_review.json   backup mac dinh neu khong --no-ui-backup
data/intermediate/review_ui_log.json            optional
```

## Chay Qua Integration

Validate Stage 7 khong mo UI:

```powershell
python -m integration.run_pipeline --from-stage 7 --to-stage 7
```

Mo UI:

```powershell
python -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

## Chay CLI Truc Tiep

```powershell
python -m review_ui.cli --project-id demo_01 --timeline data/intermediate/timeline.json --matching-candidates data/intermediate/matching_candidates.json --clip-metadata data/intermediate/clip_metadata.json --audio-segments data/intermediate/audio_segments.json --media-metadata data/intermediate/media_metadata.json --host 127.0.0.1 --port 7860
```

Tham so huu ich:

- `--readonly`: chi xem, khong save.
- `--no-backup`: khong tao `timeline.before_review.json`.
- `--log-path`: ghi log review.

## Pham Vi Chinh Sua

Review UI chi duoc sua cac field review/timeline duoc phep:

- doi clip tu top-k candidates
- tao visual item tu candidate khi segment thieu visual
- chinh `clip_start`, `clip_end`, `speed`
- chinh transition/crop/volume/locked/notes/needs_review
- cap nhat `updated_at` khi save

Review UI khong sua upstream files: `matching_candidates.json`,
`clip_metadata.json`, `audio_segments.json`, `media_metadata.json`.

## Test / Validation

```powershell
pytest review_ui/tests/
python scripts/validate_json.py --input-dir data/intermediate
```

## Tai Lieu

- `docs/details/09_stage_7_review_ui.md`
- `docs/details/02_data_contract.md`
- `docs/schemas/timeline.schema.md`
- `docs/samples/timeline_sample.json`
