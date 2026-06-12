# Audio-Guided Video Montage

## 1. Giới thiệu dự án

**Audio-Guided Video Montage** — hệ thống dựng video bán tự động theo audio thuyết minh, tận dụng cảnh có sẵn trong video nguồn (không sinh video mới bằng AI).

Phạm vi, MVP, demo: [`docs/details/00_project_scope.md`](docs/details/00_project_scope.md).

## 2. Mục tiêu MVP

Pipeline end-to-end và checklist chức năng bắt buộc: [`docs/details/00_project_scope.md` §8](docs/details/00_project_scope.md).

Kiến trúc module: [`docs/details/01_system_architecture.md` §2](docs/details/01_system_architecture.md).

## 3. Cấu trúc thư mục

```text
project-root/
│
├── docs/
│   ├── README.md
│   ├── problem.md
│   ├── analysis.md
│   │
│   ├── details/
│   │   ├── 00_project_scope.md
│   │   ├── 01_system_architecture.md
│   │   ├── 02_data_contract.md
│   │   ├── 03_stage_1_input_processing.md
│   │   ├── 04_stage_2_audio_analysis.md
│   │   ├── 05_stage_3_video_analysis.md
│   │   ├── 06_stage_4_embedding_indexing.md
│   │   ├── 07_stage_5_matching_engine.md
│   │   ├── 08_stage_6_timeline_planning.md
│   │   ├── 09_stage_7_review_ui.md
│   │   ├── 10_stage_8_rendering.md
│   │   ├── 11_team_assignment.md
│   │   └── 12_integration_plan.md
│   │
│   ├── schemas/
│   │   ├── media_metadata.schema.md
│   │   ├── audio_segments.schema.md
│   │   ├── clip_metadata.schema.md
│   │   ├── embedding_metadata.schema.md
│   │   ├── matching_candidates.schema.md
│   │   ├── timeline.schema.md
│   │   ├── render_config.schema.md
│   │   ├── render_log.schema.md
│   │   └── evaluation_report.schema.md
│   │
│   └── samples/
│       ├── media_metadata_sample.json
│       ├── audio_segments_sample.json
│       ├── clip_metadata_sample.json
│       ├── embedding_metadata_sample.json
│       ├── embedding_index_sample/
│       ├── matching_candidates_sample.json
│       ├── timeline_sample.json
│       ├── render_config_sample.json
│       └── render_log_sample.json
│
├── integration/
├── input_processor/
├── audio_analyzer/
├── video_analyzer/
├── embedding_indexer/
├── matching_engine/
├── timeline_planner/
├── review_ui/
├── renderer/
├── shared/
├── data/
├── scripts/
│
├── README.md
├── .gitignore
└── requirements.txt
```

## 4. Vai trò của các thư mục chính

### `docs/`

Chứa toàn bộ tài liệu phân tích, thiết kế, schema và hướng dẫn làm việc của dự án.

Tất cả thành viên cần đọc tài liệu trong `docs/` trước khi code.

### `integration/`

Chứa phần tích hợp pipeline tổng thể.

Thư mục này dùng để kết nối output của các module riêng lẻ thành một luồng xử lý hoàn chỉnh.

Leader hoặc người phụ trách tích hợp sẽ quản lý chính thư mục này.

### Module pipeline

Chi tiết vai trò từng module: [`docs/details/01_system_architecture.md` §4](docs/details/01_system_architecture.md). Stage spec triển khai: `docs/details/03`–`10`.

| Thư mục | Output chính |
| ------- | ------------ |
| `input_processor/` | `media_metadata.json` |
| `audio_analyzer/` | `audio_segments.json` |
| `video_analyzer/` | `clip_metadata.json` |
| `embedding_indexer/` | `embedding_metadata.json` |
| `matching_engine/` | `matching_candidates.json` |
| `timeline_planner/` | `timeline.json` |
| `review_ui/` | `timeline.json` (cập nhật) |
| `renderer/` | `final_video.mp4`, `render_log.json` |

### `shared/`

Chứa các thành phần dùng chung:

* Kiểu dữ liệu chung.
* Hàm đọc/ghi JSON.
* Validator kiểm tra schema.
* Helper xử lý thời gian, path, duration.

