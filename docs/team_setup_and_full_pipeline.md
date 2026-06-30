# Team Setup And Full Pipeline Guide

Tai lieu nay danh cho thanh vien moi clone repo tu GitHub ve may rieng va muon
chay thu mot vi du tu dau den cuoi.

Muc tieu:

```text
clone repo
  -> cai moi truong
  -> cau hinh Kaggle
  -> dat video/audio vao data/raw
  -> chay Stage 1-6 tren Kaggle
  -> review local bang UI
  -> render final_video.mp4
```

Huong dan uu tien Windows CMD. Neu dung PowerShell, phan lon lenh van tuong tu,
nhung lenh set bien moi truong se khac.

## 0. Can Chuan Bi Gi Truoc

Moi thanh vien can co:

```text
1. Git de clone repo.
2. Python de tao virtualenv.
3. Kaggle account rieng.
4. Kaggle API key file kaggle.json.
5. FFmpeg + FFprobe de render video local.
6. It nhat 1 video nguon va 1 file voice/audio.
```

Khuyen nghi:

```text
Video input: .mp4
Voice input: .mp3 hoac .wav
Dung thu muc project khong qua dac biet, tranh ky tu la neu co the.
Mo terminal moi sau khi cai Git/Python/FFmpeg de PATH duoc cap nhat.
```

## 1. Cai Git Neu Chua Co

Kiem tra:

```bat
git --version
```

Neu CMD bao `'git' is not recognized`, cai Git for Windows:

```text
https://git-scm.com/download/win
```

Khi cai, giu cac lua chon mac dinh la duoc. Cai xong dong CMD cu, mo CMD moi
va kiem tra lai:

```bat
git --version
```

## 2. Clone Repo

Mo CMD tai thu muc ban muon de project:

```bat
git clone <GITHUB_REPO_URL>
cd "Audio-Guided Video Montage"
```

Neu ten folder clone khac, chi can `cd` vao dung folder co file `README.md`,
`requirements.txt`, `scripts\kaggle_job.py`.

Kiem tra dang o dung folder:

```bat
dir README.md
dir scripts\kaggle_job.py
```

Trong huong dan ben duoi, `<PROJECT_DIR>` la thu muc vua clone. Vi du:

```text
C:\Users\YourName\Documents\Audio-Guided Video Montage
```

## 3. Cai Python Va Virtualenv

Can Python 3.11+.

Khuyen nghi cho nguoi moi:

```text
Python 3.11 hoac 3.12: on dinh nhat.
Python 3.13: co the thu voi workflow nhe, nhung neu gap loi dependency thi
fallback ve 3.12 se it rac roi hon.
```

Ly do: workflow mac dinh cua repo chi can package nhe de submit Kaggle, mo
Review UI va render local. Full local/dev stack co cac package ML nang hon nhu
`torch`, `transformers`, `faster-whisper`, va cac package nay doi khi cham ho
tro Python moi nhat.

Neu pip bao loi kieu:

```text
No matching distribution found
```

thi do thuong la dependency chua co wheel phu hop cho Python dang dung. Cach
don gian nhat la tao lai venv bang Python 3.12.

Kiem tra:

```bat
python --version
```

Neu may co nhieu ban Python, kiem tra bang Python Launcher:

```bat
py -0p
```

Neu co Python 3.12, nen tao venv bang:

```bat
py -3.12 -m venv .venv
```

Neu co Python 3.11, co the dung:

```bat
py -3.11 -m venv .venv
```

Neu CMD bao `'python' is not recognized`, cai Python:

```text
https://www.python.org/downloads/windows/
```

Khi cai Python tren Windows, nho tick:

```text
Add python.exe to PATH
```

Cai xong dong CMD cu, mo CMD moi, vao lai repo:

```bat
cd "<PROJECT_DIR>"
python --version
```

Tao va kich hoat virtualenv. Neu `python --version` dang tro toi ban Python ban
muon dung:

```bat
python -m venv .venv
.venv\Scripts\activate
```

