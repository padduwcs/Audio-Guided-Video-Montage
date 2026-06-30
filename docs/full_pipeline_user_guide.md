# Full Pipeline User Guide

> Team members who clone the repo on a new machine should start with
> [`team_setup_and_full_pipeline.md`](team_setup_and_full_pipeline.md). That
> guide avoids machine-specific paths and includes install/setup steps.

Tai lieu nay huong dan chay mot vi du hoan chinh tu file video/audio dau vao
den file video cuoi cung. Huong dan nay uu tien workflow Windows CMD + Kaggle
offload cho Stage 1-6, sau do Review UI va render local.

Neu README hoac docs cu mau thuan voi file nay, uu tien code hien tai va file
nay.

## 1. Tong Quan Luong Chay

```text
data/raw/*.mp4 + data/raw/*.mp3
        |
        v
Kaggle Stage 1-6
        |
        v
data/intermediate/timeline.json
        |
        v
Review UI Stage 7
        |
        v
Render Stage 8
        |
        v
data/final/final_video.mp4
```

Stage 1-6 chay tren Kaggle de giam tai cho may yeu:

| Stage | Viec lam | Output chinh |
| --- | --- | --- |
| 1 | Doc va normalize input media | `media_metadata.json`, `data/normalized/*` |
| 2 | ASR va tach audio segments | `audio_segments.json` |
| 3 | Tach clip/keyframe tu video | `clip_metadata.json`, `data/keyframes/*` |
| 4 | Tao embedding index | `embedding_metadata.json` |
| 5 | Match audio segment voi clip | `matching_candidates.json` |
| 6 | Lap timeline de xuat | `timeline.json` |
| 7 | Review/chinh timeline local | cap nhat `timeline.json` |
| 8 | Render video cuoi | `data/final/final_video.mp4` |

## 2. Dieu Kien Ban Dau

Can co:

- Python virtualenv `.venv` da cai dependencies.
- Kaggle API key tai `%USERPROFILE%\.kaggle\kaggle.json`.
- Kaggle CLI cai trong `.venv`.
- FFmpeg va FFprobe dung duoc trong terminal local.
- File video/audio dau vao nam trong `data/raw/`.

Mo CMD moi va vao project:

```bat
cd /d "D:\Computational Thinking\Audio-Guided Video Montage"
.venv\Scripts\activate
```

Kiem tra Kaggle CLI:

```bat
.venv\Scripts\python.exe -m kaggle --version
```

Kiem tra FFmpeg:

```bat
ffmpeg -version
ffprobe -version
```

Neu FFmpeg da cai bang `winget` nhung terminal van khong nhan, them PATH tam
thoi cho CMD hien tai:

```bat
set PATH=%PATH%;C:\Users\DUCPHAN\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin
```

Sau do kiem tra lai:

```bat
ffmpeg -version
ffprobe -version
```

## 3. Dat File Input

Dat file vao `data/raw/`.

Vi du mac dinh dang dung:

```text
data/raw/vd00_CP_overview.mp4
data/raw/vd00_CP_overview.mp3
```

Kiem tra:

```bat
dir data\raw\vd00_CP_overview.mp4
dir data\raw\vd00_CP_overview.mp3
```

Neu dung file khac, vi du:

```text
data/raw/my_video.mp4
data/raw/my_voice.mp3
```

thi chi can truyen dung ten file vao lenh chay.

Luu y ve ten file:

- Ten file dau vao co the tuy y.
- Trong cung mot lan chay, cac video khong nen trung basename. Vi du khong nen
  co ca `folder_a/video.mp4` va `folder_b/video.mp4`.
- Pipeline hien ghi output vao cac file co ten co dinh trong `data/`, nen lan
  chay moi co the ghi de ket qua cu.

## 4. Backup Ket Qua Cu Neu Can Giu Lai

Neu muon giu ket qua cu truoc khi chay input moi:

```bat
mkdir runs\case_01
xcopy data\intermediate runs\case_01\intermediate /E /I
xcopy data\normalized runs\case_01\normalized /E /I
xcopy data\keyframes runs\case_01\keyframes /E /I
xcopy data\final runs\case_01\final /E /I
```

Doi `case_01` thanh ten ban muon, vi du:

```text
runs\demo_cp_overview
runs\new_voice_test
runs\case_2026_06_29
```

## 5. Chay Stage 1-6 Tren Kaggle

### 5.1. Chay voi input mac dinh

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --device cpu --compute-type int8 --wait --pull
```

Lenh nay se:

```text
1. Dong goi source code hien tai.
2. Copy raw media vao package upload.
3. Tao/cap nhat Kaggle Dataset rieng.
4. Push Kaggle Kernel runner.
5. Chay Stage 1-6 tren Kaggle.
6. Cho kernel xong.
7. Tai output ve.
8. Copy output vao data/intermediate, data/normalized, data/keyframes.
```

### 5.2. Chay voi input ten khac

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --device cpu --compute-type int8 --wait --pull
```

