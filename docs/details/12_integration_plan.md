# 12. Integration Plan

## 1. Mục tiêu của tài liệu

Tài liệu này mô tả kế hoạch tích hợp các module trong dự án **Audio-Guided Video Montage** thành một pipeline hoàn chỉnh.

Mục tiêu chính:

* Xác định thứ tự tích hợp các module.
* Quy định cách kiểm tra output của từng module trước khi ghép.
* Giảm lỗi khi các thành viên merge code lại với nhau.
* Đảm bảo các file JSON trung gian đúng Data Contract.
* Giúp leader dễ debug khi pipeline bị lỗi.
* Đảm bảo dự án có thể chạy demo end-to-end.

Nguyên tắc quan trọng:

> Không chờ tất cả module hoàn hảo mới tích hợp. Cần tích hợp sớm bằng sample data, sau đó thay dần bằng output thật của từng module.

## 2. Phạm vi của Integration Plan

Integration Plan áp dụng cho toàn bộ pipeline:

```text
Input video/audio
→ Input Processor
→ Audio Analyzer + Video Analyzer
→ Embedding Indexer
→ Matching Engine
→ Timeline Planner
→ Review UI
→ Renderer
→ Final video
```

Tài liệu này tập trung vào:

* Cách nối output của module trước với input của module sau.
* Cách kiểm tra schema.
* Cách xử lý lỗi tích hợp.
* Cách chạy demo từng lớp.
* Cách xác định module nào đang gây lỗi.

Tài liệu này không đi sâu vào thuật toán nội bộ của từng module. Chi tiết thuật toán nằm trong stage specification tương ứng.

## 3. Nguyên tắc tích hợp chung

### 3.1. Tích hợp qua file trung gian

Các module giao tiếp với nhau bằng file JSON trung gian.

Các file chính:

```text
media_metadata.json
audio_segments.json
clip_metadata.json
embedding_metadata.json
embedding/index files
matching_candidates.json
timeline.json
render_config.json
render_log.json
evaluation_report.json
```

Module sau không nên phụ thuộc vào implementation nội bộ của module trước.

Ví dụ:

```text
Audio Analyzer không cần biết Input Processor normalize audio bằng cách nào.
Audio Analyzer chỉ cần media_metadata.json có audio.normalized_path hợp lệ.
```

### 3.2. Data Contract là nguồn tham chiếu chính

Khi có mâu thuẫn giữa code và tài liệu, cần kiểm tra lại Data Contract.

Các module phải tuân thủ:

```text
docs/details/02_data_contract.md
docs/schemas/
docs/samples/
```

Không module nào được tự ý đổi schema để “dễ code hơn”.

### 3.3. Tích hợp theo từng lớp

Không tích hợp toàn bộ hệ thống một lần.

Nên tích hợp theo các lớp:

```text
Lớp 1: Sample data
Lớp 2: Module thật chạy độc lập
Lớp 3: Pipeline không UI
Lớp 4: UI review
Lớp 5: Render final video
Lớp 6: Demo end-to-end
```

### 3.4. Ưu tiên pipeline chạy được trước

Trong MVP, ưu tiên:

* Output đúng schema.
* Pipeline chạy được từ đầu đến cuối.
* Có final video.
* Có log để debug.

Chất lượng thuật toán có thể cải thiện sau.

Ví dụ:

* Matching ban đầu có thể đơn giản.
* Timeline Planner ban đầu có thể chọn clip rank 1.
* UI ban đầu chỉ cần đổi clip trong top-k.
* Renderer ban đầu chỉ cần cut cơ bản, transition có thể thêm sau.

## 4. Các file trung gian trong pipeline

## 4.1. `media_metadata.json`

Tạo bởi:

```text
input_processor/
```

Dùng bởi:

```text
audio_analyzer/
video_analyzer/
timeline_planner/
renderer/
integration/
```

Vai trò:

* Xác định video/audio đầu vào.
* Cung cấp đường dẫn normalized media.
* Cung cấp duration, fps, resolution, sample rate.

Điều kiện tích hợp:

* File parse được.
* Có ít nhất một video usable.
* Có audio usable.
* Path normalized tồn tại.
* Duration hợp lệ.

## 4.2. `audio_segments.json`

Tạo bởi:

```text
audio_analyzer/
```

Dùng bởi:

```text
embedding_indexer/
matching_engine/
timeline_planner/
review_ui/
evaluation/
```

Vai trò:

* Chứa transcript.
* Chứa timestamp.
* Chứa query phục vụ matching.
* Là cơ sở chia timeline theo audio.

Điều kiện tích hợp:

* Có ít nhất một segment.
* Segment không overlap.
* `segment_id` duy nhất.
* `query` không rỗng.
* Timestamp hợp lệ.

## 4.3. `clip_metadata.json`

Tạo bởi:

```text
video_analyzer/
```

Dùng bởi:

```text
embedding_indexer/
matching_engine/
timeline_planner/
review_ui/
renderer/
evaluation/
```

