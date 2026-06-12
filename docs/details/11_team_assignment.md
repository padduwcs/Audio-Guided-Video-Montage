# 11. Team Assignment

## 1. Mục tiêu của tài liệu

Tài liệu này dùng để phân công công việc cho nhóm phát triển dự án **Audio-Guided Video Montage**.

Mục tiêu chính:

* Chia rõ trách nhiệm cho từng thành viên.
* Giúp mỗi người biết mình phụ trách module nào.
* Xác định input/output cần bàn giao của từng phần.
* Giảm việc làm trùng hoặc bỏ sót nhiệm vụ.
* Giúp leader theo dõi tiến độ và tích hợp hệ thống.
* Đảm bảo mọi module đều bám theo Data Contract hiện hành.

Nguyên tắc quan trọng:

> Mỗi thành viên có thể tự chọn cách triển khai bên trong module mình phụ trách, nhưng output phải đúng Data Contract để module sau có thể sử dụng được.

## 2. Nguyên tắc phân công

Dự án được chia theo module chức năng, không chia theo tên người hoặc chia theo file rời rạc.

Lý do:

* Mỗi module có trách nhiệm rõ ràng.
* Dễ phát triển song song.
* Dễ test độc lập.
* Dễ tích hợp vào pipeline chung.
* Dễ báo cáo vai trò của từng thành viên.

Các module chính gồm:

```text
input_processor
audio_analyzer
video_analyzer
embedding_indexer
matching_engine
timeline_planner
review_ui
renderer
integration
shared
```

Trong nhóm 5 người, một người có thể phụ trách nhiều module nếu các module có liên quan gần nhau.

## 3. Phân công tổng quan

| Thành viên | Vai trò chính                        | Module phụ trách chính                                         | Output chính                                          |
| ---------- | ------------------------------------ | -------------------------------------------------------------- | ----------------------------------------------------- |
| Người 1    | Leader / Integration / Data Contract | `docs/`, `integration/`, `shared/`, hỗ trợ `timeline_planner/` | Schema, sample data, integration pipeline, `timeline.json` (Timeline Planner) |
| Người 2    | Audio / NLP                          | `audio_analyzer/`                                              | `audio_segments.json`                                 |
| Người 3    | Video Processing / Computer Vision   | `input_processor/`, `video_analyzer/`                          | `media_metadata.json`, `clip_metadata.json`           |
| Người 4    | Embedding / Matching / Retrieval     | `embedding_indexer/`, `matching_engine/`                       | `embedding_metadata.json`, `matching_candidates.json` |
| Người 5    | Review UI / Renderer                 | `review_ui/`, `renderer/`                                      | UI review, `timeline.json` (sau chỉnh sửa người dùng), `final_video.mp4`, `render_log.json` |

Ghi chú:

* Timeline Planner (thường do Leader phụ trách) tạo `timeline.json` ban đầu.
* Người 5 cập nhật cùng file sau khi người dùng review/chỉnh trên UI.
* Nếu nhóm có năng lực frontend/backend không đều, có thể tách lại `review_ui/` và `renderer/` cho hai người khác nhau.
* Phân công này có thể điều chỉnh, nhưng không nên phá vỡ Data Contract.

## 4. Người 1 — Leader / System Integration / Data Contract

### 4.1. Vai trò

Người 1 chịu trách nhiệm giữ cho toàn bộ dự án đi đúng hướng.

Đây là người quản lý:

* Phạm vi MVP.
* Kiến trúc hệ thống.
* Data Contract.
* Cấu trúc repo.
* Sample data.
* Pipeline tích hợp.
* Tiến độ và chất lượng đầu ra của các module.

### 4.2. Module phụ trách

```text
docs/
integration/
shared/
timeline_planner/    hỗ trợ hoặc phụ trách chính nếu cần
```

### 4.3. Nhiệm vụ chính

Leader cần làm:

1. Chốt phạm vi MVP.
2. Chốt kiến trúc hệ thống.
3. Chốt Data Contract.
4. Tạo và cập nhật tài liệu trong `docs/`.
5. Tạo sample JSON cho các module test độc lập.
6. Quy định cấu trúc thư mục và quy tắc làm việc.
7. Theo dõi output của từng thành viên.
8. Kiểm tra output có đúng schema không.
9. Tích hợp các module thành pipeline chung.
10. Hỗ trợ xử lý lỗi khi module không ghép được với nhau.
11. Chuẩn bị demo end-to-end.
12. Tổng hợp nội dung phục vụ báo cáo và thuyết trình.

