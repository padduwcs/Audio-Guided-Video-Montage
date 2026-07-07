# User Guide

Huong dan nay danh cho nguoi dung cuoi: clone repo, mo giao dien local, chon
video/audio, chay tao ban nhap, chinh sua va xuat video. Ban khong can hieu
tung module ben trong.

## Ket Qua Can Dat

```text
data/final/final_video.mp4
```

Luong mac dinh:

```text
Raw video/audio
  -> Bat dau tren Launcher UI
  -> Chinh sua ban dung
  -> Xuat video
  -> final_video.mp4
```

## 1. Chuan Bi

Can co:

- Git de clone repo.
- Python 3.11 hoac 3.12.
- FFmpeg va FFprobe tren PATH.
- Kaggle account va API key.
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

## 3. Mo Ung Dung

Chay Launcher UI:

```powershell
.\.venv\Scripts\python.exe -B -m review_ui.launcher
```

Mo trinh duyet tai:

```text
http://127.0.0.1:7860
```

Neu cong `7860` dang ban, ung dung se tu dung cong tiep theo. Hay mo dung URL
duoc in trong terminal.

Ung dung co 3 tab chinh:

```text
Bat dau     chon file, cau hinh Kaggle, tao ban nhap
Chinh sua   mo Review UI de doi clip/chinh timeline
Xuat video  render va xem video cuoi
```

## 4. Cau Hinh Kaggle Tren UI

Tren Kaggle web:

1. Vao account Settings.
2. Tim muc API.
3. Bam Create New Token.
4. Tai file `kaggle.json`.

Trong tab `Bat dau`, nhap:

```text
Username
API key
```

Bam:

```text
Luu Kaggle
Kiem tra
```

Ung dung chi luu API key tren may cua ban tai `~/.kaggle/kaggle.json`. Key
khong duoc ghi vao repo, log hay output.

## 5. Tao Ban Nhap

Trong tab `Bat dau`:

```text
1. Chon mot hoac nhieu video nguon.
2. Chon mot file voice-over/audio.
3. Bam Dung cac file nay.
4. Bam Tao ban nhap video.
```

Ung dung se tu:

```text
copy input vao data/raw
upload len Kaggle
chay phan tich video/audio
tai timeline ve may
```

Khi xong, ban nhap nam trong:

```text
data/intermediate/timeline.json
```

## 6. Review Timeline

Trong tab `Chinh sua`, bam:

```text
Mo man hinh chinh sua
```

Ung dung se mo Review UI tai:

```text
http://127.0.0.1:7870
```

Trong Review UI, xem tung doan, doi clip neu can, roi bam `Luu Thay Doi`.

## 7. Xuat Video Cuoi

Quay lai Launcher UI, vao tab `Xuat video`, bam `Xuat video`.

Thanh pham nam tai:

```text
data/final/final_video.mp4
```

## 8. Chay Lai Case Moi

```text
data/intermediate/
data/normalized/
data/keyframes/
data/final/
```

Neu can giu ket qua cu, copy cac thu muc nay sang `runs/<ten_case>/` truoc khi
chay case moi.

Muon xoa output de chay lai, dung lenh goi PowerShell ro rang. Cach nay chay
duoc ca khi ban dang o CMD:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\clean_outputs.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\clean_outputs.ps1 -Yes
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

Loi `Requested ... compute type` tren CUDA:

```text
Mo Tuy chon nang cao trong tab Bat dau
Chon Thiet bi Kaggle = cpu
Chon Compute type = int8
Chay Tao ban nhap video lai
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
[ ] Mo Launcher UI
[ ] Luu va kiem tra Kaggle tren UI
[ ] Chon video/audio tren UI
[ ] Tao ban nhap video
[ ] Mo man hinh chinh sua va Save timeline
[ ] Xuat video
[ ] Kiem tra data/final/final_video.mp4
```

Can chi tiet hon ve Kaggle terminal workflow: [kaggle_terminal_workflow.md](kaggle_terminal_workflow.md).
