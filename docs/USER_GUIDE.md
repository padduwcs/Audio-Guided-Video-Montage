# User Guide

Huong dan nay danh cho nguoi dung cuoi: clone repo, dua video/audio vao, chay
pipeline va lay video thanh pham. Ban khong can hieu tung module ben trong.

## Ket Qua Can Dat

```text
data/final/final_video.mp4
```

Luong mac dinh:

```text
Raw video/audio
  -> Kaggle chay Stage 1-6
  -> Review UI local
  -> Render local
  -> final_video.mp4
```

## 1. Chuan Bi

Can co:

- Git de clone repo.
- Python 3.11 hoac 3.12.
- FFmpeg va FFprobe tren PATH.
- Kaggle account va file `kaggle.json`.
- It nhat 1 video nguon va 1 file audio/voice.

Kiem tra nhanh:

```powershell
git --version
python --version
ffmpeg -version
ffprobe -version
```

## 2. Clone Va Cai Moi Truong

```powershell
git clone <GITHUB_REPO_URL>
cd "Audio-Guided Video Montage"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

Neu dung Bash/macOS/Linux:

```bash
git clone <GITHUB_REPO_URL>
cd "Audio-Guided Video Montage"
python -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements-terminal.txt
```

## 3. Cau Hinh Kaggle

Tren Kaggle:

1. Vao account Settings.
2. Tim muc API.
3. Bam Create New Token.
4. Tai file `kaggle.json`.

Dat file vao:

```text
Windows: %USERPROFILE%\.kaggle\kaggle.json
macOS/Linux: ~/.kaggle/kaggle.json
```

Kiem tra Kaggle CLI:

```powershell
.\.venv\Scripts\kaggle.exe datasets list --mine
```

Dung `kaggle.exe` trong `.venv\Scripts\` tren Windows. Khong dung
`python -m kaggle` trong repo nay vi repo co thu muc local `kaggle/`.

## 4. Dat Input

Dat file vao `data/raw/`:

```text
data/raw/my_video.mp4
data/raw/my_voice.mp3
```

Ho tro nhieu video:

```text
data/raw/video_01.mp4
data/raw/video_02.mp4
data/raw/voice.mp3
```

Khong commit media len GitHub. Cac file trong `data/raw/` da duoc ignore.

## 5. Chay Stage 1-6 Tren Kaggle

Mot video:

```powershell
.\.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --device cpu --compute-type int8 --wait --pull
```

Nhieu video:

```powershell
.\.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\video_01.mp4 data\raw\video_02.mp4 --audio data\raw\voice.mp3 --device cpu --compute-type int8 --wait --pull
```

Lenh tren se:

1. Dong goi source code hien tai.
2. Upload source + raw media len private Kaggle Dataset cua account ban.
3. Chay Kaggle Kernel runner.
4. Tao artifact Stage 1-6.
5. Tai output ve `data/`.

Khi thanh cong, cac file nay se ton tai:

```text
data/intermediate/media_metadata.json
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/timeline.json
```

## 6. Review Timeline

Mo Review UI local:

```powershell
.\.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

Khi terminal hien local URL, mo trinh duyet:

```text
http://127.0.0.1:7870
```

Trong UI, review tung segment, doi candidate neu can, roi bam Save de ghi lai
`data/intermediate/timeline.json`.

Khi review xong, quay lai terminal dang chay UI va bam:

```text
Ctrl + C
```

## 7. Render Video Cuoi

```powershell
.\.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

Kiem tra thanh pham:

```powershell
dir data\final\final_video.mp4
```

## 8. Chay Lai Case Moi

Pipeline ghi output vao cac thu muc co dinh:

```text
data/intermediate/
data/normalized/
data/keyframes/
data/final/
```

Neu can giu ket qua cu, copy cac thu muc nay sang `runs/<ten_case>/` truoc khi
chay case moi.

Muon xoa output render/intermediate de chay lai:

```powershell
.\scripts\clean_outputs.ps1
.\scripts\clean_outputs.ps1 -Yes
```

Lenh dau la dry run; lenh thu hai moi xoa.

## 9. Loi Thuong Gap

Kaggle authentication error:

```powershell
dir "%USERPROFILE%\.kaggle\kaggle.json"
.\.venv\Scripts\kaggle.exe datasets list --mine
```

Khong thay `ffmpeg` hoac `ffprobe`:

```powershell
ffmpeg -version
ffprobe -version
```

Neu Windows khong nhan lenh, cai FFmpeg va mo terminal moi de PATH duoc cap
nhat.

Kaggle kernel loi:

```powershell
.\.venv\Scripts\python.exe -B scripts\kaggle_job.py logs
```

Review UI bi cache port cu:

```powershell
.\.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7871
```

## 10. Checklist Nhanh

```text
[ ] Clone repo
[ ] Tao .venv
[ ] pip install -r requirements-terminal.txt
[ ] FFmpeg/FFprobe chay duoc
[ ] Kaggle CLI doc duoc kaggle.json
[ ] Dat media vao data/raw
[ ] Chay scripts/kaggle_job.py submit --wait --pull
[ ] Mo Review UI va Save timeline
[ ] Render Stage 8
[ ] Kiem tra data/final/final_video.mp4
```

Can chi tiet hon ve Kaggle terminal workflow: [kaggle_terminal_workflow.md](kaggle_terminal_workflow.md).
