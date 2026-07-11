# Workflow Kaggle Bằng Terminal

Người dùng bình thường nên dùng Launcher UI. Tài liệu này chỉ dành cho lúc cần
debug hoặc chạy Kaggle bằng terminal.

## 1. Chuẩn Bị

Cài môi trường:

```bash
conda env create -f environment-terminal.yml
conda activate audio-montage
```

Đảm bảo đã có Kaggle API key:

```bash
kaggle datasets list --mine
```

Trên macOS/Linux, nếu Kaggle báo lỗi quyền file:

```bash
chmod 600 ~/.kaggle/kaggle.json
```

## 2. Đặt File Đầu Vào

Đặt video/audio vào `data/raw/`, ví dụ:

```text
data/raw/my_video.mp4
data/raw/my_voice.mp3
```

Định dạng hỗ trợ:

```text
Video: .mp4, .mov, .mkv, .webm
Audio: .wav, .mp3, .m4a, .aac, .flac, .ogg
```

## 3. Submit Job

```bash
python -B scripts/kaggle_job.py submit --videos data/raw/my_video.mp4 --audio data/raw/my_voice.mp3 --wait --pull
```

Nhiều video:

```bash
python -B scripts/kaggle_job.py submit --videos data/raw/video1.mp4 data/raw/video2.mp4 --audio data/raw/voice.mp3 --wait --pull
```

## 4. Output Sau Khi Pull

Kết quả Stage 1-6 sẽ nằm ở:

```text
data/intermediate/media_metadata.json
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/timeline.json
```

Sau đó mở Review UI hoặc quay lại Launcher.

## 5. Xem Log

```bash
python -B scripts/kaggle_job.py status
python -B scripts/kaggle_job.py logs
```

## 6. Ghi Nhớ

- Không bấm Run thủ công trên Kaggle web.
- Job phải được submit từ Launcher hoặc `scripts/kaggle_job.py`.
- Nếu gặp `403 Forbidden`, kiểm tra Kaggle username/API key có cùng một tài
  khoản không.
- Nếu Kaggle báo thiếu `kaggle_job_config.json`, nghĩa là Dataset input chưa
  attach vào kernel trong `/kaggle/input`.
- Nếu artifact cũ bị kẹt, xóa Dataset/Kernel private trên Kaggle:

```text
audio-guided-video-montage-input
audio-guided-video-montage-runner
```