Khi thanh cong, dau dong terminal co `(.venv)`.

Cap nhat pip va cai dependencies nhe cho workflow mac dinh:

```bat
.venv\Scripts\python.exe -m ensurepip --upgrade
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

Neu cai dependency that bai giua chung:

```bat
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

Chi cai full dev/local stack khi can chay test, chay pipeline local Stage 1-6,
hoac phat trien module:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Kiem tra cac package quan trong:

```bat
.venv\Scripts\kaggle.exe --version
.venv\Scripts\python.exe -c "import gradio; print(gradio.__version__)"
```

Khong dung `.venv\Scripts\python.exe -m kaggle --version` de kiem tra trong
repo nay, vi repo co thu muc local `kaggle/` va co the lam Python import nham
khi package Kaggle CLI chua cai xong.

## 4. Cai FFmpeg Va FFprobe

Renderer local can `ffmpeg` va `ffprobe`.

### Cach A: Cai bang winget

```bat
winget install Gyan.FFmpeg
```

Neu winget hoi dong y dieu khoan/source, nhap:

```bat
Y
```

Dong terminal cu, mo CMD moi, vao lai repo va kich hoat venv:

```bat
cd "<PROJECT_DIR>"
.venv\Scripts\activate
```

Kiem tra:

```bat
ffmpeg -version
ffprobe -version
```

### Cach B: Cai Thu Cong Bang File Zip

Dung khi may khong co winget hoac winget loi.

```text
1. Tai FFmpeg build cho Windows tu mot nguon tin cay.
2. Giai nen file zip, vi du vao C:\tools\ffmpeg.
3. Tim thu muc co ffmpeg.exe va ffprobe.exe, thuong la C:\tools\ffmpeg\bin.
4. Them thu muc bin do vao PATH.
```

Them PATH tam thoi trong CMD hien tai:

```bat
set PATH=%PATH%;C:\tools\ffmpeg\bin
```

Kiem tra:

```bat
ffmpeg -version
ffprobe -version
```

### Cach C: Neu FFmpeg Da Cai Nhung CMD Van Khong Nhan

Tim `ffmpeg.exe`:

```bat
where ffmpeg
```

Neu `where ffmpeg` khong thay, hay tim trong thu muc WinGet:

```bat
dir "%LOCALAPPDATA%\Microsoft\WinGet\Packages" /s /b | findstr ffmpeg.exe
```

Tim duoc folder `bin` chua `ffmpeg.exe` va `ffprobe.exe`, them tam thoi vao
PATH cua terminal hien tai:

```bat
set PATH=%PATH%;<FFMPEG_BIN_DIR>
```

Vi du:

```bat
set PATH=%PATH%;C:\path\to\ffmpeg\bin
```

Kiem tra lai:

```bat
ffmpeg -version
ffprobe -version
```

Neu muon them PATH vinh vien, mo Windows Search:

```text
Edit the system environment variables
  -> Environment Variables
  -> User variables
  -> Path
  -> New
  -> them <FFMPEG_BIN_DIR>
```

Sau khi them vinh vien, dong terminal cu va mo terminal moi.

## 5. Tao Kaggle API Key

Moi thanh vien nen dung Kaggle account rieng.

### 5.1. Tao token tren web Kaggle

```text
1. Mo trinh duyet va vao https://www.kaggle.com/
2. Dang nhap hoac tao account Kaggle.
3. Bam avatar/account icon o goc phai tren.
4. Chon Settings.
5. Keo xuong muc API.
6. Bam Create New Token.
7. Trinh duyet se tai file kaggle.json ve may.
```

File `kaggle.json` thuong co noi dung dang:

```json
{
  "username": "your_kaggle_username",
  "key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

Khong chia se file nay va khong commit len GitHub.

### 5.2. Dat file kaggle.json dung cho Windows

Dat file vao:

```text
%USERPROFILE%\.kaggle\kaggle.json
```

Neu chua co folder `.kaggle`, tao:

```bat
mkdir "%USERPROFILE%\.kaggle"
```

Neu file nam trong Downloads, vi du `C:\Users\YourName\Downloads\kaggle.json`,
copy bang lenh:

```bat
copy "%USERPROFILE%\Downloads\kaggle.json" "%USERPROFILE%\.kaggle\kaggle.json"
```

Kiem tra:

```bat
dir "%USERPROFILE%\.kaggle\kaggle.json"
```

Xem nhanh username trong file:

```bat
type "%USERPROFILE%\.kaggle\kaggle.json"
```

Neu file hien ra co `username` va `key` la dung. Dung de kiem tra, khong chup
man hinh/share noi dung `key`.

### 5.3. Kiem tra Kaggle CLI

Kiem tra Kaggle CLI doc duoc key:

```bat
.venv\Scripts\kaggle.exe datasets list --mine
```

Neu lenh tren tra ve danh sach dataset hoac bang rong la OK. Neu bao
authentication error, kiem tra lai vi tri va noi dung `kaggle.json`.

Neu loi quyen file tren Windows, thu:

```bat
attrib -R "%USERPROFILE%\.kaggle\kaggle.json"
```

## 6. Cau Hinh Username Kaggle

Script se tu doc username tu `%USERPROFILE%\.kaggle\kaggle.json`. Neu muon ep
ro rang trong terminal hien tai:

```bat
set KAGGLE_USERNAME=<your_kaggle_username>
```

Hoac truyen truc tiep vao lenh submit:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --username <your_kaggle_username> --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --wait --pull
```

Moi account se tao/cap nhat dataset va kernel rieng theo dang:

```text
<username>/audio-guided-video-montage-input
<username>/audio-guided-video-montage-runner
```

## 7. Dat Input Vao Repo

Dat video va voice/audio vao:

```text
data/raw/
```

Vi du:

```text
data/raw/my_video.mp4
data/raw/my_voice.mp3
```

Kiem tra:

```bat
dir data\raw\my_video.mp4
dir data\raw\my_voice.mp3
```

Luu y:

- Khong commit file media lon len GitHub.
- `.gitignore` da bo qua `*.mp4`, `*.mp3`, `data/raw/*`.
- Trong mot lan chay, khong dung hai video co cung basename. Vi du khong nen
  truyen ca `a\video.mp4` va `b\video.mp4`.

## 8. Chay Stage 1-6 Tren Kaggle

Truoc khi chay, dam bao dang o dung repo va venv da bat:

```bat
cd "<PROJECT_DIR>"
.venv\Scripts\activate
```

### Mot video + mot voice

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --device cpu --compute-type int8 --wait --pull
```

Lenh tren dung fake embeddings de test pipeline nhanh. Neu muon matching that
bang CLIP va chay ASR/CLIP tren GPU Kaggle, dung:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --real-embeddings --device cuda --compute-type float16 --wait --pull
```

Neu Kaggle bao loi CUDA hoac float16, quay lai lenh CPU on dinh:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --device cpu --compute-type int8 --wait --pull
```

### Nhieu video + mot voice

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\video1.mp4 data\raw\video2.mp4 data\raw\video3.mp4 --audio data\raw\voice.mp3 --device cpu --compute-type int8 --wait --pull
```

Lenh submit se tu dong:

```text
1. Dong goi source code hien tai.
2. Upload code + raw media len Kaggle Dataset cua account dang dung.
3. Push Kaggle Kernel runner.
4. Chay Stage 1-6 tren Kaggle.
5. Cho kernel xong.
6. Tai output ve may.
7. Copy output vao data/intermediate, data/normalized, data/keyframes.
```

Trong qua trinh chay, cac dong sau la binh thuong:

```text
Starting upload for file ...
Dataset version is being created
[dataset] not attachable yet; sleeping 30s
KernelWorkerStatus.RUNNING
[wait] sleeping 60s
```

Thanh cong se co:

```text
[wait] Kaggle kernel completed
[pull] copied Kaggle outputs into ...\data
```

