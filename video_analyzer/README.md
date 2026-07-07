# Video Analyzer

Stage 3 doc `media_metadata.json`, tach clip candidate tu video normalized va
trich keyframe.

## Input

```text
data/intermediate/media_metadata.json
```

Module doc video tu `videos[*].normalized_path` va chi xu ly video co status
`ready` hoac `warning`.

## Output

```text
data/intermediate/clip_metadata.json
data/intermediate/video_analysis_log.json
data/keyframes/*.jpg
```

## Chay Doc Lap

```powershell
python -m video_analyzer.main --media-metadata data/intermediate/media_metadata.json --output-dir data/intermediate --keyframe-dir data/keyframes --method fixed_window --overwrite
```

Dung `--method content` de tach theo scene detection. Dung `--allow-fixed-window-fallback`
neu muon fallback khi scene detection khong tao du clip.

## Test / Validation

```powershell
python -m integration.run_pipeline --from-stage 3 --to-stage 3 --video-method fixed_window --overwrite
python scripts/validate_json.py --input-dir data/intermediate
```

## Tai Lieu

- `docs/details/05_stage_3_video_analysis.md`
- `docs/details/02_data_contract.md`
- `docs/schemas/clip_metadata.schema.md`
- `docs/samples/clip_metadata_sample.json`
