# Developer Guide

Huong dan nay danh cho dev muon hieu repo, sua module, toi uu pipeline hoac
chay full stack local. Luong nguoi dung cuoi nam o [USER_GUIDE.md](USER_GUIDE.md).

## Nguyen Tac Chinh

- Khong doi workflow end-to-end neu khong co ly do ro rang.
- Moi stage giao tiep voi nhau bang JSON artifact trong `data/intermediate/`.
- `timeline.json` la trung tam cua Review UI va Renderer.
- Duong dan runtime trong JSON nen la relative path trong repo.
- Khi sua schema/artifact, cap nhat code, schema, sample va docs lien quan
  trong cung change.

## Cai Moi Truong Dev

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Can co `ffmpeg` va `ffprobe` tren PATH.

Kiem tra nhanh:

```powershell
python scripts\validate_json.py
python -m integration.run_pipeline --use-sample-data --overwrite --from-stage 1 --to-stage 6 --skip-ui
python scripts\validate_json.py --input-dir data/intermediate
```

Hoac:

```powershell
.\scripts\run_demo.ps1
```

## Pipeline Map

| Stage | Module | Input chinh | Output chinh |
| --- | --- | --- | --- |
| 1 | `input_processor` | raw video/audio | `media_metadata.json` |
| 2 | `audio_analyzer` | `media_metadata.json` | `audio_segments.json` |
| 3 | `video_analyzer` | `media_metadata.json` | `clip_metadata.json`, keyframes |
| 4 | `embedding_indexer` | audio segments + clips | `embedding_metadata.json`, vectors/index |
| 5 | `matching_engine` | embeddings + clips + segments | `matching_candidates.json` |
| 6 | `timeline_planner` | candidates + metadata | `timeline.json` |
| 7 | `review_ui` | timeline + candidates | reviewed `timeline.json` |
| 8 | `renderer` | timeline + media | `final_video.mp4`, `render_log.json` |

Entry point tich hop:

```powershell
python -m integration.run_pipeline --help
```

Kaggle entry point:

```powershell
python scripts\kaggle_job.py --help
```

## Chay Full Local

Dung khi can debug module hoac may co du dependency ML:

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

`--fake-embeddings` giup smoke test nhanh, tranh tai/chay CLIP that. Khi can
thu matching that, bo flag nay va dam bao `torch`/`transformers` cai dung cho
may.

## Chay Tung Doan

Stage 1:

```powershell
python -m integration.run_pipeline --from-stage 1 --to-stage 1 --videos data/raw/video_01.mp4 --audio data/raw/voiceover.wav --overwrite
```

Stage 2-3:

```powershell
python -m integration.run_pipeline --from-stage 2 --to-stage 3 --video-method fixed_window --overwrite
```

Stage 4-6:

```powershell
python -m integration.run_pipeline --from-stage 4 --to-stage 6 --fake-embeddings --overwrite
```

Stage 7:

```powershell
python -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

Stage 8:

```powershell
python -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

## Contract Va Sample

Tai lieu contract chinh:

```text
docs/details/02_data_contract.md
```

Schema toi thieu:

```text
docs/schemas/
```

Sample hop le:

```text
docs/samples/
```

Validate sample:

```powershell
python scripts\validate_json.py
```

Validate runtime output:

```powershell
python scripts\validate_json.py --input-dir data/intermediate
```

Khi doi format JSON, hay cap nhat:

1. `docs/details/02_data_contract.md`
2. file schema trong `docs/schemas/`
3. sample JSON trong `docs/samples/`
4. code doc/ghi JSON
5. README/guide lien quan

## Cau Truc Thu Muc

```text
audio_analyzer/       Stage 2
embedding_indexer/    Stage 4
input_processor/      Stage 1
matching_engine/      Stage 5
timeline_planner/     Stage 6
review_ui/            Stage 7
renderer/             Stage 8
video_analyzer/       Stage 3

integration/          orchestration
shared/               path, JSON, validation helpers
scripts/              demo, clean, validate, Kaggle submit
kaggle/               Kaggle runner template
docs/details/         architecture, contract, stage specs
```

## Test Huong Dan

Chay test theo module khi sua module do:

```powershell
python -m pytest audio_analyzer/tests
python -m pytest matching_engine/tests
python -m pytest renderer/tests
python -m pytest review_ui/tests
```

Chay tat ca test:

```powershell
python -m pytest
```

Truoc khi merge/sync, toi thieu nen chay:

```powershell
python scripts\validate_json.py
python -m integration.run_pipeline --use-sample-data --overwrite --from-stage 1 --to-stage 6 --skip-ui
python scripts\validate_json.py --input-dir data/intermediate
```

## Ghi Chu Van Hanh

- `requirements-terminal.txt`: cho nguoi dung cuoi, nhe, dung Kaggle + UI +
  render local.
- `requirements-dev.txt`: cho dev/test/full local.
- `requirements-kaggle.txt`: dependency chay trong Kaggle worker.
- `data/` chi commit `.gitkeep`; media va output la local artifact.
- `.kaggle_work/`, `.gradio/`, `.venv/`, `tmp/`, `runs/` la thu muc tam/local.

## Tai Lieu Sau Hon

- [kaggle_terminal_workflow.md](kaggle_terminal_workflow.md): chi tiet `scripts/kaggle_job.py`.
- [details/01_system_architecture.md](details/01_system_architecture.md): kien truc.
- [details/02_data_contract.md](details/02_data_contract.md): contract chinh.
- `details/03` den `details/10`: spec theo tung stage.
- `*/README.md`: README rieng cua tung module.