Không tự ý sửa các file trong `shared/` nếu chưa thống nhất với leader, vì đây là phần dùng chung giữa nhiều module.

### `data/`

Chứa dữ liệu chạy thử và output trung gian.

Không commit video/audio nặng lên GitHub nếu chưa thống nhất với nhóm.

Gợi ý cấu trúc:

```text
data/
├── raw/
├── normalized/
├── keyframes/
├── intermediate/
└── final/
```

### `scripts/`

Chứa các script hỗ trợ:

* Chạy demo.
* Kiểm tra schema JSON.
* Dọn output tạm.
* Chạy pipeline mẫu.

## 5. Thứ tự đọc tài liệu

**Thành viên mới phụ trách Stage X:** đọc theo [`docs/README.md` §7.2](docs/README.md) — `00` → `01` → `02` → stage spec của mình (full) → stage liền kề (chỉ §4 Input, §5 Output, §9 Handoff).

Danh sách đầy đủ theo vai trò (leader, schema, samples): [`docs/README.md` §7](docs/README.md).

## 6. Quy tắc làm việc chung

### 6.1. Code theo module

Mỗi thành viên làm việc chủ yếu trong thư mục module mình phụ trách.

Ví dụ:

* Người phụ trách audio làm trong `audio_analyzer/`.
* Người phụ trách video làm trong `video_analyzer/`.
* Người phụ trách matching làm trong `matching_engine/`.
* Người phụ trách UI làm trong `review_ui/`.
* Người phụ trách render làm trong `renderer/`.

Không sửa code trong module của người khác nếu chưa trao đổi trước.

### 6.2. Tuân thủ data contract

Các module có thể dùng thư viện và cách triển khai khác nhau, nhưng input/output phải tuân thủ schema đã thống nhất trong `docs/schemas/` và `docs/details/02_data_contract.md`.

Không tự ý đổi format JSON.

Trước khi tích hợp, chạy `python scripts/validate_json.py` trên `docs/samples/`.

Nếu cần đổi schema, phải trao đổi với leader và cập nhật tài liệu trước.

### 6.3. Mỗi module cần có README riêng

Mỗi thư mục module nên có một file `README.md` mô tả:

* Module này làm gì.
* Input là gì.
* Output là gì.
* Cách chạy.
* Cách test.
* Các thư viện cần cài.
* Ví dụ output mẫu.

### 6.4. Ưu tiên output kiểm tra được

Mỗi module nên tạo output trung gian rõ ràng để dễ debug.

Ví dụ:

* Audio module xuất `audio_segments.json`.
* Video module xuất `clip_metadata.json`.
* Matching module xuất `matching_candidates.json`.
* Timeline module xuất `timeline.json`.
* Renderer xuất `final_video.mp4`.

### 6.5. Không commit file nặng

Không commit các file lớn như:

* `.mp4`
* `.mov`
* `.mkv`
* `.wav`
* `.mp3`
* File model lớn
* Output render nặng

Các file này nên đặt trong `data/` và được ignore bằng `.gitignore`.

Chỉ nên commit:

* Source code.
* File cấu hình nhỏ.
* File JSON sample nhỏ.
* Tài liệu.
* Script hỗ trợ.

## 7. Quy trình phát triển đề xuất

### Bước 1: Đọc tài liệu

Trước khi code, mỗi thành viên cần đọc:

* Tài liệu tổng quan.
* Data contract.
* Stage spec liên quan đến module của mình.

### Bước 2: Làm module độc lập

Mỗi thành viên phát triển module của mình bằng dữ liệu mẫu trong `docs/samples/`.

Không cần chờ toàn bộ pipeline hoàn thiện mới bắt đầu làm.

### Bước 3: Xuất output đúng schema

Mỗi module phải xuất output đúng schema để module sau có thể sử dụng.

Ví dụ:

```text
audio_analyzer
→ audio_segments.json
→ matching_engine sử dụng
```

### Bước 4: Test module riêng

Mỗi module cần có cách test riêng trước khi tích hợp.

Ví dụ:

* Audio module test bằng audio ngắn.
* Video module test bằng video ngắn.
* Matching module test bằng JSON mẫu.
* Renderer test bằng `timeline_sample.json`, `media_metadata_sample.json` và `render_config_sample.json`.

