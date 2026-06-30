# Audio-Guided Video Montage

Repo nay chua pipeline ban tu dong de dung video montage theo audio thuyet minh.
He thong khong sinh video moi; no chon, cat, sap xep va render lai cac clip tu
video nguon co san.

Thanh vien moi nen bat dau tai:

- docs/team_setup_and_full_pipeline.md: setup tu dau, chay Stage 1-6 tren
  Kaggle, review UI, render local.
- docs/current_pipeline_runbook.md: runbook ngan gon theo code hien tai.
- docs/README.md: ban do tai lieu va thu tu doc cho tung vai tro.

## Trang Thai Hien Tai

Repo khong con la skeleton. Cac stage 1-8 deu co implementation va duoc noi qua
`integration.run_pipeline`.

| Stage | Module | Output chinh |
| --- | --- | --- |
| 1 | `input_processor` | `media_metadata.json` |
| 2 | `audio_analyzer` | `audio_segments.json` |
| 3 | `video_analyzer` | `clip_metadata.json` |
| 4 | `embedding_indexer` | `embedding_metadata.json`, vectors/index |
| 5 | `matching_engine` | `matching_candidates.json` |
| 6 | `timeline_planner` | `timeline.json` |
| 7 | `review_ui` | `timeline.json` da review |
| 8 | `renderer` | `final_video.mp4`, `render_log.json` |

## Cau Truc Repo

```text
audio_analyzer/       Stage 2: ASR, segmentation, query enrichment
embedding_indexer/    Stage 4: text/visual embedding va index
input_processor/      Stage 1: normalize media va metadata
matching_engine/      Stage 5: top-k clip candidates
timeline_planner/     Stage 6: tao timeline draft
review_ui/            Stage 7: Gradio review UI va validator
renderer/             Stage 8: ffmpeg renderer
video_analyzer/       Stage 3: scene/fixed-window clips va keyframes

integration/          runner noi cac stage
shared/               JSON/path/contract helpers dung chung
scripts/              bootstrap, validate, demo, Kaggle submit
kaggle/               runner chay tren Kaggle
docs/                 architecture, contract, runbook, team setup
data/                 input/output local; chi commit .gitkeep
```

## Setup Nhanh

Can Python 3.11+ va `ffmpeg`/`ffprobe` tren PATH.

Workflow mac dinh cho thanh vien moi la offload Stage 1-6 len Kaggle bang GPU
va real CLIP embeddings, nen local chi can dependency nhe:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

Neu can dev/test hoac chay Stage 1-6 local:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Smoke Test Contract

```powershell
python scripts\validate_json.py
python -m integration.run_pipeline --use-sample-data --overwrite --from-stage 1 --to-stage 6 --skip-ui
python scripts\validate_json.py --input-dir data/intermediate
```

Hoac dung script:

```powershell
.\scripts\run_demo.ps1
```

## Workflow Khuyen Nghi Cho Nhom

1. Dat video/audio vao `data/raw/`.
2. Chay Stage 1-6 tren Kaggle:

```powershell
.\.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --wait --pull
```

3. Mo Review UI local:

```powershell
.\.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

4. Render video cuoi:

```powershell
.\.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

Video cuoi nam tai `data/final/final_video.mp4`.

## Quy Tac Du Lieu

- Khong commit media, output render, vector, index, model cache.
- Duong dan trong JSON runtime phai la relative path trong repo.
- Contract chinh nam o `docs/details/02_data_contract.md`, schema toi thieu o
  `docs/schemas/`, sample hop le o `docs/samples/`.
- Khi code va docs mau thuan, uu tien code hien tai + data contract, roi cap
  nhat docs ngay.

## Lenh Huu Ich

```powershell
python scripts\validate_json.py
python scripts\validate_json.py --input-dir data/intermediate
.\scripts\bootstrap_data_dirs.ps1
.\scripts\clean_outputs.ps1 -Yes
python -m integration.run_pipeline --help
```
