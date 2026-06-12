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

Tóm tắt phạm vi, MVP và demo: [`details/00_project_scope.md`](details/00_project_scope.md).

Pipeline và module: [`details/01_system_architecture.md`](details/01_system_architecture.md) §2.

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

#### Stage spec (`03`–`10`)

Mỗi file stage spec theo template 12 mục (mục tiêu, pipeline, trách nhiệm, I/O, contract fields, quy trình, test, …). Owner module đọc file tương ứng trước khi code.

| File | Module | Output chính |
| ---- | ------ | ------------ |
| [`03_stage_1_input_processing.md`](details/03_stage_1_input_processing.md) | `input_processor/` | `media_metadata.json` |
| [`04_stage_2_audio_analysis.md`](details/04_stage_2_audio_analysis.md) | `audio_analyzer/` | `audio_segments.json` |
| [`05_stage_3_video_analysis.md`](details/05_stage_3_video_analysis.md) | `video_analyzer/` | `clip_metadata.json` |
| [`06_stage_4_embedding_indexing.md`](details/06_stage_4_embedding_indexing.md) | `embedding_indexer/` | `embedding_metadata.json` |
| [`07_stage_5_matching_engine.md`](details/07_stage_5_matching_engine.md) | `matching_engine/` | `matching_candidates.json` |
| [`08_stage_6_timeline_planning.md`](details/08_stage_6_timeline_planning.md) | `timeline_planner/` | `timeline.json` |
| [`09_stage_7_review_ui.md`](details/09_stage_7_review_ui.md) | `review_ui/` | `timeline.json` (cập nhật) |
| [`10_stage_8_rendering.md`](details/10_stage_8_rendering.md) | `renderer/` | `final_video.mp4`, `render_log.json` |

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
6. Stage spec của module phụ trách (xem §7.2 nếu là owner stage)
7. `details/11_team_assignment.md`
8. `details/12_integration_plan.md`

### 7.2. Nếu phụ trách Stage X (thành viên mới)

Đây là thứ tự **bắt buộc tối thiểu** trước khi code module của mình.

| Bước | Tài liệu | Cách đọc |
| ---- | -------- | -------- |
| 1 | [`details/00_project_scope.md`](details/00_project_scope.md) | Toàn bộ — hiểu MVP và phạm vi |
| 2 | [`details/01_system_architecture.md`](details/01_system_architecture.md) | Toàn bộ — pipeline, module, ranh giới |
| 3 | [`details/02_data_contract.md`](details/02_data_contract.md) | Toàn bộ — **đọc kỹ** trước khi định nghĩa output |
| 4 | File stage mình phụ trách (`03`–`10`) | **Toàn bộ** — logic, test, acceptance, checklist |
| 5 | Stage liền kề (trước + sau) | **Chỉ** §4 Input · §5 Output · §9 Handoff |

Mỗi stage spec dùng cùng template 12 mục; §4 = input, §5 = output, §9 = điều kiện bàn giao.

**Bổ sung sau bước 1–5:** schema + sample JSON của file output stage mình (`docs/schemas/`, `docs/samples/`); README module (`<folder>/README.md`).

#### Bảng stage → file spec → stage liền kề