### Bước 5: Tích hợp dần

Sau khi module chạy độc lập, leader sẽ tích hợp từng phần vào pipeline chung trong `integration/`.

Không chờ tất cả module hoàn hảo mới tích hợp.

### Bước 6: Chạy demo end-to-end

Mục tiêu cuối là chạy được một demo hoàn chỉnh:

```text
Input video/audio
→ intermediate JSON files
→ review/update timeline
→ final_video.mp4
```

## 8. Output trung gian chuẩn

Các file output trung gian quan trọng gồm:

```text
media_metadata.json
audio_segments.json
clip_metadata.json
embedding_metadata.json
embedding/index files
matching_candidates.json
timeline.json
render_log.json
```

Artifact cuối cùng:

```text
final_video.mp4
```

Ý nghĩa từng file sẽ được mô tả chi tiết trong `docs/details/02_data_contract.md` và `docs/schemas/`.

## 9. Nguyên tắc tích hợp

Khi tích hợp module, cần kiểm tra theo thứ tự:

1. File output có tồn tại không?
2. JSON có đúng format không?
3. Các field bắt buộc có đủ không?
4. Đơn vị thời gian có thống nhất không?
5. `clip_id`, `segment_id`, `video_id` có khớp giữa các file không?
6. Module sau có đọc được output của module trước không?
7. Pipeline có chạy được với dữ liệu mẫu không?

Nếu có lỗi, ưu tiên kiểm tra file JSON trung gian trước khi sửa code.

## 10. Quy ước chung

### 10.1. Đơn vị thời gian

Tất cả thời gian trong JSON sử dụng đơn vị giây.

Ví dụ:

```json
{
  "start": 12.5,
  "end": 18.2
}
```

### 10.2. Score

Các điểm số nên nằm trong khoảng từ `0.0` đến `1.0`.

Ví dụ:

```json
{
  "semantic_score": 0.82,
  "visual_quality_score": 0.76,
  "final_score": 0.79
}
```

### 10.3. Confidence

Confidence dùng ba mức chính:

```text
high
medium
low
```

### 10.4. ID

ID nên đặt ngắn gọn, dễ đọc và thống nhất.

Ví dụ:

```text
video_01
a001
v01_c003
candidates_a001
```

## 11. Phân công module tổng quát

| Vai trò              | Thư mục chính                      | Output chính                  |
| -------------------- | ---------------------------------- | ----------------------------- |
| Leader / Integration | `docs/`, `integration/`, `shared/` | Schema, pipeline, sample data |
| Input Processing     | `input_processor/`                 | `media_metadata.json`         |
| Audio / NLP          | `audio_analyzer/`                  | `audio_segments.json`         |
| Video / CV           | `video_analyzer/`                  | `clip_metadata.json`          |
| Embedding / Indexing | `embedding_indexer/`               | `embedding_metadata.json`, embedding/index files |
| Matching / Retrieval | `matching_engine/`                 | `matching_candidates.json`    |
| Timeline Planning    | `timeline_planner/`                | `timeline.json`               |
| UI Review            | `review_ui/`                       | Updated `timeline.json`       |
| Rendering            | `renderer/`                        | `final_video.mp4`, `render_log.json` |

Một thành viên có thể phụ trách nhiều module tùy theo phân công thực tế.

## 12. Trạng thái hiện tại

Repo sẵn sàng cho giai đoạn triển khai module:

* Tài liệu thiết kế và Data Contract đã thống nhất.
* Schema và mẫu JSON trong `docs/samples/` đã validate cross-file.
* Chưa có implementation code; bắt đầu từ module trong `docs/details/11_team_assignment.md`.

Trước tích hợp: `python scripts/validate_json.py`.

## 13. Mục tiêu làm việc của repo

Repo này không chỉ chứa code, mà còn là nơi thống nhất cách cả nhóm hiểu và phát triển dự án.

Mỗi phần code cần bám theo tài liệu thiết kế, đặc biệt là:

* Scope MVP.
* Kiến trúc hệ thống.
* Data Contract.
* Stage specification.
* Kế hoạch tích hợp.

Nếu có thay đổi lớn trong cách làm, cần cập nhật tài liệu tương ứng để cả nhóm không bị lệch hướng.