### 4.4. Output cần bàn giao

Leader cần tạo hoặc quản lý:

```text
docs/details/00_project_scope.md
docs/details/01_system_architecture.md
docs/details/02_data_contract.md
docs/details/03_stage_1_input_processing.md
docs/details/04_stage_2_audio_analysis.md
docs/details/05_stage_3_video_analysis.md
docs/details/06_stage_4_embedding_indexing.md
docs/details/07_stage_5_matching_engine.md
docs/details/08_stage_6_timeline_planning.md
docs/details/09_stage_7_review_ui.md
docs/details/10_stage_8_rendering.md
docs/details/11_team_assignment.md
docs/details/12_integration_plan.md
docs/samples/*.json
integration/
shared/
```

Output quan trọng nhất:

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
data/intermediate/timeline.json   (Timeline Planner, qua timeline_planner/ hoặc integration/)
```

### 4.5. Tiêu chí hoàn thành

Vai trò leader được xem là hoàn thành tốt khi:

* Các thành viên hiểu rõ việc mình cần làm.
* Mỗi module có input/output rõ ràng.
* Sample data đủ để các module test độc lập.
* Các module có thể tích hợp thông qua JSON trung gian.
* Pipeline có thể chạy demo end-to-end.
* Tài liệu đủ rõ để báo cáo và bảo vệ đồ án.

## 5. Người 2 — Audio / NLP

### 5.1. Vai trò

Người 2 phụ trách phân tích audio thuyết minh.

Mục tiêu là biến audio thành transcript có timestamp và chia thành các audio segment có ý nghĩa để hệ thống có thể tìm clip phù hợp.

### 5.2. Module phụ trách

```text
audio_analyzer/
```

### 5.3. Input cần đọc

```text
data/intermediate/media_metadata.json
```

Lấy audio từ `audio.normalized_path`. Chỉ chạy khi `audio.status` là `ready` hoặc `warning`.

### 5.4. Nhiệm vụ chính

Người phụ trách Audio/NLP cần làm:

1. Đọc `media_metadata.json`.
2. Lấy audio thuyết minh đã chuẩn hóa.
3. Chạy ASR để tạo transcript.
4. Lấy timestamp cho transcript.
5. Chia audio thành các segment có ý nghĩa.
6. Sinh `segment_id` dạng `a001`, `a002`, ...
7. Sinh `query` cho từng segment.
8. Trích keywords nếu có thể.
9. Tạo `translated_query` nếu Matching cần tiếng Anh.
10. Gán `segment_type` nếu xác định được.
11. Gán `asr_confidence` nếu ASR hỗ trợ.
12. Đánh dấu `needs_review` cho đoạn rủi ro.
13. Xuất `audio_segments.json`.
14. Xuất `audio_analysis_log.json` để debug nếu cần.

### 5.5. Output cần bàn giao

Output chính:

```text
data/intermediate/audio_segments.json
```

Output phụ:

```text
data/intermediate/audio_analysis_log.json
```

### 5.6. Module sử dụng output

Output của người 2 được dùng bởi:

```text
embedding_indexer/
matching_engine/
timeline_planner/
review_ui/
evaluation/
```

### 5.7. Tiêu chí hoàn thành

Module Audio Analyzer đạt yêu cầu khi:

* Đọc đúng audio từ `media_metadata.json`.
* Tạo được transcript có timestamp.
* Chia được segment hợp lý, không quá vụn, không quá dài.
* Mỗi segment có đủ `segment_id`, `start`, `end`, `duration`, `text`, `query`, `asr_confidence`.
* `query` không rỗng.
* Timestamp không overlap và tăng dần.
* Output đúng schema `audio_segments.json`.
* Matching Engine và Timeline Planner có thể đọc output để chạy tiếp.

## 6. Người 3 — Input Processing / Video Analysis

### 6.1. Vai trò

Người 3 phụ trách xử lý video nguồn và một phần chuẩn hóa dữ liệu đầu vào.

Vai trò này gồm hai phần:

* Chuẩn hóa video/audio và tạo metadata đầu vào.
* Phân tích video nguồn để tạo danh sách clip candidate.

### 6.2. Module phụ trách

```text
input_processor/
video_analyzer/
```

### 6.3. Input cần đọc

```text
data/raw/video_*.mp4
data/raw/video_*.mov
data/raw/video_*.mkv
data/raw/voiceover.*
```

Sau Stage 1, Video Analyzer đọc:

```text
data/intermediate/media_metadata.json
```

Video paths thực tế lấy từ `media_metadata.videos[].normalized_path`. Chỉ xử lý video có `status` là `ready` hoặc `warning`.

### 6.4. Nhiệm vụ chính với Input Processor

Người phụ trách cần làm:

1. Nhận danh sách video nguồn và audio thuyết minh.
2. Kiểm tra file tồn tại và đọc được.
3. Trích metadata video/audio.
4. Chuẩn hóa video nếu cần.
5. Chuẩn hóa audio nếu cần.
6. Sinh `video_id`, `audio_id`.
7. Xuất `media_metadata.json`.

### 6.5. Nhiệm vụ chính với Video Analyzer

Người phụ trách cần làm:

1. Đọc `media_metadata.json`.
2. Lấy danh sách video có `status = ready` hoặc `warning`.
3. Chạy scene detection hoặc shot detection.
4. Tạo clip candidate.
5. Loại hoặc đánh dấu clip quá ngắn, lỗi, chất lượng quá thấp.
6. Chia nhỏ clip quá dài nếu cần.
7. Trích nhiều keyframe cho mỗi clip.
8. Tính quality score cơ bản.
9. Ghi metadata của từng clip (MVP: **`status`** và **`source_path`** trên mọi clip).
10. Xuất `clip_metadata.json`.

### 6.6. Output cần bàn giao

Output Stage 1:

```text
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
data/normalized/video_*.mp4
data/normalized/voiceover.wav
```

Output Stage 3:

```text
data/intermediate/clip_metadata.json
data/intermediate/video_analysis_log.json
data/keyframes/*.jpg
```

### 6.7. Module sử dụng output

`media_metadata.json` được dùng bởi:

```text
audio_analyzer/
video_analyzer/
timeline_planner/
review_ui/
renderer/
integration/
```

`clip_metadata.json` được dùng bởi:

```text
embedding_indexer/
matching_engine/
timeline_planner/
review_ui/
renderer/
evaluation/
```

### 6.8. Tiêu chí hoàn thành

Module đạt yêu cầu khi:

* Tạo được `media_metadata.json` đúng schema.
* Tạo được file normalized.
* Tạo được `clip_metadata.json` đúng schema.
* Mỗi clip có `clip_id`, `video_id`, `start`, `end`, `duration`, `keyframes`, `quality_score`.
* Keyframe path tồn tại.
* Clip không vượt quá duration video nguồn.
* Output có thể đưa cho Embedding Indexer và Matching Engine chạy tiếp.

## 7. Người 4 — Embedding / Matching / Retrieval

### 7.1. Vai trò

Người 4 phụ trách biến audio segment và clip/keyframe thành đặc trưng có thể so sánh, sau đó tìm top-k clip phù hợp cho từng audio segment.

Đây là phần quyết định hệ thống chọn hình có liên quan đến lời thuyết minh hay không.

### 7.2. Module phụ trách

```text
embedding_indexer/
matching_engine/
```

### 7.3. Input cần đọc

Embedding Indexer đọc:

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/keyframes/*.jpg
```

Matching Engine đọc:

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/embeddings/
data/intermediate/index/
```

### 7.4. Nhiệm vụ chính với Embedding Indexer

Người phụ trách cần làm:

1. Đọc `audio_segments.json`.
2. Đọc `clip_metadata.json`.
3. Tạo text embedding cho `query` hoặc `translated_query`.
4. Tạo image embedding cho keyframe.
5. Tổng hợp embedding keyframe để đại diện cho clip nếu cần.
6. Lưu embedding/index.
7. Xuất `embedding_metadata.json`.

### 7.5. Nhiệm vụ chính với Matching Engine

Người phụ trách cần làm:

1. Đọc audio segment.
2. Đọc clip metadata.
3. Đọc embedding/index.
4. Tính semantic score giữa audio segment và clip.
5. Kết hợp thêm quality score nếu có.
6. Tính duration fit score nếu có.
7. Hạn chế chọn clip bị lặp quá gần.
8. Trả về top-k clip cho từng segment.
9. Chọn clip mặc định.
10. Gán confidence.
11. Xuất `matching_candidates.json`.

### 7.6. Output cần bàn giao

Output Stage 4:

```text
data/intermediate/embedding_metadata.json
data/intermediate/embeddings/
data/intermediate/index/
data/intermediate/embedding_indexing_log.json
```

Output Stage 5:

```text
data/intermediate/matching_candidates.json
data/intermediate/matching_engine_log.json
```

### 7.7. Module sử dụng output

Output của người 4 được dùng bởi:

```text
timeline_planner/
review_ui/
evaluation/
```

### 7.8. Tiêu chí hoàn thành

Module đạt yêu cầu khi:

* Đọc được `audio_segments.json`.
* Đọc được `clip_metadata.json`.
* Tạo được embedding hoặc đặc trưng so khớp.
* Với mỗi audio segment, trả về được top-k clip.
* Mỗi candidate có `rank`, `clip_id`, `final_score`.
* `selected_clip_id` nằm trong danh sách candidates hoặc là `null`.
* `confidence` thuộc `high`, `medium`, `low`.
* Output đúng schema `matching_candidates.json`.
* Timeline Planner và Review UI có thể đọc output để chạy tiếp.

## 8. Người 5 — Review UI / Renderer

### 8.1. Vai trò

Người 5 phụ trách phần người dùng nhìn thấy và phần xuất video cuối.

Vai trò này gồm hai phần:

* Review UI: cho người dùng xem timeline, xem clip đề xuất và đổi clip nếu cần.
* Renderer: đọc timeline và xuất video cuối.

### 8.2. Module phụ trách

```text
review_ui/
renderer/
```

### 8.3. Input cần đọc cho Review UI

```text
data/intermediate/timeline.json
data/intermediate/matching_candidates.json
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/media_metadata.json
data/normalized/*.wav
```

Voice-over preview: `media_metadata.audio.normalized_path`. Video preview: path từ `clip_metadata` hoặc `timeline.items[].visual_items[].source_path`.

### 8.4. Input cần đọc cho Renderer

```text
data/intermediate/timeline.json
data/intermediate/media_metadata.json
data/intermediate/clip_metadata.json
data/intermediate/render_config.json
```

Voice-over: CLI → `render_config.audio.voiceover_path` → `media_metadata.audio.normalized_path`. Video: `timeline.items[].visual_items[].source_path`.

### 8.5. Nhiệm vụ chính với Review UI

Người phụ trách cần làm:

1. Hiển thị danh sách audio segment.
2. Hiển thị transcript từng segment.
3. Hiển thị clip đang được chọn.
4. Hiển thị score và confidence.
5. Highlight đoạn cần review.
6. Hiển thị top-k clip thay thế.
7. Cho phép người dùng chọn clip khác.
8. Cho phép chỉnh một số tham số cơ bản nếu có.
9. Cập nhật `timeline.json` (ghi đè cùng path, cập nhật `updated_at`).
10. Lưu lại timeline đã chỉnh.
11. (Tùy chọn) Ghi `review_ui_log.json` để debug.

### 8.6. Nhiệm vụ chính với Renderer

Người phụ trách cần làm:

1. Đọc `timeline.json`.
2. Validate timeline trước khi render.
3. Cắt clip theo `clip_start`, `clip_end`.
4. Đặt clip vào timeline theo `timeline_start`, `timeline_end`.
5. Chỉnh speed nếu cần.
6. Scale/crop video theo render settings.
7. Thêm transition cơ bản.
8. Ghép voice-over làm audio chính.
9. Tắt hoặc giảm audio gốc nếu cấu hình yêu cầu.
10. Xuất `final_video.mp4`.
11. Xuất `render_log.json`.

### 8.7. Output cần bàn giao

Output Review UI:

```text
data/intermediate/timeline.json
```

Nếu cần backup so sánh, có thể xuất `data/intermediate/timeline_updated.json`; integration truyền path timeline cho Renderer.

Output Renderer:

```text
data/final/final_video.mp4
data/intermediate/render_log.json
```

### 8.8. Module sử dụng output

Output của Review UI được dùng bởi:

```text
renderer/
evaluation/
```

Output của Renderer được dùng cho:

```text
demo
report
evaluation
```

### 8.9. Tiêu chí hoàn thành

Review UI đạt yêu cầu khi:

* Đọc được timeline mẫu.
* Hiển thị được segment, transcript, clip hiện tại.
* Hiển thị được top-k candidate.
* Đổi clip và cập nhật timeline được.
* Không làm hỏng schema `timeline.json`.

Renderer đạt yêu cầu khi:

* Đọc được `timeline.json`.
* Cắt và ghép được clip.
* Ghép được voice-over.
* Xuất được `final_video.mp4`.
* Có log render để debug.
* Video cuối chạy được bằng trình phát phổ biến.

## 9. Timeline Planner — Trách nhiệm phối hợp

Timeline Planner là module quan trọng vì nằm giữa Matching Engine, Review UI và Renderer.

Tùy năng lực nhóm, Timeline Planner có thể do:

* Leader phụ trách chính.
* Người làm Matching hỗ trợ logic chọn clip.
* Người làm Renderer hỗ trợ kiểm tra timeline có render được không.
* Người làm UI hỗ trợ xem timeline có dễ hiển thị không.

### 9.1. Input

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/media_metadata.json
```

### 9.2. Output

```text
data/intermediate/timeline.json
data/intermediate/timeline_planning_log.json
```

`timeline_planning_log.json` — log debug, optional.

### 9.3. Nhiệm vụ

Timeline Planner cần:

1. Chọn clip mặc định cho mỗi audio segment.
2. Tạo `visual_items`.
3. Xử lý clip dài hơn audio segment.
4. Xử lý clip ngắn hơn audio segment.
5. Cho phép một audio segment có nhiều visual items.
6. Thêm speed mặc định.
7. Thêm transition mặc định.
8. Gán confidence, score, candidates_ref.
9. Copy `text` chính xác từ `audio_segments.json`.
10. Đảm bảo timeline render được.

### 9.4. Lý do cần phối hợp

Nếu Timeline Planner chỉ dựa vào Matching, timeline có thể không render tốt.

Nếu chỉ dựa vào Renderer, timeline có thể render được nhưng không khớp nghĩa.

Vì vậy, module này cần phối hợp giữa:

```text
Matching Engine
Timeline Planner
Review UI
Renderer
Leader
```

## 10. Ma trận phụ thuộc giữa các thành viên

| Người                 | Phụ thuộc đầu vào từ                       | Cung cấp output cho                         |
| --------------------- | ------------------------------------------ | ------------------------------------------- |
| Người 1 - Leader      | Tất cả module                              | Tất cả module                               |
| Người 2 - Audio       | Người 3 - Input Processor                  | Người 4, Timeline Planner, Người 5          |
| Người 3 - Video       | Dữ liệu raw                                | Người 2, Người 4, Timeline Planner, Người 5 |
| Người 4 - Embedding/Matching | Người 2, Người 3                           | Timeline Planner (Leader), Người 5                   |
| Người 5 - UI/Renderer | Leader, Người 3, Người 4, Timeline Planner | Demo, Evaluation, Report                    |

## 11. Quy tắc phối hợp

### 11.1. Không tự ý đổi schema

Không thành viên nào được tự ý đổi:

* Tên file JSON.
* Tên field.
* Kiểu dữ liệu.
* Quy ước ID.
* Quy ước path.
* Cấu trúc `timeline.json`.

Nếu cần đổi, phải trao đổi với leader và cập nhật tài liệu trước.

### 11.2. Output phải kiểm tra được

Mỗi module cần xuất file trung gian rõ ràng.

Không chỉ in kết quả ra terminal.

Ví dụ:

```text
audio_analyzer -> audio_segments.json
video_analyzer -> clip_metadata.json
matching_engine -> matching_candidates.json
timeline_planner -> timeline.json
renderer -> final_video.mp4 + render_log.json
```

### 11.3. Mỗi module cần README riêng

Mỗi thư mục module nên có `README.md` mô tả:

* Module làm gì.
* Input là gì.
* Output là gì.
* Cách chạy.
* Cách test.
* Thư viện cần cài.
* Giới hạn hiện tại.

### 11.4. Không sửa module của người khác nếu chưa trao đổi

Để tránh conflict khi merge code:

* Mỗi người chủ yếu làm trong module mình phụ trách.
* Nếu cần sửa module khác, phải báo trước.
* Nếu thay đổi ảnh hưởng Data Contract, phải báo leader.

### 11.5. Dùng sample data để làm song song

Khi module trước chưa xong, thành viên có thể dùng sample data trong:

```text
docs/samples/
```

Ví dụ:

* UI dùng `timeline_sample.json`.
* Renderer dùng `timeline_sample.json`, `media_metadata_sample.json`, `render_config_sample.json` và media source mẫu.
* Matching dùng `audio_segments_sample.json`, `clip_metadata_sample.json`, `embedding_metadata_sample.json` và `embedding_index_sample/`.

## 12. Mốc bàn giao đề xuất

### Mốc 1 — Chốt tài liệu nền

Mục tiêu:

* Chốt Project Scope.
* Chốt System Architecture.
* Chốt Data Contract.
* Chốt Stage Specification.
* Chốt Team Assignment.
* Chốt Integration Plan.

Output:

```text
docs/details/*.md
docs/schemas/*.md
docs/samples/*.json
```

### Mốc 2 — Module chạy độc lập

Mục tiêu:

Mỗi thành viên làm module của mình chạy được với dữ liệu mẫu hoặc dữ liệu nhỏ.

Output:

```text
media_metadata.json
input_processing_log.json
audio_segments.json
audio_analysis_log.json
clip_metadata.json
video_analysis_log.json
embedding_metadata.json
embedding_indexing_log.json
matching_candidates.json
matching_engine_log.json
timeline.json
render_log.json
final_video.mp4 thử nghiệm
```

### Mốc 3 — Tích hợp pipeline cơ bản

Mục tiêu:

Ghép các module thành pipeline bán tự động.

Pipeline tối thiểu:

```text
Input video/audio
→ media_metadata.json
→ audio_segments.json
→ clip_metadata.json
→ embedding_metadata.json + embedding/index files
→ matching_candidates.json
→ timeline.json
→ final_video.mp4 + render_log.json
```

### Mốc 4 — UI review

Mục tiêu:

* UI đọc được timeline.
* UI hiển thị top-k candidate.
* UI đổi clip được.
* UI lưu timeline đã chỉnh.

### Mốc 5 — Demo cuối

Mục tiêu:

* Chạy được demo end-to-end.
* Có video final.
* Có các file JSON trung gian.
* Có thể giải thích pipeline trong báo cáo.
* Có thể chỉ ra hạn chế và hướng phát triển.

## 13. Tiêu chí hoàn thành chung của nhóm

Dự án được xem là hoàn thành ở mức MVP khi:

1. Nhận được video nguồn và audio thuyết minh.
2. Tạo được metadata đầu vào.
3. Tạo được transcript có timestamp.
4. Tạo được clip candidate từ video nguồn.
5. Tạo được embedding metadata và embedding/index files.
6. Tạo được top-k clip cho từng audio segment.
7. Tạo được timeline JSON.
8. UI đọc và chỉnh được timeline.
9. Renderer xuất được video cuối và `render_log.json`.
10. Các file JSON trung gian đúng Data Contract.
11. Có thể chạy demo end-to-end.
12. Có tài liệu giải thích rõ vai trò từng module.
13. Có nhận xét về hạn chế và hướng phát triển.

## 14. Ghi chú cho leader

Leader nên ưu tiên kiểm tra các điểm sau trong quá trình nhóm làm việc:

* Mọi người có đọc đúng stage spec chưa.
* Output từng module có đúng schema không.
* ID giữa các file có khớp không.
* Path có dùng relative path không.
* Timeline có render được không.
* UI có làm hỏng timeline không.
* Có module nào đang bị quá tải không.
* Có phần nào đang làm ngoài phạm vi MVP không.
* Có vấn đề tích hợp nào cần xử lý sớm không.

Nếu một module chưa hoàn thiện, leader nên yêu cầu module đó xuất bản tối giản nhưng đúng schema trước. Chất lượng thuật toán có thể cải thiện sau, nhưng Data Contract cần ổn định sớm.

## 15. Kết luận

Phân công nhóm cần bám theo kiến trúc module hóa của dự án.

Mỗi thành viên tập trung vào module của mình, nhưng phải hiểu module đó nằm ở đâu trong pipeline và output của mình sẽ được ai sử dụng.

Nguyên tắc quan trọng nhất:

**Làm độc lập trong module riêng, nhưng giao tiếp bằng Data Contract chung.**