Neu day la lan dau account do push dataset/kernel, Kaggle co the mat vai phut
de tao private Dataset va Kernel. Dung tat terminal khi dang `RUNNING` hoac
`[wait] sleeping`.

## 9. Kiem Tra Output Stage 1-6

```bat
dir data\intermediate\media_metadata.json
dir data\intermediate\audio_segments.json
dir data\intermediate\clip_metadata.json
dir data\intermediate\embedding_metadata.json
dir data\intermediate\matching_candidates.json
dir data\intermediate\timeline.json
```

Kiem tra nhanh so segment:

```bat
.venv\Scripts\python.exe -B -c "import json; t=json.load(open('data/intermediate/timeline.json', encoding='utf-8')); print(t.get('project_id'), len(t.get('items', [])))"
```

## 10. Mo Review UI

Review UI chay local tren may minh, khong chay tren Kaggle.

Truoc khi mo UI, neu terminal moi thi vao repo va bat venv:

```bat
cd "<PROJECT_DIR>"
.venv\Scripts\activate
```

Chay bang port moi de tranh server cu:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

Khi thay:

```text
Running on local URL: http://127.0.0.1:7870
```

mo browser vao:

```text
http://127.0.0.1:7870
```

Terminal dung yen la dung vi no dang giu UI server song.

Trong UI:

```text
1. Chon tung segment.
2. Nghe audio/text.
3. Xem preview clip.
4. Doi candidate neu clip chua hop.
5. Chinh start/end/speed/crop neu can.
6. Bam cap nhat.
7. Bam Save de ghi timeline.json.
```

Warning nhu `LOW_CONFIDENCE`, `NEEDS_REVIEW`, `FALLBACK_USED` la binh thuong
khi dang dung fake embeddings. Chung nhac nguoi dung can review thu cong.

Sau khi review xong, quay lai terminal UI va bam:

```bat
Ctrl + C
```

## 11. Render Video Cuoi

Kiem tra FFmpeg:

```bat
ffmpeg -version
ffprobe -version
```

Render:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
```

Kiem tra ket qua:

```bat
dir data\final\final_video.mp4
dir data\intermediate\render_log.json
```

Video cuoi nam tai:

```text
data/final/final_video.mp4
```

Mo file video bang File Explorer hoac trinh phat video de xem san pham.

## 12. Backup Ket Qua Truoc Khi Chay Case Moi

Pipeline hien ghi output vao cac duong dan co dinh:

```text
data/intermediate/
data/normalized/
data/keyframes/
data/final/
```

Neu chay case moi, ket qua cu co the bi ghi de. Backup truoc:

```bat
mkdir runs\case_01
xcopy data\intermediate runs\case_01\intermediate /E /I
xcopy data\normalized runs\case_01\normalized /E /I
xcopy data\keyframes runs\case_01\keyframes /E /I
xcopy data\final runs\case_01\final /E /I
```

`runs/` la thu muc local nen khong nen commit len GitHub neu chua can.

## 13. Debug Loi Thuong Gap

### Kaggle authentication error

Kiem tra:

```bat
dir "%USERPROFILE%\.kaggle\kaggle.json"
.venv\Scripts\kaggle.exe datasets list --mine
```

Neu van loi, tao lai API token tren Kaggle va thay file `kaggle.json`.

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

doi mot lat va chay lai submit. Script da co retry, nhung Kaggle doi khi index
dataset cham.

### Review UI bao No API found

Thu:

```text
1. Tat UI bang Ctrl + C.
2. Dong tab browser cu.
3. Chay lai bang port moi, vi du 7871.
4. Mo tab an danh hoac Ctrl + F5.
```

### Render bao WinError 2

Thuong la `ffmpeg` hoac `ffprobe` chua nam trong PATH.

Kiem tra:

```bat
ffmpeg -version
ffprobe -version
```

Neu khong nhan, them folder `bin` cua FFmpeg vao PATH.

### pip install loi dependency tren Python moi

Neu thay:

```text
ERROR: Could not find a version that satisfies the requirement ...
ERROR: No matching distribution found for ...
```

thi thu 2 cach theo thu tu:

1. Neu chi muon chay workflow Kaggle + UI + render, dung file nhe:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

2. Neu van can full dev/local stack va dang dung Python qua moi, tao lai venv
bang Python 3.12:

```bat
deactivate
rmdir /S /Q .venv
py -0p
py -3.12 -m venv .venv
.venv\Scripts\activate
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Neu may khong co Python 3.12, co the cai them Python 3.12 tu python.org roi lam
lai cac lenh tren. Khong can go Python cu; co the cai song song nhieu version.