Vai trò:

* Chứa danh sách clip candidate.
* Chứa keyframe.
* Chứa quality score.
* Cho biết mỗi clip nằm trong video nào, từ giây nào đến giây nào.

Điều kiện tích hợp:

* Có ít nhất một clip usable.
* `clip_id` duy nhất.
* `video_id` tồn tại trong `media_metadata.json`.
* `start`, `end`, `duration` hợp lệ.
* Keyframe path tồn tại nếu dùng embedding hình ảnh.

## 4.4. `embedding_metadata.json`

Tạo bởi:

```text
embedding_indexer/
```

Dùng bởi:

```text
matching_engine/
```

Vai trò:

* Lưu mapping giữa segment/clip/keyframe và embedding.
* Cho Matching Engine biết embedding nào thuộc đối tượng nào.

Điều kiện tích hợp:

* Text embedding map đúng với `segment_id`.
* Visual embedding map đúng với `clip_id` hoặc `keyframe_id`.
* Index path tồn tại nếu dùng FAISS hoặc index riêng.
* Model/dimension được ghi rõ.

## 4.5. `matching_candidates.json`

Tạo bởi:

```text
matching_engine/
```

Dùng bởi:

```text
timeline_planner/
review_ui/
evaluation/
```

Vai trò:

* Chứa top-k clip cho từng audio segment.
* Chứa score và confidence.
* Chứa clip mặc định được chọn.

Điều kiện tích hợp:

* Mỗi `audio_segment_id` tồn tại trong `audio_segments.json`.
* Mỗi `clip_id` tồn tại trong `clip_metadata.json`.
* `selected_clip_id` nằm trong candidates hoặc là `null`.
* `rank` hợp lệ.
* `final_score` nằm trong `[0.0, 1.0]`.

## 4.6. `timeline.json`

Tạo bởi:

```text
timeline_planner/
```

Có thể được cập nhật bởi:

```text
review_ui/
```

Dùng bởi:

```text
renderer/
evaluation/
```

Vai trò:

* Mô tả bản dựng video cuối.
* Là file trung tâm giữa Timeline Planner, UI và Renderer.

Điều kiện tích hợp:

* Mỗi `segment_id` tồn tại trong `audio_segments.json`.
* Mỗi visual item có `clip_id` tồn tại trong `clip_metadata.json`.
* `source_path` tồn tại.
* `clip_start`, `clip_end` nằm trong video nguồn.
* `timeline_start`, `timeline_end` hợp lệ.
* Tổng timeline gần khớp duration audio.

## 4.7. `render_config.json`

Tạo bởi:

```text
user/system/integration/
```

Dùng bởi:

```text
renderer/
```

Vai trò:

* Lưu cấu hình render nếu không dùng trực tiếp `timeline.render_settings`.
* Cung cấp output path, resolution, fps, format, audio mix và crop/transition mặc định.

Điều kiện tích hợp:

* File parse được nếu pipeline truyền `render_config.json` cho Renderer.
* `output.path`, `width`, `height`, `fps` và `format` hợp lệ.
* `audio.voiceover_path` khớp với media đã chuẩn hóa hoặc được override có chủ đích.
* `video.crop_mode` và `video.default_transition` thuộc allowed values trong Data Contract.

## 4.8. `render_log.json`

Tạo bởi:

```text
renderer/
```

Dùng bởi:

```text
integration/
evaluation/
report/
```

Vai trò:

* Ghi lại kết quả render.
* Hỗ trợ debug nếu render lỗi.

Điều kiện tích hợp:

* Có `status`.
* Có `output_path`.
* Có `warnings` và `errors`.
* Nếu render thành công, `output_path` tồn tại.

## 5. Chiến lược tích hợp theo lớp

## 5.1. Lớp 1 — Tích hợp bằng sample data

### Mục tiêu

Tạo bộ dữ liệu mẫu đúng schema để các module phía sau có thể làm trước mà không cần chờ module phía trước hoàn thiện.

### File cần có

```text
docs/samples/media_metadata_sample.json
docs/samples/audio_segments_sample.json
docs/samples/clip_metadata_sample.json
docs/samples/embedding_metadata_sample.json
docs/samples/embedding_index_sample/
docs/samples/matching_candidates_sample.json
docs/samples/timeline_sample.json
docs/samples/render_config_sample.json
docs/samples/render_log_sample.json
```

### Việc cần làm

Leader chuẩn bị sample data:

* Đủ nhỏ để dễ đọc.
* Đúng schema.
* Có ID map với nhau.
* Có path giả hoặc path thật phục vụ test.
* Có ít nhất 2-3 audio segments.
* Có ít nhất 4-6 clip candidates.
* Có ít nhất một segment confidence thấp.
* Có ít nhất một segment dùng nhiều visual items nếu muốn test timeline linh hoạt.

### Module có thể test bằng sample data

Review UI test bằng:

```text
timeline_sample.json
matching_candidates_sample.json
clip_metadata_sample.json
audio_segments_sample.json
media_metadata_sample.json
```

Renderer test bằng:

```text
timeline_sample.json
media_metadata_sample.json
render_config_sample.json
media source sample
```

Timeline Planner test bằng:

```text
audio_segments_sample.json
media_metadata_sample.json
clip_metadata_sample.json
matching_candidates_sample.json
```

Matching Engine test bằng:

```text
audio_segments_sample.json
clip_metadata_sample.json
embedding_metadata_sample.json
embedding_index_sample/
```

### Tiêu chí hoàn thành lớp 1

Lớp này hoàn thành khi:

* Sample JSON parse được.
* ID giữa các sample khớp nhau.
* UI đọc được sample timeline.
* Renderer có thể thử đọc sample timeline.
* Các thành viên hiểu output module mình cần tạo.

## 5.2. Lớp 2 — Module thật chạy độc lập

### Mục tiêu

Mỗi module chạy được riêng và xuất output đúng schema.

Không yêu cầu pipeline chạy end-to-end ngay.

### Yêu cầu với từng module

Input Processor cần tạo:

```text
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
```

Audio Analyzer cần tạo:

```text
data/intermediate/audio_segments.json
data/intermediate/audio_analysis_log.json
```

Video Analyzer cần tạo:

```text
data/intermediate/clip_metadata.json
data/intermediate/video_analysis_log.json
data/keyframes/*.jpg
```

Embedding Indexer cần tạo:

```text
data/intermediate/embedding_metadata.json
data/intermediate/embeddings/
data/intermediate/index/
data/intermediate/embedding_indexing_log.json
```

Matching Engine cần tạo:

```text
data/intermediate/matching_candidates.json
data/intermediate/matching_engine_log.json
```

Timeline Planner cần tạo:

```text
data/intermediate/timeline.json
```

Renderer cần tạo:

```text
data/final/final_video.mp4
data/intermediate/render_log.json
```

### Tiêu chí hoàn thành lớp 2

Lớp này hoàn thành khi:

* Mỗi module chạy được bằng CLI hoặc script riêng.
* Mỗi module có README hướng dẫn chạy.
* Output chính tồn tại.
* Output chính đúng schema.
* Module có test case tối thiểu.
* Có log hoặc message lỗi dễ hiểu khi chạy thất bại.

## 5.3. Lớp 3 — Pipeline không UI

### Mục tiêu

Ghép các module xử lý tự động thành pipeline cơ bản, chưa cần UI.

Pipeline:

```text
Input Processor
→ Audio Analyzer + Video Analyzer
→ Embedding Indexer
→ Matching Engine
→ Timeline Planner
→ Renderer
```

### Input

```text
data/raw/video_*.mp4
data/raw/voiceover.*
```

### Output mong đợi

```text
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
data/intermediate/audio_segments.json
data/intermediate/audio_analysis_log.json
data/intermediate/clip_metadata.json
data/intermediate/video_analysis_log.json
data/intermediate/embedding_metadata.json
data/intermediate/embedding_indexing_log.json
data/intermediate/matching_candidates.json
data/intermediate/matching_engine_log.json
data/intermediate/timeline.json
data/intermediate/render_log.json
data/final/final_video.mp4
```

Log debug (optional): `timeline_planning_log.json`, `review_ui_log.json`.

`render_config.json` optional khi tách cấu hình render.

### Tiêu chí hoàn thành lớp 3

Lớp này hoàn thành khi:

* Chạy được pipeline không UI.
* Tạo được toàn bộ file trung gian chính.
* Renderer xuất được video cuối.
* Video cuối có thời lượng gần bằng audio.
* Có thể chỉ ra mỗi đoạn audio dùng clip nào thông qua `timeline.json`.

## 5.4. Lớp 4 — Tích hợp Review UI

### Mục tiêu

Kết nối UI với timeline và candidate data.

UI cần đọc:

```text
timeline.json
matching_candidates.json
audio_segments.json
clip_metadata.json
media_metadata.json
```

UI cần làm được:

* Hiển thị danh sách audio segment.
* Hiển thị transcript.
* Hiển thị clip hiện tại.
* Hiển thị top-k candidate.
* Highlight segment cần review.
* Cho phép đổi clip.
* Lưu lại timeline đã chỉnh.

### Output

```text
data/intermediate/timeline.json
```

Nếu cần backup, có thể xuất `data/intermediate/timeline_updated.json`; integration truyền path timeline cho Renderer.

### Tiêu chí hoàn thành lớp 4

Lớp này hoàn thành khi:

* UI đọc được timeline thật.
* UI hiển thị đúng segment và candidate.
* Người dùng đổi clip được.
* Timeline sau khi đổi vẫn đúng schema.
* Renderer đọc được timeline sau khi UI chỉnh.

## 5.5. Lớp 5 — Render sau chỉnh sửa

### Mục tiêu

Đảm bảo renderer dùng timeline đã chỉnh từ UI để xuất video mới.