### 5.3. Chay voi nhieu video nguon

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\video1.mp4 data\raw\video2.mp4 data\raw\video3.mp4 --audio data\raw\voice.mp3 --device cpu --compute-type int8 --wait --pull
```

### 5.4. Output binh thuong khi dang chay

Cac dong sau la binh thuong:

```text
Starting upload for file ...
Dataset version is being created
[dataset] not attachable yet; sleeping 30s
KernelWorkerStatus.RUNNING
[wait] sleeping 60s
```

Neu thanh cong, se co dong gan giong:

```text
[wait] Kaggle kernel completed
[pull] copied Kaggle outputs into ...\data
```

## 6. Kiem Tra Output Stage 1-6

Chay:

```bat
dir data\intermediate\media_metadata.json
dir data\intermediate\audio_segments.json
dir data\intermediate\clip_metadata.json
dir data\intermediate\embedding_metadata.json
dir data\intermediate\matching_candidates.json
dir data\intermediate\timeline.json
```

Neu cac file tren ton tai, Stage 1-6 da xong.

Co the kiem tra nhanh timeline:

```bat
.venv\Scripts\python.exe -B -c "import json; t=json.load(open('data/intermediate/timeline.json', encoding='utf-8')); print(t.get('project_id'), len(t.get('items', [])))"
```

## 7. Mo Review UI Stage 7

Dung port moi moi lan chay de tranh dinh server cu:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

Khi thay:

```text
Running on local URL: http://127.0.0.1:7870
```

mo trinh duyet vao:

```text
http://127.0.0.1:7870
```

Terminal dung yen o do la dung. No dang giu server UI song.

Neu trinh duyet bao cache hoac `No API found`:

- Dong tab UI cu.
- Nhan `Ctrl + F5`.
- Hoac doi port, vi du `7871`, `7872`.

## 8. Cach Review Trong UI

Lam theo tung segment:

```text
1. Chon segment a001, a002, ...
2. Nghe audio/text cua segment.
3. Xem preview clip hien tai.
4. Neu clip chua hop, chon candidate khac.
5. Bam doi/cap nhat.
6. Chinh start/end/speed/crop neu can.
7. Bo needs_review neu segment da on.
8. Bam Save de ghi lai timeline.json.
```

Cac warning sau la binh thuong khi dang dung fake embeddings:

```text
LOW_CONFIDENCE
NEEDS_REVIEW
FALLBACK_USED
```

Chung khong chan luu hay render. Chung chi nhac ban can review thu cong.

Sau khi review xong, quay lai terminal dang chay UI va nhan:

```bat
Ctrl + C
```

## 9. Render Stage 8 Local

Dam bao CMD hien tai co FFmpeg trong PATH:

```bat
ffmpeg -version
ffprobe -version
```

Render:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

Kiem tra output:

```bat
dir data\final\final_video.mp4
dir data\intermediate\render_log.json
```

File video cuoi:

```text
data/final/final_video.mp4
```

## 10. Mot Lenh Mau Cho Vi Du Hoan Chinh

Voi input mac dinh:

```bat
cd /d "D:\Computational Thinking\Audio-Guided Video Montage"
.venv\Scripts\activate
set PATH=%PATH%;C:\Users\DUCPHAN\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --device cpu --compute-type int8 --wait --pull
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

Sau khi review va tat UI bang `Ctrl + C`:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
dir data\final\final_video.mp4
```

Voi input khac:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --device cpu --compute-type int8 --wait --pull
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7871
```

Sau khi review:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

## 11. Loi Thuong Gap

### Kaggle kernel loi

Lay log:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py logs
```

Neu log qua dai:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py logs > kaggle_log.txt
```

### Dataset chua attach kip

Neu thay:

```text
The following are not valid dataset sources
```

doi mot lat va chay lai:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --device cpu --compute-type int8 --wait --pull
```

### Review UI mo duoc nhung thao tac loi

Thu:

```text
1. Tat UI bang Ctrl + C.
2. Dong tab trinh duyet cu.
3. Chay lai UI bang port moi.
4. Mo tab an danh hoac Ctrl + F5.
```

Vi du:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7872
```

### Render bao WinError 2

Thuong la FFmpeg/FFprobe chua nam trong PATH.

Kiem tra:

```bat
ffmpeg -version
ffprobe -version
```

Neu khong nhan, them PATH tam thoi:

```bat
set PATH=%PATH%;C:\Users\DUCPHAN\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin
```

### Output cu bi ghi de

Backup truoc khi chay case moi:

```bat
mkdir runs\case_backup
xcopy data\intermediate runs\case_backup\intermediate /E /I
xcopy data\normalized runs\case_backup\normalized /E /I
xcopy data\keyframes runs\case_backup\keyframes /E /I
xcopy data\final runs\case_backup\final /E /I
```

## 12. Ghi Chu Ve Fake Embeddings Va Real Embeddings

Workflow hien tai nen dung fake embeddings truoc de kiem tra end-to-end nhanh:

```text
--fake-embeddings
```

Trong `scripts/kaggle_job.py`, fake embeddings dang la mac dinh. Vi vay lenh
`submit` se uu tien chay on dinh tu Stage 1-6 ma khong tai model CLIP lon.

Khi muon thu matching tot hon bang CLIP that, dung:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --real-embeddings --device cpu --compute-type int8 --wait --pull
```

Luu y: real embeddings co the cham hon, tai model lon hon, va yeu cau dependency
model/torch on dinh hon.
