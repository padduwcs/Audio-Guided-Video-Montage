# Audio-Guided Video Montage

Tao video montage tu **video nguon co san** va **audio thuyet minh**.
He thong khong sinh video moi; no phan tich audio, chon/cat/sap xep clip tu
footage, cho nguoi dung review, roi render thanh mot file video cuoi.

## Nen Bat Dau O Dau?

Neu ban chi muon clone repo va tao video:

1. Doc [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
2. Chay Launcher UI local
3. Chon video, voice-over va cau hinh Kaggle tren UI
4. Bam tao ban nhap, chinh sua, roi xuat video

Neu ban la dev hoac muon toi uu pipeline:

1. Doc [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
2. Doc data contract: [docs/details/02_data_contract.md](docs/details/02_data_contract.md)
3. Doc spec cua module minh phu trach trong `docs/details/`

## Workflow Cho Nguoi Dung

Can co Python 3.11+, FFmpeg/FFprobe va Kaggle API key.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

Mo Launcher UI:

```powershell
.\.venv\Scripts\python.exe -B -m review_ui.launcher
```

Trong trinh duyet, lam theo 3 tab: `Bat dau`, `Chinh sua`, `Xuat video`.
Neu cong `7860` dang ban, mo URL ma terminal in ra.

Thanh pham nam tai:

```text
data/final/final_video.mp4
```

## Workflow Cho Dev

Cai full dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Smoke test contract va sample pipeline:

```powershell
python scripts\validate_json.py
python -m integration.run_pipeline --use-sample-data --overwrite --from-stage 1 --to-stage 6 --skip-ui
python scripts\validate_json.py --input-dir data/intermediate
```

Hoac chay script:

```powershell
.\scripts\run_demo.ps1
```

## Pipeline

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

Entry point chinh la:

```text
integration.run_pipeline
```

Kaggle workflow goi cung pipeline do thong qua:

```text
scripts/kaggle_job.py
```

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
docs/                 user guide, developer guide, architecture, contract
data/                 input/output local; chi commit .gitkeep
```

## Quy Tac Du Lieu

- Khong commit media, output render, vector, index, model cache.
- Runtime JSON dung relative path trong repo.
- `timeline.json` la artifact trung tam cho Review UI va Renderer.
- Khi code va docs mau thuan, uu tien code hien tai + data contract, roi cap
  nhat docs ngay.