Flow:

```text
Review UI
→ timeline.json (cùng path, nội dung đã cập nhật)
→ Renderer
→ final_video.mp4
```

### Yêu cầu

Renderer không được tự chọn lại clip.

Renderer chỉ làm theo timeline.

Nếu UI chọn clip khác, final video phải dùng clip mới.

### Tiêu chí hoàn thành lớp 5

Lớp này hoàn thành khi:

* Đổi clip trên UI.
* Lưu timeline.
* Render lại.
* Video cuối thay đổi đúng theo timeline mới.
* Không cần chạy lại ASR, Video Analyzer, Embedding hoặc Matching.

## 5.6. Lớp 6 — Demo end-to-end

### Mục tiêu

Chạy toàn bộ hệ thống như một sản phẩm hoàn chỉnh ở mức MVP.

Flow demo:

```text
1. Cung cấp video/audio đầu vào.
2. Chạy pipeline tạo file trung gian.
3. Mở UI review.
4. Đổi một clip trong top-k.
5. Render video cuối.
6. Mở final_video.mp4.
7. Giải thích timeline và output.
```

### Tiêu chí hoàn thành lớp 6

Demo đạt yêu cầu khi:

* Pipeline chạy được từ đầu đến cuối.
* Có video final.
* Có timeline JSON.
* Có matching candidates.
* UI chỉnh được ít nhất một segment.
* Renderer xuất lại video sau chỉnh sửa.
* Nhóm giải thích được vai trò từng module.

## 6. Thứ tự tích hợp đề xuất

## 6.1. Giai đoạn A — Chuẩn bị nền

Người phụ trách: Leader

Việc cần làm:

1. Chốt Data Contract.
2. Tạo sample JSON.
3. Tạo cấu trúc thư mục.
4. Tạo README cho repo.
5. Tạo README cho docs.
6. Tạo skeleton README cho từng module.
7. Tạo script validate JSON nếu có thể.

Output:

```text
docs/
docs/samples/
integration/
shared/
scripts/
```

## 6.2. Giai đoạn B — Tích hợp Stage 1 và Stage 2

Ghép:

```text
Input Processor
→ Audio Analyzer
```

Mục tiêu:

* Input Processor tạo `media_metadata.json`.
* Audio Analyzer đọc `audio.normalized_path`.
* Audio Analyzer tạo `audio_segments.json`.

Kiểm tra:

* Audio path đúng.
* Audio duration khớp.
* `audio_id` khớp.
* `project_id` khớp.

Lỗi thường gặp:

* Path audio ghi absolute path.
* Audio Analyzer hard-code path.
* Stage 1 output sai schema.
* Stage 2 không xử lý `status = warning`.

## 6.3. Giai đoạn C — Tích hợp Stage 1 và Stage 3

Ghép:

```text
Input Processor
→ Video Analyzer
```

Mục tiêu:

* Video Analyzer đọc `videos[*].normalized_path`.
* Video Analyzer tạo `clip_metadata.json`.
* `clip_metadata.video_id` khớp với `media_metadata.videos.video_id`.

Kiểm tra:

* Mỗi `video_id` tồn tại.
* Clip không vượt quá duration video.
* Keyframe path tồn tại.
* Clip quá ngắn được loại hoặc đánh dấu.

Lỗi thường gặp:

* Video Analyzer tự sinh `video_id` khác Stage 1.
* Clip timestamp tính theo file raw thay vì file normalized.
* Keyframe path sai.
* Không xử lý video `warning`.

## 6.4. Giai đoạn D — Tích hợp Audio, Video và Embedding

Ghép:

```text
audio_segments.json
clip_metadata.json
keyframes/
→ Embedding Indexer
```

Mục tiêu:

* Tạo text embedding cho từng segment.
* Tạo visual embedding cho keyframe/clip.
* Tạo `embedding_metadata.json`.

Kiểm tra:

* Mỗi `segment_id` có text embedding.
* Mỗi clip hoặc keyframe usable có visual embedding.
* Embedding dimension thống nhất.
* Index path tồn tại nếu dùng index.

Lỗi thường gặp:

* Embedding dùng `text` thay vì `query` không theo thống nhất.
* Không xử lý `translated_query = null`.
* Một số keyframe path không tồn tại.
* Model text/image không cùng không gian embedding.

## 6.5. Giai đoạn E — Tích hợp Matching Engine

Ghép:

```text
audio_segments.json
clip_metadata.json
embedding_metadata.json
embedding/index files
→ matching_candidates.json
```

Mục tiêu:

* Mỗi audio segment có top-k clip.
* Có score và confidence.
* Có selected clip mặc định.

Kiểm tra:

* Mỗi `audio_segment_id` tồn tại.
* Mỗi candidate `clip_id` tồn tại.
* `rank` đúng thứ tự.
* `selected_clip_id` hợp lệ.
* `final_score` trong `[0.0, 1.0]`.

Lỗi thường gặp:

* Matching trả clip_id không có trong clip metadata.
* Thiếu candidate cho segment.
* Score không chuẩn hóa.
* Không có confidence.
* Top-k ít hơn kỳ vọng nhưng không ghi lý do.

## 6.6. Giai đoạn F — Tích hợp Timeline Planner

Ghép:

```text
audio_segments.json
clip_metadata.json
matching_candidates.json
media_metadata.json
→ timeline.json
```

Mục tiêu:

* Tạo timeline render được.
* Mỗi segment có visual item.
* Timeline duration khớp audio.
* Có candidates_ref để UI tra top-k.

Kiểm tra:

* `segment_id` khớp.
* `clip_id` khớp.
* `source_path` tồn tại.
* `clip_start`, `clip_end` hợp lệ.
* `timeline_start`, `timeline_end` hợp lệ.
* `speed` trong giới hạn.
* `candidates_ref` khớp với candidate set.

Lỗi thường gặp:

* Timeline dùng clip_id không tồn tại.
* Clip quá ngắn nhưng không xử lý.
* Timeline có gap lớn không chủ đích.
* Timeline overlap sai.
* Không map được candidate set cho UI.

## 6.7. Giai đoạn G — Tích hợp Renderer

Ghép:

```text
timeline.json
media_metadata.json
normalized media
→ final_video.mp4
```

Mục tiêu:

* Render được video cuối từ timeline.

Kiểm tra:

* Source path tồn tại.
* Clip start/end hợp lệ.
* Output video mở được.
* Audio voice-over được ghép vào.
* Duration final gần duration audio.

Lỗi thường gặp:

* Path video sai.
* Clip end vượt duration.
* Codec output lỗi.
* Audio final không khớp.
* Speed làm lệch duration.
* Transition làm timeline dài/ngắn hơn dự kiến.

## 6.8. Giai đoạn H — Tích hợp UI

Ghép:

```text
timeline.json
matching_candidates.json
clip_metadata.json
audio_segments.json
media files
→ Review UI
→ timeline.json (cùng path, nội dung đã cập nhật)
```

Mục tiêu:

* UI hiển thị timeline.
* UI cho đổi clip.
* UI lưu timeline mới.

Kiểm tra:

* UI không làm mất field quan trọng.
* UI không đổi schema.
* UI giữ `candidates_ref`.
* UI set `user_edited = true` nếu người dùng đổi clip.
* Timeline sau chỉnh vẫn render được.

Lỗi thường gặp:

* UI chỉ lưu một phần timeline.
* UI đổi clip nhưng không cập nhật `source_path`.
* UI làm mất `timeline_start/timeline_end`.
* UI không validate clip mới.
* UI làm hỏng JSON format.

## 7. Quy trình kiểm tra trước khi merge module

Trước khi merge code của một module vào nhánh chính, cần kiểm tra:

```text
[ ] Module có README riêng
[ ] Module chạy được bằng lệnh rõ ràng
[ ] Module đọc input đúng vị trí
[ ] Module xuất output đúng tên file
[ ] Output parse được JSON
[ ] Output đúng Data Contract
[ ] ID khớp với các file liên quan
[ ] Path dùng relative path
[ ] Có test với dữ liệu nhỏ
[ ] Có ghi chú limitation nếu module chưa hoàn thiện
```

Nếu module chưa đạt đủ, không nên tích hợp vào pipeline chính. Có thể giữ ở branch riêng hoặc đánh dấu experimental.

## 8. Quy trình validate dữ liệu

## 8.1. Validate thủ công

Leader có thể kiểm tra bằng cách mở file JSON và đối chiếu:

* Top-level fields.
* Required fields.
* ID mapping.
* Path.
* Timestamp.
* Score.
* Confidence.

## 8.2. Validate bằng script

Nên có script:

```text
scripts/validate_json.py
```

Script này có thể kiểm tra:

```text
media_metadata.json
audio_segments.json
clip_metadata.json
embedding_metadata.json
matching_candidates.json
timeline.json
render_config.json
render_log.json
```

Các mức kiểm tra:

### Mức 1 — JSON parse

Kiểm tra file có parse được không.

### Mức 2 — Required fields

Kiểm tra field bắt buộc.

### Mức 3 — Type check

Kiểm tra kiểu dữ liệu.

### Mức 4 — Value range

Kiểm tra:

* Time >= 0.
* Score trong `[0.0, 1.0]`.
* Confidence hợp lệ.
* Speed hợp lệ.

### Mức 5 — Cross-file mapping

Kiểm tra:

* `segment_id` khớp.
* `clip_id` khớp.
* `video_id` khớp.
* `candidate_set_id` khớp.
* Path tồn tại.

## 8.3. Thứ tự validate đề xuất

```text
1. media_metadata.json
2. audio_segments.json
3. clip_metadata.json
4. embedding_metadata.json
5. matching_candidates.json
6. timeline.json
7. render_config.json nếu dùng file cấu hình riêng
8. render_log.json
```

