# Hướng Dẫn Sử Dụng

## 1. Cài Công Cụ

Cài ba thứ sau:

1. [Git](https://git-scm.com/downloads)
2. [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/)
3. Tạo tài khoản [Kaggle](https://www.kaggle.com/)

Sau khi cài xong, mở **Anaconda Prompt** trên Windows hoặc **Terminal** trên
macOS và kiểm tra:

```bash
git --version
conda --version
```

## 2. Tải Và Cài Ứng Dụng

```bash
git clone https://github.com/padduwcs/Audio-Guided-Video-Montage.git
cd Audio-Guided-Video-Montage
conda env update -f environment-terminal.yml --prune
conda activate audio-montage
```

Lệnh trên sẽ tạo môi trường nếu máy chưa có, hoặc đồng bộ môi trường cũ với
phiên bản repo hiện tại. Có thể chạy lại an toàn sau mỗi lần cập nhật repo.

## 3. Lấy Kaggle API

1. Mở Kaggle, vào **Settings**.
2. Tìm mục **API** và chọn **Create New Token**.
3. Mở file `kaggle.json` vừa tải về.
4. Giữ lại hai giá trị `username` và `key` để nhập vào ứng dụng.

## 4. Mở Ứng Dụng

Tại thư mục repo, chạy:

```bash
conda activate audio-montage
python -B -m review_ui.launcher
```

Mở địa chỉ terminal hiển thị, mặc định là:

```text
http://127.0.0.1:7860
```

## 5. Tạo Video

Trong tab **Bắt đầu**:

1. Chọn video nguồn và audio/voice-over.
2. Nhập Kaggle `username` và `key`.
3. Bấm **Lưu Kaggle**, sau đó bấm **Kiểm tra**.
4. Bấm **Dùng các file này**.
5. Bấm **Tạo bản nháp video** và chờ hoàn tất.

Không chạy Kernel thủ công trên trang Kaggle.

## 6. Chỉnh Sửa Và Xuất Video

1. Vào tab **Chỉnh sửa** và mở màn hình chỉnh sửa.
2. Xem, đổi clip hoặc chỉnh từng đoạn rồi lưu timeline.
3. Quay lại Launcher, vào tab **Xuất video** và bấm xuất.

Video hoàn chỉnh nằm tại:

```text
data/final/final_video.mp4
```

Các lần sử dụng sau chỉ cần mở terminal tại repo và chạy lại hai lệnh ở bước 4.
