# Renderer

Stage 8 render `timeline.json` thanh video cuoi bang ffmpeg.

## Input

```text
data/intermediate/timeline.json
data/intermediate/media_metadata.json
data/intermediate/render_config.json      optional; integration co the tao lai
```

Video source lay tu `timeline.items[].visual_items[].source_path`. Voice-over
uu tien tham so CLI, sau do `render_config`, sau do `media_metadata.audio.normalized_path`.

## Output

```text
data/final/final_video.mp4
data/intermediate/render_log.json
```

## Chay Qua Integration

```powershell
python -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

## Chay CLI Renderer

```powershell
python -m renderer.cli --timeline data/intermediate/timeline.json --output data/final/final_video.mp4 --log-path data/intermediate/render_log.json
```

## Gioi Han Hien Tai

- MVP on dinh nhat voi transition `cut`.
- Renderer fail neu timeline item khong co `visual_items` renderable.
- Can `ffmpeg` va `ffprobe` tren PATH, hoac truyen path qua CLI/integration.

## Test / Validation

```powershell
pytest renderer/tests/
python scripts/validate_json.py --input-dir data/intermediate
```

## Tai Lieu

- `docs/details/10_stage_8_rendering.md`
- `docs/details/02_data_contract.md`
- `docs/schemas/timeline.schema.md`
- `docs/schemas/render_log.schema.md`
