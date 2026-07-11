# Hướng Dẫn Sử Dụng

Hướng dẫn này dành cho người mới, máy chưa cài gì. Bạn chỉ cần làm theo từng
bước để mở ứng dụng, chọn video/audio, tạo bản nháp, chỉnh sửa và xuất video.

Kết quả cuối cùng sẽ nằm ở:

```text
data/final/final_video.mp4
```

## 1. Cài Công Cụ Cần Thiết

Cài 3 thứ sau:

1. Git: https://git-scm.com/downloads
2. Miniconda hoặc Anaconda: https://docs.conda.io/projects/miniconda
3. Tài khoản Kaggle: https://www.kaggle.com

Sau khi cài xong, mở Terminal:

- Windows: mở **Anaconda Prompt** hoặc **PowerShell**.
- macOS: mở **Terminal**.

Kiểm tra nhanh:

```bash
git --version
conda --version
```

## 2. Tải Repo Về Máy

```bash
git clone <GITHUB_REPO_URL>
cd "Audio-Guided Video Montage"
```

Thay `<GITHUB_REPO_URL>` bằng link repo thật.

## 3. Tạo Môi Trường Chạy

Dùng Conda để Windows/macOS có cùng Python và FFmpeg:

```bash
conda env create -f environment-terminal.yml
conda activate audio-montage
```

Mỗi lần mở terminal mới để chạy app, dùng lại:

```bash
conda activate audio-montage
```

## 4. Chuẩn Bị Kaggle API Key

Trên Kaggle:

1. Vào **Account Settings**.
2. Tìm mục **API**.
3. Bấm **Create New Token**.
4. Máy sẽ tải file `kaggle.json`.

Mở file `kaggle.json`, bạn sẽ thấy:

```json
{
  "username": "...",
  "key": "..."
}
```

Giữ lại `username` và `key` để nhập trong ứng dụng.

## 5. Mở Ứng Dụng

Trong terminal đang ở thư mục repo:

```bash
python -B -m review_ui.launcher
```

Mở trình duyệt tại:

```text
http://127.0.0.1:7860
```

Nếu terminal in ra cổng khác, mở đúng URL mà terminal hiển thị.

## 6. Tạo Bản Nháp Video

Trong tab **Bắt đầu**:

1. Chọn một hoặc nhiều video nguồn.
2. Chọn một file audio/voice-over.
3. Nhập Kaggle `username` và `key`.
4. Bấm **Lưu Kaggle**.
5. Bấm **Kiểm tra**.
6. Bấm **Dùng các file này**.
7. Bấm **Tạo bản nháp video**.

Định dạng hỗ trợ:

```text
Video: .mp4, .mov, .mkv, .webm
Audio: .wav, .mp3, .m4a, .aac, .flac, .ogg
```

Không bấm **Run** thủ công trên Kaggle web. Hãy để ứng dụng tự gửi job lên
Kaggle.

## 7. Chỉnh Sửa Bản Nháp

Khi bản nháp đã sẵn sàng, vào tab **Chỉnh sửa** và bấm:

```text
Mở màn hình chỉnh sửa
```

Ứng dụng sẽ mở Review UI tại:

```text
http://127.0.0.1:7870
```

Trong Review UI:

1. Xem từng đoạn.
2. Đổi clip nếu cần.
3. Chỉnh thời gian/crop/âm lượng nếu muốn.
4. Bấm **Lưu Thay Đổi**.

## 8. Xuất Video Cuối

Quay lại Launcher UI, vào tab **Xuất video**, bấm:

```text
Xuất video
```

Video cuối nằm ở:

```text
data/final/final_video.mp4
```

## 9. Chạy Dự Án Mới

Nếu muốn làm video mới, mở Launcher UI và chọn file mới.

Nếu muốn xóa kết quả cũ trước khi chạy lại:

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\clean_outputs.ps1 -Yes
```

macOS/Linux:

```bash
bash scripts/clean_outputs.sh
```

## 10. Ghi Nhớ

- Người dùng cuối chỉ cần mở Launcher UI.
- Stage 1-6 chạy trên Kaggle.
- Review và render chạy trên máy local.
- Nếu Kaggle báo `401 Unauthorized`, hãy tạo lại API token trên Kaggle rồi
  bấm **Lưu Kaggle** và **Kiểm tra** trong Launcher.
- Không commit video, audio, output, embedding hoặc file trong `data/`.
