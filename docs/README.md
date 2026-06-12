# Hướng dẫn tài liệu

## 1. Mục đích của thư mục `docs/`

Thư mục `docs/` chứa toàn bộ tài liệu phân tích, thiết kế và quy ước phát triển của dự án **Audio-Guided Video Montage**.

Tài liệu trong thư mục này dùng để:

* Giúp thành viên hiểu đúng bài toán.
* Thống nhất phạm vi MVP.
* Thống nhất kiến trúc hệ thống.
* Thống nhất input/output giữa các module.
* Làm cơ sở để phân công công việc.
* Giúp từng thành viên tự phát triển module của mình mà không bị lệch hướng.
* Giúp quá trình tích hợp, debug và báo cáo diễn ra rõ ràng hơn.

Trước khi code, mỗi thành viên cần đọc các tài liệu liên quan trong `docs/`. Thứ tự ưu tiên khi triển khai: Data Contract → schemas → samples → stage spec → README module.

## 2. Tổng quan dự án

Dự án xây dựng một hệ thống dựng video bán tự động theo audio thuyết minh.

Đầu vào:

* Một hoặc nhiều video nguồn có sẵn.
* Một file audio thuyết minh / voice-over.

Đầu ra:

* Video hoàn chỉnh `final_video.mp4`.
* Timeline dựng video `timeline.json`.
* Các file trung gian phục vụ phân tích, matching, review và render.

Luồng xử lý tổng quát:

```text
Video nguồn + Audio thuyết minh
→ Input Processing
→ Audio Analysis + Video Analysis
→ Tạo embedding / đặc trưng
→ Matching audio segment với top-k clip
→ Tạo timeline JSON
→ Review và chỉnh sửa trên UI
→ Render video cuối
```

Dự án không nhằm tạo video mới từ đầu bằng AI. Hệ thống chỉ sử dụng các cảnh có sẵn trong video nguồn để tạo ra bản dựng mới phù hợp nhất với audio thuyết minh.

## 3. Cấu trúc tài liệu

```text
docs/
│
├── README.md
├── problem.md
├── analysis.md
│
├── details/
│   ├── 00_project_scope.md
│   ├── 01_system_architecture.md
│   ├── 02_data_contract.md
│   ├── 03_stage_1_input_processing.md
│   ├── 04_stage_2_audio_analysis.md
│   ├── 05_stage_3_video_analysis.md
│   ├── 06_stage_4_embedding_indexing.md
│   ├── 07_stage_5_matching_engine.md
│   ├── 08_stage_6_timeline_planning.md
│   ├── 09_stage_7_review_ui.md
│   ├── 10_stage_8_rendering.md
│   ├── 11_team_assignment.md
│   └── 12_integration_plan.md
│
├── schemas/
│   ├── media_metadata.schema.md
│   ├── audio_segments.schema.md
│   ├── clip_metadata.schema.md
│   ├── embedding_metadata.schema.md
│   ├── matching_candidates.schema.md
│   ├── timeline.schema.md
│   ├── render_config.schema.md
│   ├── render_log.schema.md
│   └── evaluation_report.schema.md
│
└── samples/
    ├── media_metadata_sample.json
    ├── audio_segments_sample.json
    ├── clip_metadata_sample.json
    ├── embedding_metadata_sample.json
    ├── embedding_index_sample/
    ├── matching_candidates_sample.json
    ├── timeline_sample.json
    ├── render_config_sample.json
    └── render_log_sample.json
```

## 4. Vai trò của từng nhóm tài liệu

### 4.1. Tài liệu nền

#### `problem.md`

Phát biểu bài toán gốc.

File này dùng để hiểu:

* Bài toán xuất phát từ nhu cầu gì.
* Input và output mong muốn ban đầu là gì.
* Vì sao bài toán có ý nghĩa thực tế.
* Những tình huống thực tế mà hệ thống cần hỗ trợ.

Nên đọc đầu tiên.

#### `analysis.md`

Phân tích tổng thể bài toán và hướng giải quyết.

File này dùng để hiểu:

