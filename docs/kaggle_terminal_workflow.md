# Kaggle Terminal Workflow

Tai lieu nay mo ta cach dung `scripts/kaggle_job.py` de chay Stage 1-6 tren
Kaggle tu terminal. Khong can upload/download thu cong tren web.

## Dieu Kien

- Da cai dependency local bang `requirements-terminal.txt`.
- Da co Kaggle API token tai `%USERPROFILE%\.kaggle\kaggle.json`, hoac set
  `KAGGLE_USERNAME` va cau hinh Kaggle CLI tuong duong.
- Raw media nam trong `data/raw/`.
- Khong can file media mac dinh trong repo; luon truyen ro `--videos` va
  `--audio`.

Kiem tra:

```bat
.venv\Scripts\kaggle.exe --version
.venv\Scripts\kaggle.exe datasets list --mine
```

## Lenh Chay Khuyen Nghi

Mac dinh, lenh duoi day dung fake embeddings de kiem tra pipeline nhanh va on
dinh:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --device cpu --compute-type int8 --wait --pull
```

Neu muon matching that bang CLIP va chay ASR/CLIP tren GPU Kaggle:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --real-embeddings --device cuda --compute-type float16 --wait --pull
```

Nhieu video:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\video1.mp4 data\raw\video2.mp4 --audio data\raw\voice.mp3 --device cpu --compute-type int8 --wait --pull
```

Neu muon chi ro username:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --username <your_kaggle_username> --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --wait --pull
```

Script se fail ro rang neu thieu username, `--videos`, hoac `--audio`.

## Script Lam Gi

```text
1. Tao package tam trong .kaggle_work/packages/job_*/
2. Copy raw media vao package dataset
3. Copy source code hien tai vao package dataset
4. Ghi kaggle_job_config.json
5. Tao/cap nhat private Kaggle Dataset cua username hien tai
6. Doi dataset attachable
7. Push Kaggle Kernel runner va attach dataset
8. Chay integration.run_pipeline Stage 1-6 tren Kaggle
9. Neu co --wait, doi kernel xong
10. Neu co --pull, tai output ve data/
```

Output duoc copy ve:

```text
data/intermediate/
data/normalized/
data/keyframes/
```

## Debug Tung Buoc

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py package --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3
.venv\Scripts\python.exe -B scripts\kaggle_job.py push-dataset
.venv\Scripts\python.exe -B scripts\kaggle_job.py run
.venv\Scripts\python.exe -B scripts\kaggle_job.py status
.venv\Scripts\python.exe -B scripts\kaggle_job.py logs
.venv\Scripts\python.exe -B scripts\kaggle_job.py pull
```

## Output Mong Doi Sau Stage 6

```text
data/intermediate/media_metadata.json
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/timeline.json
```

Sau do review local:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

Render local:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

## Ghi Chu

- Mac dinh script dung fake embeddings de Stage 1-6 chay nhanh va on dinh.
- Dung `--real-embeddings --device cuda --compute-type float16` khi muon thu
  CLIP that va GPU. Neu Kaggle bao loi CUDA/float16, quay lai
  `--device cpu --compute-type int8`.
- Mac dinh transfer mode la `dataset`; mode nay phu hop media lon hon kernel
  embed mode.
- `.kaggle_work/` chi la thu muc tam va da duoc ignore.
