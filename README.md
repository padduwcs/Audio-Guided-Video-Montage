# Audio-Guided Video Montage

## 1. Giới thiệu dự án

Dự án xây dựng một hệ thống dựng video bán tự động dựa trên audio thuyết minh.

Đầu vào của hệ thống gồm:

* Một hoặc nhiều video nguồn có sẵn.
* Một file audio thuyết minh / voice-over.

Hệ thống sẽ phân tích nội dung audio, phân tích video nguồn, chọn các đoạn video phù hợp với từng đoạn lời nói, lập timeline dựng video, cho phép người dùng kiểm tra và chỉnh sửa cơ bản, sau đó render ra video hoàn chỉnh.

Mục tiêu của dự án không phải là tạo video mới từ đầu, mà là tận dụng các cảnh có sẵn trong video nguồn để tạo ra một bản dựng phù hợp nhất với audio thuyết minh.

## 2. Mục tiêu MVP

Trong phạm vi MVP, hệ thống cần có một luồng xử lý end-to-end cơ bản:

```text
Video nguồn + Audio thuyết minh
→ Phân tích audio
→ Phân tích video
→ Tìm top-k clip phù hợp
→ Tạo timeline JSON
→ Review / chỉnh sửa cơ bản
→ Render video cuối
```

MVP cần làm được:

* Nhận video và audio đầu vào.
* Tạo transcript có timestamp từ audio.
* Chia audio thành các segment có ý nghĩa.
* Tách video nguồn thành các clip candidate.
* Trích keyframe và tính quality score cho clip.
* Tạo embedding / đặc trưng để so khớp audio segment với clip.
* Trả về top-k clip phù hợp cho từng audio segment.
* Tạo `timeline.json`.
* Có UI review cơ bản để xem timeline và đổi clip trong top-k.
* Render video cuối từ `timeline.json`.

MVP chưa tập trung vào:

* Hiệu ứng dựng video nâng cao.
* Timeline nhiều track như phần mềm dựng video chuyên nghiệp.
* Color grading.
* Motion graphic phức tạp.
* Chỉnh sửa audio chi tiết.
* Tự động tạo caption đẹp.

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
│   │   ├── matching_candidates.schema.md
│   │   └── timeline.schema.md
│   │
│   └── samples/
│       ├── audio_segments_sample.json
│       ├── clip_metadata_sample.json
│       ├── matching_candidates_sample.json
│       └── timeline_sample.json
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

### `input_processor/`

Phụ trách chuẩn hóa dữ liệu đầu vào:

* Kiểm tra video/audio.
* Chuẩn hóa định dạng.
* Lấy metadata.
* Tạo thông tin media đầu vào.

### `audio_analyzer/`

Phụ trách xử lý audio:

* ASR / speech-to-text.
* Transcript có timestamp.
* Chia audio thành segment.
* Sinh query cho từng segment.

Output chính là `audio_segments.json`.

### `video_analyzer/`

Phụ trách xử lý video nguồn:

* Scene detection.
* Tạo clip candidate.
* Trích keyframe.
* Tính quality score.

Output chính là `clip_metadata.json`.

### `embedding_indexer/`

Phụ trách tạo embedding và index:

* Text embedding cho audio query.
* Image/video embedding cho keyframe hoặc clip.
* Lưu index phục vụ truy vấn nhanh.

### `matching_engine/`

Phụ trách so khớp audio segment với clip:

* Nhận `audio_segments.json`.
* Nhận `clip_metadata.json` và embedding/index.
* Trả về top-k clip phù hợp cho từng audio segment.
* Gán score và confidence.

Output chính là `matching_candidates.json`.

### `timeline_planner/`

Phụ trách lập timeline dựng video:

* Chọn clip mặc định từ matching result.
* Xử lý duration.
* Xử lý clip ngắn hơn hoặc dài hơn audio segment.
* Thêm speed, transition, fallback nếu cần.

Output chính là `timeline.json`.

### `review_ui/`

Phụ trách giao diện review:

* Hiển thị audio segment.
* Hiển thị transcript.
* Hiển thị clip được chọn.
* Hiển thị top-k clip thay thế.
* Cho phép người dùng đổi clip hoặc chỉnh thông số cơ bản.
* Cập nhật `timeline.json`.

### `renderer/`

Phụ trách render video cuối:

* Đọc `timeline.json`.
* Cắt clip từ video nguồn.
* Chỉnh speed nếu cần.
* Thêm transition cơ bản.
* Ghép voice-over làm audio chính.
* Xuất video cuối `.mp4`.

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

Thành viên mới nên đọc tài liệu theo thứ tự sau:

1. `docs/problem.md`
   Hiểu phát biểu bài toán và nhu cầu thực tế.

2. `docs/analysis.md`
   Hiểu phân tích tổng thể và hướng thiết kế hệ thống.

3. `docs/README.md`
   Hiểu bản đồ tài liệu trong thư mục `docs/`.

4. `docs/details/00_project_scope.md`
   Hiểu MVP làm gì và không làm gì.

5. `docs/details/01_system_architecture.md`
   Hiểu kiến trúc module và luồng dữ liệu tổng thể.

6. `docs/details/02_data_contract.md`
   Đọc kỹ trước khi code, vì đây là chuẩn input/output chung.

7. File stage tương ứng với phần mình phụ trách.
   Ví dụ người làm audio đọc `04_stage_2_audio_analysis.md`.

8. `docs/details/11_team_assignment.md`
   Xem phân công nhiệm vụ.

9. `docs/details/12_integration_plan.md`
   Đọc trước khi tích hợp module vào pipeline chung.

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

Các module có thể dùng thư viện và cách triển khai khác nhau, nhưng input/output phải tuân thủ schema đã thống nhất trong `docs/schemas/`.

Không tự ý đổi format JSON.

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
* Renderer test bằng `timeline_sample.json`.

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
matching_candidates.json
timeline.json
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
  "quality_score": 0.76,
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
| Embedding / Indexing | `embedding_indexer/`               | Embedding/index files         |
| Matching / Retrieval | `matching_engine/`                 | `matching_candidates.json`    |
| Timeline Planning    | `timeline_planner/`                | `timeline.json`               |
| UI Review            | `review_ui/`                       | Updated `timeline.json`       |
| Rendering            | `renderer/`                        | `final_video.mp4`             |

Một thành viên có thể phụ trách nhiều module tùy theo phân công thực tế.

## 12. Trạng thái hiện tại

Hiện tại repo đang ở giai đoạn thiết kế nền:

* Đã có phát biểu bài toán.
* Đã có phân tích ý tưởng tổng thể.
* Đang xây dựng tài liệu chi tiết cho từng stage.
* Chưa chốt hoàn toàn schema và sample data.

Các thành viên nên ưu tiên đọc tài liệu trước khi triển khai code.

## 13. Mục tiêu làm việc của repo

Repo này không chỉ chứa code, mà còn là nơi thống nhất cách cả nhóm hiểu và phát triển dự án.

Mỗi phần code cần bám theo tài liệu thiết kế, đặc biệt là:

* Scope MVP.
* System architecture.
* Data contract.
* Stage specification.
* Integration plan.

Nếu có thay đổi lớn trong cách làm, cần cập nhật tài liệu tương ứng để cả nhóm không bị lệch hướng.