* Vì sao chọn hướng bán tự động.
* Vì sao cần chia hệ thống thành nhiều module.
* Vì sao cần `timeline.json`.
* Vì sao cần top-k clip thay vì chỉ chọn top-1.
* Những rủi ro chính của bài toán.
* MVP nên làm đến đâu.

Nên đọc sau `problem.md`. Triển khai code theo Data Contract và `docs/samples/`, không lấy JSON từ file này.

### 4.2. Tài liệu chi tiết trong `details/`

#### `00_project_scope.md`

Chốt phạm vi sản phẩm.

File này trả lời:

* Sản phẩm cuối cùng là gì?
* MVP cần có những chức năng nào?
* Những chức năng nào chưa làm trong MVP?
* Input/output chính của hệ thống là gì?
* Demo cuối cần đạt mức nào?

Tất cả thành viên nên đọc file này để không hiểu lệch mục tiêu dự án.

#### `01_system_architecture.md`

Chốt kiến trúc hệ thống và luồng dữ liệu tổng thể.

File này mô tả:

* Các module chính trong hệ thống.
* Vai trò của từng module.
* Module nào tạo file nào.
* Module nào đọc file nào.
* Các module phụ thuộc nhau như thế nào.
* Phần nào có thể phát triển song song.
* Vì sao `timeline.json` là trung tâm của hệ thống.

Tất cả thành viên nên đọc file này trước khi làm module riêng.

#### `02_data_contract.md`

Chốt Data Contract giữa các module.

Đây là một trong những file quan trọng nhất của dự án.

File này định nghĩa:

* Các file JSON trung gian.
* Cấu trúc dữ liệu của từng file.
* Các field bắt buộc và optional.
* Quy ước ID.
* Quy ước thời gian.
* Quy ước score và confidence.
* Mapping giữa các file.
* Quy tắc validate dữ liệu.

Mọi thành viên cần đọc kỹ file này trước khi code.

Không tự ý đổi schema hoặc tên field nếu chưa thống nhất với leader.

#### `03_stage_1_input_processing.md`

Tài liệu chi tiết cho Stage 1: Input Processing.

Stage này phụ trách:

* Kiểm tra video/audio đầu vào.
* Chuẩn hóa định dạng nếu cần.
* Lấy metadata.
* Tạo `media_metadata.json`.

Người phụ trách input processing cần đọc kỹ file này.

#### `04_stage_2_audio_analysis.md`

Tài liệu chi tiết cho Stage 2: Audio Analysis.

Stage này phụ trách:

* Chạy ASR.
* Tạo transcript có timestamp.
* Chia audio thành segment.
* Tạo query cho matching.
* Xuất `audio_segments.json`.

Người phụ trách audio/NLP cần đọc kỹ file này.

#### `05_stage_3_video_analysis.md`

Tài liệu chi tiết cho Stage 3: Video Analysis.

Stage này phụ trách:

* Scene detection / shot detection.
* Tạo clip candidate.
* Trích keyframe.
* Tính quality score.
* Xuất `clip_metadata.json`.

Người phụ trách video/computer vision cần đọc kỹ file này.

#### `06_stage_4_embedding_indexing.md`

Tài liệu chi tiết cho Stage 4: Embedding and Indexing.

Stage này phụ trách:

* Tạo text embedding cho audio segment.
* Tạo image/video embedding cho keyframe hoặc clip.
* Lưu embedding/index.
* Xuất `embedding_metadata.json`.

Người phụ trách embedding/retrieval cần đọc kỹ file này.

#### `07_stage_5_matching_engine.md`

Tài liệu chi tiết cho Stage 5: Matching Engine.

Stage này phụ trách:

* So khớp audio segment với clip candidate.
* Tính semantic score.
* Kết hợp `visual_quality_score` từ quality của clip, duration fit, diversity, continuity nếu có.
* Trả về top-k clip.
* Gán confidence.
* Xuất `matching_candidates.json`.

Người phụ trách matching cần đọc kỹ file này.

#### `08_stage_6_timeline_planning.md`

Tài liệu chi tiết cho Stage 6: Timeline Planning.

Stage này phụ trách:

* Chọn clip mặc định cho từng audio segment.
* Xử lý clip dài hơn hoặc ngắn hơn audio.
* Cho phép một audio segment có nhiều visual items.
* Thêm speed, transition, fallback nếu cần.
* Xuất `timeline.json`.

Người phụ trách timeline hoặc integration cần đọc kỹ file này.

#### `09_stage_7_review_ui.md`

Tài liệu chi tiết cho Stage 7: Review UI.

Stage này phụ trách:

* Hiển thị timeline.
* Hiển thị transcript.
* Hiển thị clip đang chọn.
* Hiển thị top-k candidate.
* Cho phép người dùng đổi clip.
* Cho phép chỉnh một số tham số cơ bản.
* Cập nhật `timeline.json`.

Người phụ trách UI cần đọc kỹ file này.

#### `10_stage_8_rendering.md`

Tài liệu chi tiết cho Stage 8: Rendering.

Stage này phụ trách:

* Đọc `timeline.json`.
* Cắt clip theo timeline.
* Scale/crop video.
* Ghép transition cơ bản.
* Ghép audio thuyết minh làm audio chính.
* Xuất `final_video.mp4`.

Người phụ trách renderer cần đọc kỹ file này.

#### `11_team_assignment.md`

Tài liệu phân công công việc ở mức bản nền. File này dùng để chuẩn bị chia việc, nhưng khi triển khai vẫn phải đối chiếu với Data Contract và stage spec tương ứng.

File này mô tả:

* Ai phụ trách module nào.
* Output cần giao của từng người.
* Những phần cần phối hợp.
* Trách nhiệm của leader.
* Cách kiểm tra tiến độ.

Tất cả thành viên nên đọc sau khi đã hiểu kiến trúc tổng thể.

#### `12_integration_plan.md`

Tài liệu kế hoạch tích hợp ở mức bản nền. File này dùng để định hướng thứ tự ghép module, nhưng pipeline thật vẫn phải validate theo Data Contract và output thực tế của từng module.

File này mô tả:

* Tích hợp module theo thứ tự nào.
* Dùng sample data như thế nào.
* Kiểm tra output từng module ra sao.
* Debug pipeline như thế nào.
* Điều kiện để demo end-to-end được xem là thành công.

Leader và các thành viên chuẩn bị merge module vào pipeline chung cần đọc kỹ file này.

## 5. Tài liệu schema trong `schemas/`

Thư mục `schemas/` mô tả bản schema tối thiểu của từng file dữ liệu quan trọng theo Data Contract.

Các file schema giúp thành viên kiểm tra output của module mình.

### `media_metadata.schema.md`

Schema cho `media_metadata.json`.

Dùng bởi:

* Input Processor.
* Audio Analyzer.
* Video Analyzer.
* Renderer.
* Integration pipeline.

### `audio_segments.schema.md`

Schema cho `audio_segments.json`.

Dùng bởi:

* Audio Analyzer.
* Matching Engine.
* Timeline Planner.
* Review UI.
* Evaluation.

### `clip_metadata.schema.md`

Schema cho `clip_metadata.json`.

Dùng bởi:

* Video Analyzer.
* Embedding Indexer.
* Matching Engine.
* Timeline Planner.
* Review UI.
* Renderer.

### `embedding_metadata.schema.md`

Schema cho `embedding_metadata.json`.

Dùng bởi:

* Embedding Indexer.
* Matching Engine.
* Evaluation.

### `matching_candidates.schema.md`

Schema cho `matching_candidates.json`.

Dùng bởi:

* Matching Engine.
* Timeline Planner.
* Review UI.
* Evaluation.

### `timeline.schema.md`

Schema cho `timeline.json`.

Dùng bởi:

* Timeline Planner.
* Review UI.
* Renderer.
* Evaluation.

### `render_config.schema.md`

Schema cho `render_config.json`.

Dùng bởi:

* Renderer.

### `render_log.schema.md`

Schema cho `render_log.json`.

Dùng bởi:

* Renderer.
* Integration pipeline.
* Evaluation.

### `evaluation_report.schema.md`

