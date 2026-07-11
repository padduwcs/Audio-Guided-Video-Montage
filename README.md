# Audio-Guided Video Montage

Tạo video montage từ **video nguồn có sẵn** và **audio/voice-over**.
Hệ thống không sinh video mới; nó phân tích audio, chọn/cắt/sắp xếp clip từ
footage, cho người dùng review, rồi render video cuối.

## Bắt Đầu Nhanh

Người dùng mới nên đọc:

```text
docs/USER_GUIDE.md
```

Luồng sử dụng:

```text
Cài Git + Conda
-> Clone repo
-> Tạo môi trường bằng environment-terminal.yml
-> Mở Launcher UI
-> Chọn video/audio
-> Nhập Kaggle API key
-> Tạo bản nháp
-> Chỉnh sửa
-> Xuất video
```

Lệnh chạy sau khi đã cài Conda:

```bash
conda env create -f environment-terminal.yml
conda activate audio-montage
python -B -m review_ui.launcher
```

Video cuối nằm ở:

```text
data/final/final_video.mp4
```

## Dành Cho Dev

Cài môi trường đầy đủ:

```bash
conda env create -f environment-dev.yml
conda activate audio-montage-dev
```

Hoặc dùng pip:

```bash
python -m pip install -r requirements-dev.txt
```

Tài liệu chính:

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): hướng dẫn cho người dùng cuối.
- [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md): hướng dẫn cho dev.
- [docs/details/02_data_contract.md](docs/details/02_data_contract.md): data contract.
- [docs/kaggle_terminal_workflow.md](docs/kaggle_terminal_workflow.md): debug Kaggle bằng terminal.

## Pipeline

| Stage | Module | Output chính |
| --- | --- | --- |
| 1 | `input_processor` | `media_metadata.json` |
| 2 | `audio_analyzer` | `audio_segments.json` |
| 3 | `video_analyzer` | `clip_metadata.json` |
| 4 | `embedding_indexer` | `embedding_metadata.json` |
| 5 | `matching_engine` | `matching_candidates.json` |
| 6 | `timeline_planner` | `timeline.json` |
| 7 | `review_ui` | timeline đã review |
| 8 | `renderer` | `final_video.mp4` |

Entry point chính:

```text
integration.run_pipeline
```

Người dùng cuối chủ yếu đi qua:

```text
review_ui.launcher
```

## Cấu Trúc Repo

```text
audio_analyzer/       Stage 2
embedding_indexer/    Stage 4
input_processor/      Stage 1
matching_engine/      Stage 5
timeline_planner/     Stage 6
review_ui/            Stage 7 + Launcher UI
renderer/             Stage 8
video_analyzer/       Stage 3

integration/          runner nối các stage
shared/               helper dùng chung
scripts/              script chạy local/Kaggle/validate
kaggle/               runner chạy trên Kaggle
docs/                 tài liệu
data/                 input/output local, chỉ commit .gitkeep
```

## Ghi Nhớ

- Không commit media, output render, model cache, vector hoặc index.
- `data/` là dữ liệu runtime local.
- Kaggle Dataset/Kernel phải được tạo từ Launcher hoặc `scripts/kaggle_job.py`.
- Không bấm Run thủ công trên Kaggle web cho kernel do repo generate.