Không validate timeline trước khi validate các file mà timeline phụ thuộc.

## 9. Quy trình debug khi pipeline lỗi

## 9.1. Nguyên tắc debug

Khi pipeline lỗi, không sửa code ngay.

Trước tiên cần xác định lỗi nằm ở:

* Input file.
* Output JSON.
* Mapping ID.
* Path media.
* Timestamp.
* Module logic.
* Renderer/codec.

Ưu tiên kiểm tra file trung gian trước.

## 9.2. Debug theo từng điểm dừng

### Lỗi sau Input Processor

Kiểm tra:

```text
media_metadata.json
```

Câu hỏi:

* Có audio không?
* Có video usable không?
* Path normalized có tồn tại không?
* Duration có hợp lệ không?
* Status có phải `ready` hoặc `warning` không?

### Lỗi sau Audio Analyzer

Kiểm tra:

```text
audio_segments.json
audio_analysis_log.json
```

Câu hỏi:

* Có segment không?
* Segment có timestamp hợp lệ không?
* Query có rỗng không?
* Segment có overlap không?
* ASR có nhận sai quá nặng không?

### Lỗi sau Video Analyzer

Kiểm tra:

```text
clip_metadata.json
keyframes/
```

Câu hỏi:

* Có clip candidate không?
* Clip có keyframe không?
* Keyframe path tồn tại không?
* Clip start/end có vượt video duration không?
* Quality score có hợp lệ không?

### Lỗi sau Embedding Indexer

Kiểm tra:

```text
embedding_metadata.json
embeddings/
index/
```

Câu hỏi:

* Embedding có được tạo đủ không?
* Text và visual embedding có cùng model/space không?
* Index path có tồn tại không?
* Dimension có khớp không?

### Lỗi sau Matching Engine

Kiểm tra:

```text
matching_candidates.json
```

Câu hỏi:

* Mỗi segment có candidate không?
* Candidate clip_id có tồn tại không?
* Score có hợp lệ không?
* Confidence có hợp lệ không?
* selected_clip_id có nằm trong candidates không?

### Lỗi sau Timeline Planner

Kiểm tra:

```text
timeline.json
```

Câu hỏi:

* Mỗi segment có visual_items không?
* Clip trong timeline có tồn tại không?
* Source path có tồn tại không?
* Timeline có gap/overlap sai không?
* Clip duration sau speed có khớp segment không?

### Lỗi sau Review UI

Kiểm tra:

```text
data/intermediate/timeline.json
```

Câu hỏi:

* UI có làm mất field không?
* Clip mới có tồn tại không?
* Timeline còn đúng schema không?
* user_edited có được set không?
* candidates_ref còn giữ không?

### Lỗi sau Renderer

Kiểm tra:

```text
render_log.json
final_video.mp4
```

Câu hỏi:

* Renderer lỗi ở clip nào?
* Path nào không tồn tại?
* Clip start/end nào sai?
* Codec output có lỗi không?
* Audio voice-over có được ghép không?

## 10. Quy tắc xử lý lỗi khi tích hợp

## 10.1. Lỗi chặn pipeline

Các lỗi sau nên dừng pipeline:

* Không có audio thuyết minh usable.
* Không có video nguồn usable.
* `media_metadata.json` không parse được.
* Không tạo được audio segment nào.
* Không tạo được clip candidate nào.
* `timeline.json` không hợp lệ.
* Renderer không tìm được media source.
* Renderer không xuất được video.

## 10.2. Lỗi không chặn pipeline

Các lỗi sau có thể cho pipeline chạy tiếp nhưng phải ghi warning:

* Một video nguồn bị lỗi nhưng vẫn còn video khác usable.
* ASR confidence thấp ở một số segment.
* Một số segment có confidence matching thấp.
* Một số clip có quality thấp nhưng vẫn usable.
* Không tạo được `translated_query`.
* Top-k ít hơn cấu hình mong muốn nhưng vẫn có candidate.
* Một vài transition không hỗ trợ và được fallback về `cut`.

## 10.3. Fallback tích hợp

Nếu một module chưa hoàn thiện, có thể dùng fallback để giữ pipeline chạy:

| Module chưa hoàn thiện | Fallback                                                   |
| ---------------------- | ---------------------------------------------------------- |
| Audio Analyzer         | Dùng `audio_segments_sample.json` hoặc transcript viết tay |
| Video Analyzer         | Chia video theo khoảng thời gian cố định                   |
| Embedding Indexer      | Dùng score giả hoặc keyword matching đơn giản              |
| Matching Engine        | Chọn clip theo thứ tự hoặc random có kiểm soát             |
| Timeline Planner       | Chọn clip rank 1 cho mỗi segment                           |
| Review UI              | Chỉnh trực tiếp `timeline.json`                            |
| Renderer transition    | Dùng `cut` thay vì fade/crossfade                          |

Fallback phải được ghi rõ trong log hoặc báo cáo, tránh trình bày như kết quả hoàn chỉnh.

