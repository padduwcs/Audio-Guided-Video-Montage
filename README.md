# Audio-Guided Video Montage

Ứng dụng tạo video montage từ video nguồn và audio/voice-over có sẵn. Hệ thống
phân tích nội dung, tạo bản nháp trên Kaggle, cho phép chỉnh sửa rồi render video
cuối trên máy.

## Cài Đặt Và Chạy

Hướng dẫn đầy đủ cho người mới: [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

Sau khi đã cài Git và Miniconda:

```bash
git clone https://github.com/padduwcs/Audio-Guided-Video-Montage.git
cd Audio-Guided-Video-Montage
conda env update -f environment-terminal.yml --prune
conda activate audio-montage
python -B -m review_ui.launcher
```

Lệnh `conda env update` dùng được cho cả lần cài đầu tiên và những lần cập nhật
repo sau này.

Mở địa chỉ được in trong terminal, mặc định là `http://127.0.0.1:7860`.

## Cách Sử Dụng

1. Chọn video nguồn và audio trong tab **Bắt đầu**.
2. Lưu và kiểm tra Kaggle API.
3. Bấm **Tạo bản nháp video**.
4. Chỉnh các đoạn trong tab **Chỉnh sửa**.
5. Render tại tab **Xuất video**.

Video hoàn chỉnh nằm tại `data/final/final_video.mp4`.