Schema cho `evaluation_report.json` (dùng khi làm đánh giá demo; chưa có sample JSON).

Dùng bởi:

* Đánh giá.
* Báo cáo/Demo.

## 6. Dữ liệu mẫu trong `samples/`

Thư mục `samples/` chứa mẫu JSON theo Data Contract. Tám file lõi được kiểm tra cross-file bằng `python scripts/validate_json.py`.

Mục đích:

* Giúp thành viên hiểu output cần tạo ra.
* Giúp test module trước khi module trước đó hoàn thiện.
* Giúp UI và renderer làm trước bằng dữ liệu giả.
* Giúp leader kiểm tra tích hợp sớm.

Các file mẫu chính:

```text
media_metadata_sample.json
audio_segments_sample.json
clip_metadata_sample.json
embedding_metadata_sample.json
embedding_index_sample/
matching_candidates_sample.json
timeline_sample.json
render_config_sample.json
render_log_sample.json
```

Ví dụ:

* Người làm UI có thể dùng `timeline_sample.json`, `matching_candidates_sample.json`, `clip_metadata_sample.json`, `audio_segments_sample.json` và `media_metadata_sample.json` để dựng giao diện mà không cần chờ pipeline thật hoàn thành.
* Người làm renderer có thể dùng `timeline_sample.json`, `media_metadata_sample.json`, `render_config_sample.json` và media source mẫu để test render video mà không cần chờ toàn bộ pipeline.
* Người làm matching có thể dùng `audio_segments_sample.json`, `clip_metadata_sample.json`, `embedding_metadata_sample.json`, `embedding_index_sample/` và nhìn `matching_candidates_sample.json` để biết output cần xuất ra.

## 7. Thứ tự đọc tài liệu đề xuất

### 7.1. Với tất cả thành viên

Tất cả thành viên nên đọc theo thứ tự:

1. `problem.md`
2. `analysis.md`
3. `details/00_project_scope.md`
4. `details/01_system_architecture.md`
5. `details/02_data_contract.md`
6. Stage spec của module phụ trách
7. `details/11_team_assignment.md`
8. `details/12_integration_plan.md`

### 7.2. Với leader / người tích hợp

Leader nên đọc và nắm toàn bộ:

```text
problem.md
analysis.md
details/00_project_scope.md
details/01_system_architecture.md
details/02_data_contract.md
details/03_stage_1_input_processing.md
details/04_stage_2_audio_analysis.md
details/05_stage_3_video_analysis.md
details/06_stage_4_embedding_indexing.md
details/07_stage_5_matching_engine.md
details/08_stage_6_timeline_planning.md
details/09_stage_7_review_ui.md
details/10_stage_8_rendering.md
details/11_team_assignment.md
details/12_integration_plan.md
schemas/
samples/
```

Leader chịu trách nhiệm giữ cho tài liệu, schema và code integration không bị lệch nhau.

### 7.3. Với người làm Audio Analyzer

Nên đọc:

```text
problem.md
analysis.md
details/00_project_scope.md
details/01_system_architecture.md
details/02_data_contract.md
details/04_stage_2_audio_analysis.md
schemas/audio_segments.schema.md
schemas/media_metadata.schema.md
samples/audio_segments_sample.json
samples/media_metadata_sample.json
```

Output chính cần tạo:

```text
audio_segments.json
```

### 7.4. Với người làm Video Analyzer

Nên đọc:

```text
problem.md
analysis.md
details/00_project_scope.md
details/01_system_architecture.md
details/02_data_contract.md
details/05_stage_3_video_analysis.md
schemas/clip_metadata.schema.md
schemas/media_metadata.schema.md
samples/clip_metadata_sample.json
samples/media_metadata_sample.json
```

Output chính cần tạo:

```text
clip_metadata.json
```

### 7.5. Với người làm Embedding / Matching

Nên đọc:

```text
details/00_project_scope.md
details/01_system_architecture.md
details/02_data_contract.md
details/06_stage_4_embedding_indexing.md
details/07_stage_5_matching_engine.md
schemas/audio_segments.schema.md
schemas/clip_metadata.schema.md
schemas/embedding_metadata.schema.md
schemas/matching_candidates.schema.md
samples/audio_segments_sample.json
samples/clip_metadata_sample.json
samples/embedding_metadata_sample.json
samples/embedding_index_sample/
samples/matching_candidates_sample.json
```