## 11. Integration pipeline script

## 11.1. Mục tiêu

Nên có một script chạy pipeline cơ bản, ví dụ:

```text
scripts/run_demo.sh
```

hoặc:

```text
python -m integration.run_pipeline
```

Script này giúp demo và test tích hợp nhanh hơn.

## 11.2. Pipeline CLI đề xuất

Ví dụ:

```text
python -m integration.run_pipeline \
  --project-id demo_01 \
  --videos data/raw/video_01.mp4 data/raw/video_02.mp4 \
  --audio data/raw/voiceover.mp3 \
  --output-dir data \
  --top-k 5
```

## 11.3. Các bước script cần chạy

```text
1. Run Input Processor
2. Validate media_metadata.json
3. Run Audio Analyzer
4. Validate audio_segments.json
5. Run Video Analyzer
6. Validate clip_metadata.json
7. Run Embedding Indexer
8. Validate embedding_metadata.json
9. Run Matching Engine
10. Validate matching_candidates.json
11. Run Timeline Planner
12. Validate timeline.json
13. Validate render_config.json nếu dùng file cấu hình riêng
14. Run Renderer
15. Validate final_video.mp4 và render_log.json
```

## 11.4. Chế độ chạy đề xuất

Script nên hỗ trợ:

```text
--from-stage
--to-stage
--skip-ui
--overwrite
--use-sample-data
--validate-only
```

Ví dụ:

```text
python -m integration.run_pipeline --from-stage 4 --to-stage 6
```

Dùng để chạy lại từ Embedding đến Timeline mà không chạy lại ASR và Video Analyzer.

## 12. Quy tắc chạy lại pipeline

## 12.1. Khi nào cần chạy lại toàn bộ pipeline

Cần chạy lại từ đầu nếu:

* Thay video nguồn.
* Thay audio thuyết minh.
* Thay cấu hình normalize.
* Xóa file normalized.
* Đổi project_id.

## 12.2. Khi nào chỉ cần chạy lại một phần

Nếu sửa transcript:

```text
Audio Analyzer
→ Embedding Indexer
→ Matching Engine
→ Timeline Planner
→ UI/Renderer
```

Nếu sửa scene detection hoặc clip metadata:

```text
Video Analyzer
→ Embedding Indexer
→ Matching Engine
→ Timeline Planner
→ UI/Renderer
```

Nếu sửa thuật toán matching:

```text
Matching Engine
→ Timeline Planner
→ UI/Renderer
```

Nếu chỉ đổi clip trên UI:

```text
Renderer
```

Không cần chạy lại:

```text
Input Processor
Audio Analyzer
Video Analyzer
Embedding Indexer
Matching Engine
```

Nếu chỉ đổi render settings:

```text
Renderer
```

## 13. Quy tắc làm việc với branch và merge

### 13.1. Branch theo module

Mỗi thành viên nên làm trên branch riêng:

```text
feature/audio-analyzer
feature/video-analyzer
feature/matching-engine
feature/review-ui
feature/renderer
feature/integration
```

### 13.2. Không merge code chưa có output

Không nên merge module nếu:

* Chưa chạy được.
* Chưa có README.
* Chưa có output JSON.
* Output sai schema.
* Làm hỏng module khác.

### 13.3. Merge nhỏ, kiểm tra thường xuyên

Nên merge từng phần nhỏ:

* Xong input validation thì merge.
* Xong metadata writer thì merge.
* Xong ASR basic thì merge.
* Xong output schema thì merge.

Không nên để mỗi người làm quá lâu rồi merge một lần rất lớn.

## 14. Quy tắc đặt output khi tích hợp

Tất cả output chính nên đặt dưới:

```text
data/intermediate/
```

Output media nên đặt dưới:

```text
data/normalized/
data/keyframes/
data/final/
```

Gợi ý:

```text
data/
├── raw/
├── normalized/
├── keyframes/
├── intermediate/
└── final/
```

Quy tắc:

* JSON trung gian: `data/intermediate/`
* Video/audio normalized: `data/normalized/`
* Keyframe: `data/keyframes/`
* Video final: `data/final/`
* Sample data: `docs/samples/`

Không đặt output rải rác trong từng module khi chạy pipeline tích hợp. Module có thể có output test riêng, nhưng pipeline chính nên dùng cấu trúc chung.

## 15. Kiểm tra chất lượng demo

Trước buổi demo, cần kiểm tra:

```text
[ ] Input video/audio có sẵn
[ ] Pipeline chạy không lỗi
[ ] Tạo đủ file JSON trung gian
[ ] UI mở được timeline
[ ] UI đổi clip được
[ ] Renderer xuất được final_video.mp4
[ ] Video final mở được
[ ] Audio voice-over nghe được
[ ] Hình ảnh khớp tương đối với lời nói
[ ] Có ít nhất một đoạn minh họa top-k candidate
[ ] Có ít nhất một đoạn confidence thấp để giải thích review UI
[ ] Có thể giải thích timeline.json
[ ] Có thể giải thích hạn chế của hệ thống
```

