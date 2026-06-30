# Kaggle Terminal Workflow

Tai lieu nay mo ta cach chay pipeline tren Kaggle bang terminal, khong can mo
web de upload/download moi lan chay.

## 1. Dieu kien ban dau

- Da co `kaggle.json` tai `%USERPROFILE%\.kaggle\kaggle.json`.
- Da cai Kaggle CLI trong `.venv`.
- File input hien tai:

```text
data/raw/vd00_CP_overview.mp4
data/raw/vd00_CP_overview.mp3
```

## 2. Lenh chay nhanh

Tu cmd, dung:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --wait --pull
```

Lenh mac dinh se dung:

```text
username: doc tu KAGGLE_USERNAME hoac %USERPROFILE%\.kaggle\kaggle.json
dataset: audio-guided-video-montage-input
kernel: audio-guided-video-montage-runner
video: data/raw/vd00_CP_overview.mp4
audio: data/raw/vd00_CP_overview.mp3
to-stage: 6
fake embeddings: co
transfer mode: dataset
ASR device/compute: cpu + int8
```

## 3. Lenh day du tuong duong

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --username <your_kaggle_username> --project-id demo_01 --videos data\raw\vd00_CP_overview.mp4 --audio data\raw\vd00_CP_overview.mp3 --to-stage 6 --fake-embeddings --wait --pull
```

Script se tu dong:

```text
1. Tao active package moi trong .kaggle_work/packages/job_*/
2. Copy raw media vao dataset/raw/
3. Copy source code vao dataset/project_source_*/
4. Ghi kaggle_job_config.json kem ten source_dir moi
5. Tao/cap nhat private Kaggle Dataset
6. Doi dataset thay config va raw media
7. Push Kaggle Kernel runner nho, attach dataset vua tao
8. Neu Kaggle attach dataset cham, tu retry push kernel
9. Chay kernel tren Kaggle
10. Doi job xong neu co --wait
11. Tai output ve neu co --pull
12. Copy output vao data/intermediate, data/normalized, data/keyframes
```

Runner tren Kaggle se copy raw media tu `/kaggle/input/...` vao
`/kaggle/working/audio-guided-video-montage/data/raw/` truoc khi chay Stage 1,
de cac module thay path nam trong project root.

Mac dinh runner chay faster-whisper bang `cpu` + `int8`. Ly do: mot so phien
Kaggle co hien CUDA nhung backend faster-whisper/ctranslate2 lai bao loi voi
`float16`. Khi can uu tien chay on dinh tu dau den cuoi, giu mac dinh nay.
Sau khi pipeline da chay muot, co the thu GPU bang lenh ro rang:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --device cuda --compute-type int8 --wait --pull
```

## 4. Chay tung buoc de debug

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py package
.venv\Scripts\python.exe -B scripts\kaggle_job.py push-dataset
.venv\Scripts\python.exe -B scripts\kaggle_job.py run
.venv\Scripts\python.exe -B scripts\kaggle_job.py status
.venv\Scripts\python.exe -B scripts\kaggle_job.py pull
```

Neu kernel loi, xem log:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py logs
```

## 5. Output mong doi sau Stage 6

```text
data/intermediate/media_metadata.json
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/timeline.json
```

Sau khi co timeline, co the review local:

```bat
.venv\Scripts\python.exe -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui
```

## 6. Neu muon doi file input

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\video_khac.mp4 --audio data\raw\audio_khac.mp3 --wait --pull
```

## 7. Luu y bao mat

- Khong commit `kaggle.json`.
- Thu muc `.kaggle_work/` chi la file tam de upload/download va da duoc ignore.
- Mac dinh dung dataset mode vi Kaggle API co gioi han kich thuoc file code kernel.
- Kernel bundle mode chi hop voi input rat nho. Neu can thu:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --transfer-mode kernel --wait --pull
```

## 8. Loi dataset chua attach kip

Neu thay:

```text
The following are not valid dataset sources
```

nghia la Kaggle vua tao dataset xong nhung chua index kip. Script se tu retry
push kernel. Neu van loi, doi mot lat roi chay lai lenh:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --wait --pull
```