### python -m kaggle bao No module named kaggle.__main__

Neu thay:

```text
No module named kaggle.__main__; 'kaggle' is a package and cannot be directly executed
```

thi khong dung lenh `python -m kaggle` de kiem tra CLI. Trong repo nay co thu
muc local `kaggle/`, nen hay dung executable cua CLI:

```bat
.venv\Scripts\kaggle.exe --version
.venv\Scripts\kaggle.exe datasets list --mine
```

Neu `.venv\Scripts\kaggle.exe` khong ton tai, dependency install chua thanh
cong. Hay sua loi pip install truoc.

### ImportError hoac No module named ...

Thu cai lai dependencies trong venv:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

Neu ban dang dev/chay full local Stage 1-6, cai them full dev stack:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Neu van loi, xoa va tao lai venv:

```bat
rmdir /S /Q .venv
python -m venv .venv
.venv\Scripts\activate
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python.exe -m pip install -r requirements-terminal.txt
```

### Output bi ghi de

Backup `data/intermediate`, `data/normalized`, `data/keyframes`, `data/final`
truoc khi chay case moi.

## 14. Fake Embeddings Va Real Embeddings

Mac dinh script Kaggle dang dung fake embeddings de chay end-to-end nhanh va on
dinh hon:

```text
fake embeddings: on
```

Khi muon thu matching bang model that:

```bat
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --real-embeddings --device cpu --compute-type int8 --wait --pull
```

Real embeddings co the cham hon va phu thuoc model/torch nhieu hon.

## 15. Mot Vi Du Day Du Tu Dau Den Cuoi

Gia su file dau vao la:

```text
data/raw/my_video.mp4
data/raw/my_voice.mp3
```

Chay Stage 1-6 tren Kaggle:

```bat
cd "<PROJECT_DIR>"
.venv\Scripts\activate
.venv\Scripts\python.exe -B scripts\kaggle_job.py submit --videos data\raw\my_video.mp4 --audio data\raw\my_voice.mp3 --device cpu --compute-type int8 --wait --pull
```

Mo Review UI:

```bat
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 7 --to-stage 7 --launch-ui --no-ui-backup --ui-port 7870
```

Mo browser:

```text
http://127.0.0.1:7870
```

Review, bam Save, quay lai terminal va `Ctrl + C`.

Render:

```bat
ffmpeg -version
ffprobe -version
.venv\Scripts\python.exe -B -m integration.run_pipeline --from-stage 8 --to-stage 8 --overwrite
dir data\final\final_video.mp4
```

Neu `data\final\final_video.mp4` ton tai, pipeline da hoan tat.

## 16. Checklist Nhanh Cho Thanh Vien Moi

```text
[ ] Cai Git
[ ] Clone repo
[ ] Cai Python
[ ] Tao .venv
[ ] pip install -r requirements-terminal.txt
[ ] Cai ffmpeg/ffprobe va verify version
[ ] Tao Kaggle account
[ ] Tao Kaggle API token
[ ] Dat kaggle.json vao %USERPROFILE%\.kaggle\
[ ] Verify Kaggle CLI
[ ] Dat input vao data/raw
[ ] Chay kaggle_job.py submit --videos ... --audio ... --wait --pull
[ ] Mo Review UI
[ ] Save timeline
[ ] Render Stage 8
[ ] Kiem tra data/final/final_video.mp4
```
