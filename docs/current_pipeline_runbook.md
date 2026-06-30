# Current Pipeline Runbook

Tai lieu nay mo ta cach cai moi truong va chay pipeline theo code hien tai.
Neu README cu mau thuan voi file nay, uu tien file nay va code trong cac
module.

## 1. Trang thai that hien tai

Repo hien khong con la skeleton. Cac stage 1-8 deu co code rieng:

| Stage | Module | Trang thai code |
| --- | --- | --- |
| 1 | `input_processor` | Co CLI/API that, dung `ffmpeg`/`ffprobe`, xuat `media_metadata.json`. |
| 2 | `audio_analyzer` | Co pipeline ASR `faster-whisper`, segmentation, query enrichment, xuat `audio_segments.json`. |
| 3 | `video_analyzer` | Co scene/fixed-window detection, trich keyframe, xuat `clip_metadata.json`. |
| 4 | `embedding_indexer` | Co CLIP backend that va `--fake` backend de smoke test nhanh. |
| 5 | `matching_engine` | Co scoring/top-k/fallback/DP assignment, xuat `matching_candidates.json`. |
| 6 | `timeline_planner` | Co planner that, da duoc integration runner goi truc tiep. |
| 7 | `review_ui` | Co validate CLI va Gradio UI tuy chon. Integration mac dinh validate non-interactive. |
| 8 | `renderer` | Co ffmpeg renderer, ho tro MVP tot nhat voi transition `cut`. |

`integration.run_pipeline` hien da goi module that theo tung stage. Rieng
`--use-sample-data` chi copy artifact mau cho stage 1-5 de test contract nhanh;
khong thay the duoc render that vi sample path media co the khong ton tai.

## 2. Cai moi truong

Can cai Python 3.11 hoac 3.12 va system `ffmpeg`/`ffprobe`.
Khong nen dung Python 3.13 voi requirements hien tai vi `torch==2.5.1`
khong co wheel Windows phu hop cho Python 3.13.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Bash:

```bash
python -m venv .venv
./.venv/bin/python -m ensurepip --upgrade
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements-dev.txt
```

Kiem tra cong cu he thong:

```powershell
ffmpeg -version
ffprobe -version
```

Ghi chu:

- `torch` trong `requirements.txt` la ban mac dinh. Neu may dung CUDA, cai ban
  `torch` phu hop theo huong dan cua PyTorch roi moi chay CLIP that.
- Smoke test nen dung `--fake-embeddings` truoc de tranh phu thuoc model CLIP,
  GPU, hoac tai model lon.

## 3. Lenh kiem tra nhanh

Validate sample contract:

```powershell
python scripts\validate_json.py
```

Chay sample pipeline toi Timeline Planner:

```powershell
python -m integration.run_pipeline --use-sample-data --overwrite --from-stage 1 --to-stage 6 --skip-ui
```

Lenh tren phai tao/validate:

```text
data/intermediate/media_metadata.json
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/timeline.json
```

## 4. Chay pipeline that tu raw media

Dat file input vao `data/raw/`, vi du:

```text
data/raw/video_01.mp4
data/raw/voiceover.wav
```

Smoke test end-to-end, dung embedding gia lap de tranh model CLIP:

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

Output mong doi:

```text
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
data/intermediate/audio_segments.json
data/intermediate/audio_analysis_log.json
data/intermediate/clip_metadata.json
data/intermediate/video_analysis_log.json
data/intermediate/embedding_metadata.json
data/intermediate/embedding_indexing_log.json
data/intermediate/matching_candidates.json
data/intermediate/matching_engine_log.json
data/intermediate/timeline.json
data/intermediate/timeline_planning_log.json
data/intermediate/render_config.json
data/intermediate/render_log.json
data/final/final_video.mp4
```

Neu muon dung CLIP that, bo `--fake-embeddings`. Khi do can cai dung `torch`,
`transformers`, `pillow`, va model co the duoc tai lan dau.

Neu muon mo UI review truoc render:

```powershell
python -m integration.run_pipeline `
  --project-id demo_01 `
  --videos data/raw/video_01.mp4 `
  --audio data/raw/voiceover.wav `
  --overwrite `
  --fake-embeddings `
  --video-method fixed_window `
  --from-stage 1 `
  --to-stage 7 `
  --launch-ui

python -m integration.run_pipeline --from-stage 8 --to-stage 8 --skip-ui
```

## 5. Chay tung stage

Stage 1:

```powershell
python -m integration.run_pipeline --from-stage 1 --to-stage 1 --videos data/raw/video_01.mp4 --audio data/raw/voiceover.wav --overwrite
```

Stage 2:

```powershell
python -m integration.run_pipeline --from-stage 2 --to-stage 2 --overwrite
```

Stage 3:

```powershell
python -m integration.run_pipeline --from-stage 3 --to-stage 3 --video-method fixed_window --overwrite
```

Stage 4-6:

```powershell
python -m integration.run_pipeline --from-stage 4 --to-stage 6 --fake-embeddings --overwrite
```

Stage 8 render lai tu timeline da co:

```powershell
python -m integration.run_pipeline --from-stage 8 --to-stage 8 --skip-ui --overwrite
```

## 6. Validation

`scripts/validate_json.py --input-dir data/intermediate` can mot bo contract day
du, gom ca `render_config.json` va `render_log.json`. Vi vay integration runner
chi chay full validation khi cac file contract deu ton tai.

Khi debug, uu tien kiem tra theo thu tu:

```text
media_metadata.json
audio_segments.json
clip_metadata.json
embedding_metadata.json
matching_candidates.json
timeline.json
render_log.json
```

## 7. Gioi han can nho

- Renderer MVP nen dung `transition = cut`. `fade/crossfade` multi-segment chua
  duoc hoan thien.
- `matching_engine` hien de `continuity_score` va `diversity_score` la `null`.
- `audio_analyzer.translated_query` hien chu yeu de `null`; Stage 4 uu tien
  `translated_query` neu co, fallback sang `query`.
- Sample JSON dung de test contract, khong dam bao render duoc neu path media
  mau khong ton tai tren may.