| Stage | Module | File spec (bước 4 — đọc full) | Stage trước (bước 5 — §4/§5/§9) | Stage sau (bước 5 — §4/§5/§9) |
| ----- | ------ | ------------------------------- | -------------------------------- | ----------------------------- |
| 1 | `input_processor/` | [`03_stage_1_input_processing.md`](details/03_stage_1_input_processing.md) | — | [`04_stage_2_audio_analysis.md`](details/04_stage_2_audio_analysis.md) |
| 2 | `audio_analyzer/` | [`04_stage_2_audio_analysis.md`](details/04_stage_2_audio_analysis.md) | [`03_stage_1_input_processing.md`](details/03_stage_1_input_processing.md) | [`05_stage_3_video_analysis.md`](details/05_stage_3_video_analysis.md) |
| 3 | `video_analyzer/` | [`05_stage_3_video_analysis.md`](details/05_stage_3_video_analysis.md) | [`04_stage_2_audio_analysis.md`](details/04_stage_2_audio_analysis.md) | [`06_stage_4_embedding_indexing.md`](details/06_stage_4_embedding_indexing.md) |
| 4 | `embedding_indexer/` | [`06_stage_4_embedding_indexing.md`](details/06_stage_4_embedding_indexing.md) | [`05_stage_3_video_analysis.md`](details/05_stage_3_video_analysis.md) | [`07_stage_5_matching_engine.md`](details/07_stage_5_matching_engine.md) |
| 5 | `matching_engine/` | [`07_stage_5_matching_engine.md`](details/07_stage_5_matching_engine.md) | [`06_stage_4_embedding_indexing.md`](details/06_stage_4_embedding_indexing.md) | [`08_stage_6_timeline_planning.md`](details/08_stage_6_timeline_planning.md) |
| 6 | `timeline_planner/` | [`08_stage_6_timeline_planning.md`](details/08_stage_6_timeline_planning.md) | [`07_stage_5_matching_engine.md`](details/07_stage_5_matching_engine.md) | [`09_stage_7_review_ui.md`](details/09_stage_7_review_ui.md) |
| 7 | `review_ui/` | [`09_stage_7_review_ui.md`](details/09_stage_7_review_ui.md) | [`08_stage_6_timeline_planning.md`](details/08_stage_6_timeline_planning.md) | [`10_stage_8_rendering.md`](details/10_stage_8_rendering.md) |
| 8 | `renderer/` | [`10_stage_8_rendering.md`](details/10_stage_8_rendering.md) | [`09_stage_7_review_ui.md`](details/09_stage_7_review_ui.md) | — |

**Ghi chú pipeline:**

* Stage 2 (Audio) và Stage 3 (Video) chạy **song song** sau Stage 1 — không phụ thuộc lẫn nhau; bước 5 chỉ cần stage liền kề theo bảng.
* Stage 4 đọc output từ **cả** Stage 2 và Stage 3. Ngoài bước 5, nên đọc thêm [`04_stage_2_audio_analysis.md`](details/04_stage_2_audio_analysis.md) §4/§5/§9.
* Stage 1 không có stage trước; owner Stage 1 nên đọc thêm [`05_stage_3_video_analysis.md`](details/05_stage_3_video_analysis.md) §4/§5/§9 (Video Analyzer cũng nhận output Stage 1, song song với Audio).
* Stage 8 không có stage sau.
* Leader / integration: đọc toàn bộ stage spec `03`–`10` (§7.3).

**Ví dụ — owner Stage 5 (Matching Engine):**

```text
1. details/00_project_scope.md
2. details/01_system_architecture.md
3. details/02_data_contract.md
4. details/07_stage_5_matching_engine.md          (full)
5a. details/06_stage_4_embedding_indexing.md    (§4, §5, §9)
5b. details/08_stage_6_timeline_planning.md     (§4, §5, §9)
+ schemas/matching_candidates.schema.md
+ samples/matching_candidates_sample.json
```

### 7.3. Với leader / người tích hợp

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

### 7.4. Với người làm Audio Analyzer

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

### 7.5. Với người làm Video Analyzer

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

### 7.6. Với người làm Embedding / Matching

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

### 7.7. Với người làm Timeline Planner

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

### 7.8. Với người làm Review UI

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

### 7.9. Với người làm Renderer

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

Toàn bộ quy ước (thời gian, score, confidence, ID, path, mapping, validate): [`details/02_data_contract.md`](details/02_data_contract.md) §2 và §13–14.

Khi mâu thuẫn: **Data Contract → schemas → samples → stage spec → README module**.

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

* Phạm vi, kiến trúc, Data Contract, 8 stage spec (template 12 mục, tham chiếu `02`/schemas/samples), phân công nhóm và kế hoạch tích hợp.
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