## 16. Tiêu chí hoàn thành tích hợp MVP

Tích hợp MVP được xem là hoàn thành khi:

1. Chạy được pipeline với ít nhất một audio và một video nguồn.
2. Tạo được `media_metadata.json`.
3. Tạo được `audio_segments.json`.
4. Tạo được `clip_metadata.json`.
5. Tạo được `embedding_metadata.json` và embedding/index files.
6. Tạo được `matching_candidates.json`.
7. Tạo được `timeline.json`.
8. UI đọc được timeline.
9. UI đổi được clip trong top-k.
10. Timeline sau khi UI chỉnh vẫn đúng schema.
11. Renderer xuất được `final_video.mp4`.
12. Renderer xuất được `render_log.json`.
13. Final video dùng voice-over làm audio chính.
14. Final video có hình ảnh liên quan tương đối đến audio.
15. Có log hoặc thông tin debug khi lỗi.
16. Có thể chạy lại một phần pipeline khi cần.
17. Có thể giải thích rõ từng file trung gian trong báo cáo.

## 17. Rủi ro tích hợp và cách giảm

| Rủi ro                           | Ảnh hưởng                      | Cách giảm                              |
| -------------------------------- | ------------------------------ | -------------------------------------- |
| Các module xuất JSON khác schema | Không ghép được pipeline       | Validate JSON trước khi merge          |
| ID không khớp giữa các file      | Timeline/UI/Renderer lỗi       | Chốt quy tắc ID và kiểm tra cross-file |
| Path dùng absolute path          | Máy khác không chạy được       | Bắt buộc dùng relative path            |
| Timestamp audio sai              | Timeline lệch voice-over       | Validate duration và timestamp         |
| Clip start/end sai               | Renderer lỗi hoặc cắt sai cảnh | Kiểm tra clip nằm trong duration video |
| Keyframe path sai                | Embedding lỗi                  | Validate path sau Video Analyzer       |
| Matching trả clip không tồn tại  | Timeline Planner lỗi           | Cross-check với clip metadata          |
| UI làm hỏng timeline             | Renderer không chạy            | Validate timeline sau khi UI lưu       |
| Renderer lỗi codec               | Không xuất được video          | Chuẩn hóa media từ Stage 1             |
| Merge conflict nhiều             | Chậm tiến độ                   | Chia code theo module, merge nhỏ       |

## 18. Vai trò của leader trong tích hợp

Leader cần phụ trách:

* Giữ Data Contract ổn định.
* Review output của từng module.
* Tạo sample data.
* Viết hoặc quản lý validator.
* Tích hợp từng module vào pipeline.
* Quyết định khi nào dùng fallback.
* Kiểm tra demo end-to-end.
* Ghi lại lỗi tích hợp thường gặp.
* Đảm bảo tài liệu và code không lệch nhau.

Leader không nhất thiết phải viết toàn bộ code tích hợp, nhưng cần nắm rõ:

```text
File nào được tạo ở đâu
File nào được module nào đọc
ID nào cần khớp
Path nào cần tồn tại
Pipeline lỗi ở đâu thì kiểm tra gì trước
```

## 19. Checklist tích hợp cuối cùng

Trước khi chốt MVP, kiểm tra:

```text
[ ] docs/details/02_data_contract.md đã được review và thống nhất cho MVP hiện tại
[ ] docs/samples/ có sample JSON hợp lệ
[ ] media_metadata.json đúng schema
[ ] audio_segments.json đúng schema
[ ] clip_metadata.json đúng schema
[ ] embedding_metadata.json đúng schema
[ ] embedding/index files có thể load được nếu dùng index riêng
[ ] matching_candidates.json đúng schema
[ ] timeline.json đúng schema
[ ] render_log.json đúng schema sau khi render
[ ] ID khớp giữa các file
[ ] Path media/keyframe tồn tại
[ ] Pipeline không UI chạy được
[ ] UI đọc timeline được
[ ] UI đổi clip được
[ ] UI lưu timeline đúng schema
[ ] Renderer đọc timeline được
[ ] Renderer xuất final_video.mp4
[ ] final_video.mp4 mở được
[ ] Có render_log.json
[ ] Có cách chạy demo rõ ràng
[ ] Có ghi chú hạn chế hiện tại
```

## 20. Kết luận

Integration Plan giúp nhóm chuyển từ các module riêng lẻ sang một hệ thống hoàn chỉnh.

Điểm quan trọng nhất không phải là mỗi module dùng thuật toán phức tạp đến đâu, mà là:

* Output có đúng Data Contract không.
* ID có khớp không.
* Path có đúng không.
* Timeline có render được không.
* Pipeline có chạy end-to-end không.

Nguyên tắc cuối cùng:

**Tích hợp sớm bằng sample data, kiểm tra schema liên tục, thay dần module giả bằng module thật, và luôn giữ `timeline.json` là trung tâm của bản dựng.**