Output chính cần tạo:

```text
embedding_metadata.json
matching_candidates.json
```

### 7.6. Với người làm Timeline Planner

Nên đọc:

```text
details/00_project_scope.md
details/01_system_architecture.md
details/02_data_contract.md
details/08_stage_6_timeline_planning.md
schemas/matching_candidates.schema.md
schemas/timeline.schema.md
schemas/media_metadata.schema.md
schemas/clip_metadata.schema.md
samples/matching_candidates_sample.json
samples/timeline_sample.json
samples/media_metadata_sample.json
samples/clip_metadata_sample.json
```

Output chính cần tạo:

```text
timeline.json
```

### 7.7. Với người làm Review UI

Nên đọc:

```text
details/00_project_scope.md
details/01_system_architecture.md
details/02_data_contract.md
details/09_stage_7_review_ui.md
schemas/timeline.schema.md
schemas/matching_candidates.schema.md
schemas/clip_metadata.schema.md
schemas/audio_segments.schema.md
schemas/media_metadata.schema.md
samples/timeline_sample.json
samples/matching_candidates_sample.json
samples/clip_metadata_sample.json
samples/audio_segments_sample.json
samples/media_metadata_sample.json
```

Output chính cần tạo hoặc cập nhật:

```text
timeline.json (ghi đè data/intermediate/timeline.json, cập nhật updated_at)
```

### 7.8. Với người làm Renderer

Nên đọc:

```text
details/00_project_scope.md
details/01_system_architecture.md
details/02_data_contract.md
details/10_stage_8_rendering.md
schemas/timeline.schema.md
schemas/media_metadata.schema.md
schemas/clip_metadata.schema.md
schemas/render_config.schema.md
samples/timeline_sample.json
samples/media_metadata_sample.json
samples/render_config_sample.json
```

Output chính cần tạo:

```text
final_video.mp4
render_log.json
```

## 8. Quy tắc khi làm việc với tài liệu

### 8.1. Không tự ý đổi Data Contract

Không tự ý đổi:

* Tên file JSON.
* Tên field.
* Kiểu dữ liệu.
* Quy ước ID.
* Quy ước score.
* Quy ước confidence.
* Cấu trúc `timeline.json`.

Nếu cần thay đổi, phải:

1. Trao đổi với leader.
2. Cập nhật `details/02_data_contract.md`.
3. Cập nhật file schema trong `schemas/`.
4. Cập nhật sample JSON trong `samples/`.
5. Thông báo cho các module bị ảnh hưởng.

### 8.2. Tài liệu phải đi trước thay đổi lớn

Nếu thay đổi lớn về module hoặc luồng dữ liệu, cần cập nhật tài liệu trước hoặc cùng lúc với code.

Không để tình trạng code đã đổi nhưng tài liệu vẫn mô tả theo cách cũ.

### 8.3. Mỗi module cần bám đúng stage spec

Khi làm module, thành viên cần đọc file stage tương ứng và bám theo:

* Mục tiêu.
* Input.
* Output.
* Quy trình xử lý.
* Fallback.
* Tiêu chí hoàn thành.
* Cách test độc lập.

Nếu thấy stage spec chưa rõ, cần hỏi lại trước khi code.

### 8.4. Sample data phải luôn đúng schema

Các file trong `samples/` phải là dữ liệu mẫu hợp lệ.

Không đưa dữ liệu mẫu sai schema vào repo, vì UI, renderer hoặc module khác có thể dùng các file này để test.

## 9. Quy ước dữ liệu quan trọng

### 9.1. Thời gian

Tất cả thời gian trong JSON dùng đơn vị giây.

Ví dụ:

```json
{
  "start": 12.5,
  "end": 18.2,
  "duration": 5.7
}
```

### 9.2. Score

Tất cả score nằm trong khoảng `0.0` đến `1.0`.

Ví dụ:

```json
{
  "semantic_score": 0.82,
  "visual_quality_score": 0.76,
  "final_score": 0.79
}
```

Nếu chưa tính được score, dùng `null`, không tự đặt giá trị giả gây hiểu nhầm.

### 9.3. Confidence

Confidence dùng ba mức:

```text
high
medium
low
```

Ý nghĩa:

* `high`: hệ thống khá chắc.
* `medium`: nên kiểm tra lại.
* `low`: cần người dùng kiểm tra.

### 9.4. ID

ID cần ổn định, dễ đọc và không chứa khoảng trắng.

Ví dụ:

```text
video_01
audio_01
a001
v01_c003
v01_c003_k01
candidates_a001
t001_i01
```

### 9.5. Path

Path nên là đường dẫn tương đối, không dùng đường dẫn tuyệt đối của máy cá nhân.

Ví dụ nên dùng:

```json
{
  "path": "data/normalized/video_01.mp4"
}
```

Không nên dùng:

```json
{
  "path": "C:/Users/Name/Desktop/project/video_01.mp4"
}
```

## 10. Quy tắc kiểm tra trước khi tích hợp

Trước khi đưa output của module vào pipeline chung, cần kiểm tra:

1. File output có tồn tại không?
2. JSON có parse được không?
3. Có đủ field bắt buộc không?
4. Kiểu dữ liệu có đúng không?
5. ID có khớp với các file liên quan không?
6. Thời gian `start`, `end`, `duration` có hợp lệ không?
7. Score có nằm trong khoảng `0.0` đến `1.0` không?
8. Path media hoặc keyframe có tồn tại không?
9. Module sau có thể đọc được output không?

Nếu pipeline lỗi, ưu tiên kiểm tra file JSON trung gian trước khi sửa code.

## 11. Cách sử dụng tài liệu trong quá trình phát triển

### 11.1. Khi bắt đầu nhận module

Thành viên cần:

1. Đọc phạm vi sản phẩm.
2. Đọc kiến trúc hệ thống.
3. Đọc Data Contract.
4. Đọc tài liệu stage của module mình.
5. Xem schema liên quan.
6. Xem sample JSON liên quan.
7. Viết README riêng cho module nếu chưa có.

### 11.2. Khi đang code

Trong quá trình code, cần liên tục đối chiếu:

* Output có đúng schema không?
* Có đúng tên field không?
* Có đúng đơn vị thời gian không?
* Có đúng quy ước ID không?
* Có tạo được file output mà module sau cần không?

### 11.3. Khi hoàn thành module

Trước khi báo hoàn thành, cần có:

* Code chạy được với dữ liệu mẫu hoặc dữ liệu thật nhỏ.
* File output đúng schema.
* README module có hướng dẫn chạy.
* Ví dụ output hoặc log chạy thử.
* Ghi chú các giới hạn hiện tại nếu có.

## 12. Trạng thái tài liệu

Bộ tài liệu đã thống nhất cho triển khai MVP:

* Phạm vi, kiến trúc, Data Contract, 8 stage spec, phân công nhóm và kế hoạch tích hợp.
* Schema và mẫu JSON trong `samples/` (kiểm tra bằng `scripts/validate_json.py`).

`evaluation_report.json` có schema; sample sẽ bổ sung khi làm đánh giá demo.

Khi thay đổi contract hoặc schema, cập nhật tài liệu và chạy lại validation trước khi merge.

## 13. Nguyên tắc chung

Nguyên tắc quan trọng nhất của dự án:

> Mỗi module có thể triển khai khác nhau, nhưng input/output phải tuân thủ Data Contract chung.

Điều này giúp:

* Các thành viên làm việc song song.
* Giảm conflict khi merge code.
* Dễ kiểm tra output.
* Dễ tích hợp pipeline.
* Dễ thay thế module nếu cần cải thiện.
* Dễ báo cáo và demo.

Tài liệu trong `docs/` là nguồn tham chiếu chính của dự án. Nếu code và tài liệu mâu thuẫn, cần kiểm tra lại và cập nhật để thống nhất trước khi tiếp tục phát triển.
