# Trung Tâm Tài Liệu

Đây là bản đồ tài liệu của repo **Audio-Guided Video Montage**.

## Người Dùng Cuối

Đọc theo thứ tự:

1. [USER_GUIDE.md](USER_GUIDE.md)
2. `environment-terminal.yml`

Người dùng cuối chỉ cần mở Launcher UI, chọn video/audio, nhập Kaggle API key,
tạo bản nháp, chỉnh sửa và xuất video.

## Dev

Đọc theo thứ tự:

1. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
2. [details/02_data_contract.md](details/02_data_contract.md)
3. README của module đang sửa
4. File spec tương ứng trong `docs/details/`

## Kaggle

Thông thường người dùng không cần đọc sâu phần này. Nếu cần debug terminal:

```text
docs/kaggle_terminal_workflow.md
```

Lưu ý quan trọng:

- Job Kaggle phải được submit từ Launcher hoặc `scripts/kaggle_job.py`.
- Không bấm Run thủ công trên Kaggle web cho kernel do repo tạo.
- Lỗi `403 Forbidden` thường là lỗi Kaggle API key/quyền Dataset private.
- Lỗi thiếu `kaggle_job_config.json` nghĩa là Dataset input chưa attach vào
  kernel trong môi trường Kaggle.

## Tài Liệu Chính

```text
docs/
  README.md
  USER_GUIDE.md
  DEVELOPER_GUIDE.md
  kaggle_terminal_workflow.md

  details/
    00_project_scope.md
    01_system_architecture.md
    02_data_contract.md
    03_stage_1_input_processing.md
    04_stage_2_audio_analysis.md
    05_stage_3_video_analysis.md
    06_stage_4_embedding_indexing.md
    07_stage_5_matching_engine.md
    08_stage_6_timeline_planning.md
    09_stage_7_review_ui.md
    10_stage_8_rendering.md

  schemas/
  samples/
```

## Kiểm Tra Contract

Validate sample:

```bash
python scripts/validate_json.py
```

Validate dữ liệu runtime:

```bash
python scripts/validate_json.py --input-dir data/intermediate
```
