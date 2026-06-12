# 01. System Architecture

## 1. Mục tiêu của kiến trúc

Kiến trúc hệ thống cần đảm bảo các mục tiêu sau:

* Chia bài toán lớn thành các module nhỏ, rõ trách nhiệm.
* Mỗi module có input/output cụ thể để các thành viên phát triển song song.
* Dữ liệu trung gian được lưu thành các file JSON dễ kiểm tra, dễ debug.
* Hạn chế phụ thuộc trực tiếp giữa các phần code của từng thành viên.
* Cho phép thay thế hoặc cải thiện từng module mà không phá vỡ toàn bộ hệ thống.
* Cho phép UI chỉnh sửa timeline mà không cần chạy lại toàn bộ pipeline.
* Renderer render theo `timeline.json` và media source đã chuẩn hóa để xuất video cuối.

Kiến trúc được thiết kế theo hướng pipeline nhiều bước, trong đó các module trao đổi với nhau thông qua các file dữ liệu trung gian.

## 2. Tổng quan pipeline

Pipeline tổng thể:

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

Luồng dữ liệu tổng quát:

```text
Video source(s) + Voice-over audio
        │
        v
Input Processor
        │
        ├── media_metadata.json
        │
        ├── normalized videos
        │
        └── normalized audio
        │
        ├────────────────────────────┐
        │                            │
        v                            v
Audio Analyzer                  Video Analyzer
        │                            │
        v                            v
audio_segments.json             clip_metadata.json
        │                            │
        └──────────────┬─────────────┘
                       v
              Embedding Indexer
                       │
                       v
              embedding/index files
              embedding_metadata.json
                       │
                       v
              Matching Engine
                       │
                       v
          matching_candidates.json
                       │
                       v
              Timeline Planner
                       │
                       v
                 timeline.json
                       │
                       v
                  Review UI
                       │
                       v
          timeline.json (cập nhật, cùng path)
                       │
                       v
                   Renderer
                       │
                       v
                final_video.mp4
```

## 3. Nguyên tắc thiết kế chính

### 3.1. Module giao tiếp bằng dữ liệu trung gian

Các module không nên gọi trực tiếp logic nội bộ của nhau nếu không cần thiết. Thay vào đó, mỗi module đọc file đầu vào và sinh file đầu ra theo schema đã thống nhất.

Ví dụ:

```text
Audio Analyzer
→ xuất audio_segments.json
→ Matching Engine đọc audio_segments.json
```

Cách này giúp:

* Dễ chia việc.
* Dễ kiểm tra output từng bước.
* Dễ debug khi pipeline lỗi.
* Dễ thay thế module cũ bằng module tốt hơn.

### 3.2. `timeline.json` là trung tâm của bản dựng

`timeline.json` là file mô tả video sẽ được dựng như thế nào.

File này kết nối ba phần quan trọng:

* Timeline Planner tạo bản dựng ban đầu.
* Review UI cho người dùng chỉnh sửa timeline.
* Renderer đọc timeline để xuất video cuối.

Khi người dùng chỉnh clip, speed hoặc transition trên UI, hệ thống chỉ cần cập nhật `timeline.json`, sau đó render lại video. Không cần chạy lại ASR, scene detection, embedding hoặc matching.

### 3.3. Tách phân tích và render

Phân tích dữ liệu và render video là hai phần riêng biệt.

Phần phân tích gồm:

* Audio analysis.
* Video analysis.
* Embedding.
* Matching.
* Timeline planning.

Phần render chỉ gồm:

* Đọc timeline.
* Cắt clip.
* Ghép clip.
* Ghép audio.
* Xuất video.

Tách như vậy giúp renderer hoạt động ổn định và dễ test bằng `timeline_sample.json`, `media_metadata_sample.json`, `render_config_sample.json` và media source mẫu.

### 3.4. Tách UI và renderer

UI không trực tiếp xử lý video nặng. UI chỉ:

* Hiển thị timeline.
* Hiển thị transcript.
* Hiển thị clip được chọn.
* Hiển thị top-k candidate.
* Cho phép người dùng chỉnh lựa chọn.
* Cập nhật `timeline.json`.

Renderer mới là phần xuất video cuối.

Điều này giúp UI đơn giản hơn và tránh biến UI thành phần mềm dựng video phức tạp.

### 3.5. Mỗi stage có thể test độc lập

Mỗi module cần có khả năng chạy riêng với dữ liệu mẫu.

Ví dụ:

* `audio_analyzer/` có thể test bằng một audio ngắn.
* `video_analyzer/` có thể test bằng một video ngắn.
* `matching_engine/` có thể test bằng `audio_segments_sample.json`, `clip_metadata_sample.json`, `embedding_metadata_sample.json` và embedding/index sample files.
* `renderer/` có thể test bằng `timeline_sample.json`, `media_metadata_sample.json`, `render_config_sample.json` và media source mẫu.

## 4. Các module chính

## 4.1. Input Processor

### Vai trò

Chuẩn hóa và kiểm tra dữ liệu đầu vào trước khi đưa vào pipeline.

### Input

* Video nguồn.
* Audio thuyết minh.
* Cấu hình xử lý cơ bản.

### Xử lý chính

* Kiểm tra định dạng file.
* Lấy metadata video/audio.
* Chuẩn hóa video nếu cần.
* Chuẩn hóa audio nếu cần.
* Lưu đường dẫn file đã chuẩn hóa.
* Xuất metadata dùng chung.

### Output

```text
media_metadata.json
normalized video files
normalized audio file
```

### Module sử dụng output

* Audio Analyzer.
* Video Analyzer.
* Timeline Planner.
* Review UI.
* Renderer.
* Integration pipeline.

## 4.2. Audio Analyzer

### Vai trò

Phân tích audio thuyết minh để tạo transcript có timestamp và chia thành các audio segment.

### Input

```text
normalized audio file
media_metadata.json
```

### Xử lý chính

* Chạy ASR để chuyển audio thành text.
* Lấy timestamp theo câu, cụm từ hoặc đoạn nói.
* Chia audio thành các segment có ý nghĩa.
* Tạo query tìm kiếm clip cho từng segment.
* Cho phép sửa transcript nếu cần.

### Output

```text
audio_segments.json
```

### Module sử dụng output

* Embedding Indexer.
* Matching Engine.
* Timeline Planner.
* Review UI.
* Evaluation.

## 4.3. Video Analyzer

### Vai trò

Phân tích video nguồn để tạo danh sách clip candidate có thể dùng trong bản dựng.

### Input

```text
normalized video files
media_metadata.json
```

### Xử lý chính

* Scene detection hoặc shot detection.
* Tách video thành các clip candidate.
* Loại clip quá ngắn hoặc lỗi rõ ràng.
* Chia nhỏ clip quá dài nếu cần.
* Trích nhiều keyframe cho mỗi clip.
* Tính quality score cơ bản.
* Lưu metadata của từng clip.

### Output

```text
clip_metadata.json
keyframe image files
```

### Module sử dụng output

* Embedding Indexer.
* Matching Engine.
* Timeline Planner.
* Review UI.
* Renderer.
* Evaluation.

## 4.4. Embedding Indexer

### Vai trò

Tạo đặc trưng vector cho text query và keyframe/clip để phục vụ tìm kiếm theo nghĩa.

### Input

```text
audio_segments.json
clip_metadata.json
keyframe image files
```

### Xử lý chính

* Tạo text embedding cho query của từng audio segment.
* Tạo image embedding cho keyframe.
* Có thể tổng hợp nhiều keyframe để đại diện cho một clip.
* Lưu embedding và index để matching truy vấn nhanh.

### Output

```text
embedding/index files
embedding_metadata.json
```

### Module sử dụng output

* Matching Engine.

## 4.5. Matching Engine

### Vai trò

Tìm top-k clip phù hợp nhất cho từng audio segment.

### Input

```text
audio_segments.json
clip_metadata.json
embedding_metadata.json
embedding/index files
```

### Xử lý chính

* So sánh text embedding với image/clip embedding.
* Tính semantic score.
* Kết hợp thêm quality score, duration fit, diversity, continuity nếu có.
* Áp dụng penalty cho clip xấu hoặc bị lặp quá gần.
* Trả về top-k candidate cho mỗi audio segment.
* Gán confidence cho kết quả matching.

### Output

```text
matching_candidates.json
```

### Module sử dụng output

* Timeline Planner.
* Review UI.
* Evaluation.

## 4.6. Timeline Planner

### Vai trò

Tạo timeline dựng video ban đầu từ audio segment và matching result.

### Input

```text
audio_segments.json
clip_metadata.json
matching_candidates.json
media_metadata.json
```

### Xử lý chính

* Chọn clip mặc định cho mỗi audio segment.
* Xử lý trường hợp clip dài hơn audio segment.
* Xử lý trường hợp clip ngắn hơn audio segment.
* Cho phép một audio segment gồm một hoặc nhiều visual items.
* Thêm speed mặc định.
* Thêm transition mặc định.
* Chọn fallback clip nếu confidence thấp hoặc không có clip phù hợp.
* Tạo timeline có thể được UI chỉnh sửa và renderer sử dụng.

### Output

```text
timeline.json
```

### Module sử dụng output

* Review UI.
* Renderer.
* Evaluation.

## 4.7. Review UI

### Vai trò

Cho người dùng kiểm tra và chỉnh sửa bản dựng ban đầu theo cách đơn giản.

### Input

```text
timeline.json
matching_candidates.json
clip_metadata.json
audio_segments.json
media_metadata.json
media files
```

### Xử lý chính

* Hiển thị danh sách audio segment.
* Hiển thị transcript từng segment.
* Hiển thị clip đang được chọn.
* Hiển thị score và confidence.
* Highlight đoạn confidence thấp.
* Hiển thị top-k clip thay thế.
* Cho phép người dùng đổi clip.
* Cho phép chỉnh một số tham số cơ bản nếu có.
* Cập nhật timeline sau khi người dùng chỉnh.

### Output

```text
timeline.json (ghi đè cùng path sau khi người dùng chỉnh)
```

### Module sử dụng output

* Renderer.

## 4.8. Renderer

### Vai trò

Render video cuối từ timeline đã được tạo hoặc chỉnh sửa.

### Input

```text
timeline.json
media_metadata.json
clip_metadata.json (optional for validation)
normalized video files
normalized audio file
render_config.json (optional)
```

### Xử lý chính

* Đọc timeline.
* Cắt từng clip theo `clip_start` và `clip_end`.
* Điều chỉnh speed nếu cần.
* Scale/crop về resolution đầu ra.
* Thêm transition cơ bản.
* Ghép các clip theo thứ tự timeline.
* Dùng voice-over làm audio chính.
* Tắt hoặc giảm âm lượng audio gốc nếu cần.
* Xuất video cuối.

### Output

```text
final_video.mp4
render_log.json
```

## 4.9. Evaluation

### Vai trò

Đánh giá chất lượng kết quả để phục vụ báo cáo và cải thiện hệ thống.

### Input

```text
audio_segments.json
clip_metadata.json
embedding_metadata.json (optional)
matching_candidates.json
timeline.json
final_video.mp4
render_log.json
```

### Xử lý chính

* Tính segment coverage.
* Tính average semantic score.
* Tính low-confidence rate.
* Tính repetition rate.
* Tính duration error.
* Ghi nhận số lần người dùng chỉnh clip.
* Hỗ trợ đánh giá định tính từ người xem.

### Output

```text
evaluation_report.json
evaluation_summary.md
```

Evaluation có thể làm sau MVP, nhưng nên giữ vị trí trong kiến trúc để phục vụ báo cáo đồ án.

## 5. Các file dữ liệu trung gian

## 5.1. `media_metadata.json`

Do Input Processor tạo.

Chứa thông tin về video/audio đầu vào:

* ID media.
* Đường dẫn file.
* Duration.
* FPS.
* Resolution.
* Codec.
* Audio sample rate.
* Trạng thái chuẩn hóa.

## 5.2. `audio_segments.json`

Do Audio Analyzer tạo.

Chứa danh sách audio segment:

* `segment_id`
* `start`
* `end`
* `text`
* `query`
* thông tin confidence của ASR nếu có

## 5.3. `clip_metadata.json`

Do Video Analyzer tạo.

Chứa danh sách clip candidate:

* `clip_id`
* `video_id`
* `start`
* `end`
* `duration`
* `keyframes`
* `quality_score`
* `quality.blur_score`, `quality.brightness_score`, `quality.motion_score`, `quality.stability_score` nếu có

## 5.4. `embedding_metadata.json`

Do Embedding Indexer tạo.

Chứa thông tin mapping giữa clip/keyframe/query và embedding tương ứng.

## 5.5. `matching_candidates.json`

Do Matching Engine tạo.

Chứa top-k clip cho từng audio segment:

* `audio_segment_id`
* `selected_clip_id`
* `confidence`
* danh sách `candidates`
* score thành phần
* reason ngắn nếu có

## 5.6. `timeline.json`

Do Timeline Planner tạo, sau đó Review UI có thể cập nhật.

Chứa bản dựng cuối cùng ở dạng dữ liệu:

* Audio segment.
* Transcript.
* Visual items.
* Clip source.
* Clip start/end.
* Speed.
* Transition.
* Effect.
* Confidence.
* Candidate reference.

## 5.7. `render_config.json`

Do người dùng hoặc hệ thống tạo.

Chứa cấu hình render:

* Resolution.
* FPS.
* Output format.
* Audio mix setting.
* Default transition.
* Crop mode.

## 5.8. `render_log.json`

Do Renderer tạo.

Chứa thông tin quá trình render:

* Trạng thái render.
* Output path.
* Duration output.
* Render time.
* Warning/error nếu có.

## 6. Luồng chạy chính của hệ thống

## 6.1. Luồng tạo bản dựng ban đầu

```text
1. Người dùng cung cấp video nguồn và audio thuyết minh.
2. Input Processor kiểm tra và chuẩn hóa dữ liệu.
3. Audio Analyzer và Video Analyzer chạy song song sau khi có dữ liệu chuẩn hóa.
4. Audio Analyzer tạo audio_segments.json; Video Analyzer tạo clip_metadata.json và keyframe.
5. Embedding Indexer tạo embedding_metadata.json và embedding/index files.
6. Matching Engine tạo matching_candidates.json.
7. Timeline Planner tạo timeline.json.
8. Review UI mở timeline để người dùng kiểm tra.
```

Kết quả của luồng này là một bản dựng ban đầu có thể review.

## 6.2. Luồng chỉnh sửa trên UI

```text
1. Người dùng chọn một audio segment.
2. UI hiển thị clip hiện tại và top-k candidate.
3. Người dùng chọn clip khác hoặc chỉnh tham số cơ bản.
4. UI cập nhật timeline.json.
5. Người dùng preview lại đoạn đã chỉnh.
```

Luồng này không cần chạy lại toàn bộ pipeline.

## 6.3. Luồng render video cuối

```text
1. Renderer đọc timeline.json.
2. Renderer đọc video/audio nguồn đã chuẩn hóa.
3. Renderer cắt và ghép clip theo timeline.
4. Renderer ghép voice-over làm audio chính.
5. Renderer xuất final_video.mp4.
```

Renderer không phụ thuộc trực tiếp vào Matching Engine hoặc Audio Analyzer. Renderer chỉ cần timeline hợp lệ và media source tồn tại.

## 6.4. Luồng render lại sau chỉnh sửa

```text
1. Người dùng chỉnh timeline trên UI.
2. UI ghi đè `data/intermediate/timeline.json` và cập nhật `updated_at`.
3. Renderer đọc cùng file `timeline.json`.
4. Renderer xuất lại `final_video.mp4`.
```

Không chạy lại:

* ASR.
* Scene detection.
* Embedding.
* Matching.

Trừ khi người dùng thay đổi input hoặc yêu cầu phân tích lại.

## 7. Luồng phụ thuộc giữa các module

## 7.1. Module có thể làm song song ngay

Các module có thể phát triển sớm bằng dữ liệu mẫu:

| Module           | Điều kiện để làm độc lập                                       |
| ---------------- | -------------------------------------------------------------- |
| Audio Analyzer   | Có audio mẫu                                                   |
| Video Analyzer   | Có video mẫu                                                   |
| Review UI        | Có `timeline_sample.json`, `matching_candidates_sample.json`, `clip_metadata_sample.json`, `audio_segments_sample.json` và `media_metadata_sample.json` |
| Renderer         | Có `timeline_sample.json`, `media_metadata_sample.json`, `render_config_sample.json` và media source mẫu |
| Timeline Planner | Có `audio_segments_sample.json`, `clip_metadata_sample.json`, `matching_candidates_sample.json` và `media_metadata_sample.json` |
| Schema/Validator | Có data contract                                               |
| Evaluation       | Có timeline/video mẫu                                          |

## 7.2. Module phụ thuộc một phần

| Module                    | Phụ thuộc                                      |
| ------------------------- | ---------------------------------------------- |
| Embedding Indexer         | Cần audio segments, clip metadata và keyframe  |
| Matching Engine           | Cần audio segments, clip metadata và embedding |
| Timeline Planner bản thật | Cần audio segments, clip metadata, media metadata và matching candidates |
| UI bản đầy đủ             | Cần timeline, matching candidates, clip metadata, audio segments và media metadata |
| Renderer bản đầy đủ       | Cần timeline, media metadata, clip metadata nếu validate, render config nếu dùng file cấu hình riêng và media source |

## 7.3. Cách giảm phụ thuộc

Cần tạo sớm bộ dữ liệu mẫu:

```text
docs/samples/audio_segments_sample.json
docs/samples/media_metadata_sample.json
docs/samples/clip_metadata_sample.json
docs/samples/embedding_metadata_sample.json
docs/samples/embedding_index_sample/
docs/samples/matching_candidates_sample.json
docs/samples/timeline_sample.json
docs/samples/render_config_sample.json
docs/samples/render_log_sample.json
```

Nhờ vậy:

* UI không cần chờ Matching Engine hoàn thiện.
* Renderer không cần chờ Timeline Planner hoàn thiện.
* Matching Engine biết output cần trả về dạng nào.
* Timeline Planner có thể test logic bằng dữ liệu giả.
* Leader dễ kiểm tra tích hợp từng phần.

## 8. Ranh giới trách nhiệm giữa các module

## 8.1. Audio Analyzer không chọn clip

Audio Analyzer chỉ tạo transcript, timestamp, segment và query.

Không xử lý:

* Chọn video clip.
* Tính visual quality.
* Tạo timeline.

## 8.2. Video Analyzer không hiểu nội dung audio

Video Analyzer chỉ phân tích video nguồn.

Không xử lý:

* Transcript.
* Audio segment.
* Matching với lời nói.
* Timeline dựng cuối.

## 8.3. Matching Engine không render video

Matching Engine chỉ trả về top-k candidate và score.

Không xử lý:

* Cắt video.
* Ghép clip.
* Render output.
* UI chỉnh sửa.

## 8.4. Timeline Planner không chạy model nặng

Timeline Planner dùng kết quả đã có để lập bản dựng.

Không xử lý:

* ASR.
* Scene detection.
* Embedding.
* Matching model.

## 8.5. UI không sửa video gốc

UI chỉ sửa dữ liệu timeline.

Không xử lý:

* Ghi đè video nguồn.
* Cắt video thật.
* Render video cuối trực tiếp nếu không cần thiết.

## 8.6. Renderer không quyết định clip nào phù hợp

Renderer chỉ làm theo timeline.

Không xử lý:

* Chọn clip.
* Tính confidence.
* Tìm top-k candidate.
* Chấm điểm semantic.

## 9. Kiến trúc thư mục liên quan

Code được chia theo module ngang hàng với `docs/`:

```text
integration/
input_processor/
audio_analyzer/
video_analyzer/
embedding_indexer/
matching_engine/
timeline_planner/
review_ui/
renderer/
shared/
data/
scripts/
```

Mỗi module cần có README riêng mô tả:

* Module làm gì.
* Input là gì.
* Output là gì.
* Cách chạy.
* Cách test.
* Ví dụ output.

## 10. Chiến lược tích hợp

## 10.1. Tích hợp theo từng lớp

Không nên chờ tất cả module hoàn thiện mới tích hợp. Nên tích hợp theo từng lớp:

### Lớp 1: Dữ liệu mẫu

Tạo sample JSON đúng schema.

Mục tiêu:

* UI đọc được timeline mẫu.
* Renderer render được video mẫu.
* Timeline Planner đọc được audio segment mẫu, clip metadata mẫu, media metadata mẫu và matching mẫu.

### Lớp 2: Module thật nhưng chạy độc lập

Từng module chạy được riêng và xuất output đúng schema.

Mục tiêu:

* Audio module xuất `audio_segments.json`.
* Video module xuất `clip_metadata.json`.
* Embedding module xuất `embedding_metadata.json` và embedding/index files.
* Matching module xuất `matching_candidates.json`.
* Timeline module xuất `timeline.json`.

### Lớp 3: Pipeline bán tự động

Ghép các module bằng script hoặc integration pipeline.

Mục tiêu:

```text
audio_segments.json + clip_metadata.json + embedding_metadata.json + embedding/index files
→ matching_candidates.json
→ timeline.json
timeline.json + media_metadata.json + normalized media files
→ final_video.mp4 + render_log.json
```

### Lớp 4: UI review

Kết nối UI với timeline và candidates.

Mục tiêu:

* UI xem được timeline thật.
* UI đổi được clip.
* UI lưu lại timeline đã chỉnh.

### Lớp 5: Demo end-to-end

Chạy toàn bộ pipeline với dữ liệu demo.

Mục tiêu:

```text
Input video/audio
→ intermediate JSON files
→ review timeline
→ render final video
```

## 10.2. Kiểm tra khi tích hợp

Khi tích hợp, cần kiểm tra:

* File output có tồn tại không.
* JSON có parse được không.
* Field bắt buộc có đủ không.
* ID giữa các file có khớp không.
* Thời gian start/end có hợp lệ không.
* Clip source có tồn tại không.
* Segment duration có khớp timeline không.
* Renderer có đọc được timeline không.

Nếu lỗi, ưu tiên kiểm tra dữ liệu trung gian trước khi sửa code.

## 11. Các nguyên tắc về ID và mapping

## 11.1. `video_id`

Định danh một video nguồn.

Ví dụ:

```text
video_01
video_02
```

## 11.2. `segment_id`

Định danh một audio segment.

Ví dụ:

```text
a001
a002
a003
```

## 11.3. `clip_id`

Định danh một clip candidate được tách từ video nguồn.

Ví dụ format (padding clip index 3 chữ số):

```text
v01_c001
v01_c003
v02_c002
```

Mẫu clip ID tích hợp: `docs/samples/clip_metadata_sample.json`.

## 11.4. Mapping quan trọng

Các mapping cần giữ nhất quán:

```text
audio_segments.items[].segment_id
→ matching_candidates.items[].audio_segment_id
→ timeline.items[].segment_id

clip_metadata.items[].clip_id
→ matching_candidates.items[].candidates[].clip_id
→ timeline.items[].visual_items[].clip_id

media_metadata.videos[].video_id
→ clip_metadata.items[].video_id
→ timeline.items[].visual_items[].video_id
```

Nếu các ID không khớp, pipeline sẽ lỗi khi tích hợp.

## 12. Xử lý lỗi ở mức kiến trúc

## 12.1. Audio không nhận diện được transcript

Cách xử lý:

* Đánh dấu segment lỗi hoặc confidence thấp.
* Cho phép người dùng sửa transcript.
* Không dừng toàn bộ pipeline nếu chỉ một đoạn lỗi nhẹ.

## 12.2. Video không tách được scene tốt

Cách xử lý:

* Dùng chia clip theo khoảng thời gian cố định làm fallback.
* Loại clip quá ngắn.
* Chia clip quá dài thành đoạn nhỏ hơn.

## 12.3. Không tìm được clip phù hợp

Cách xử lý:

* Dùng clip fallback.
* Dùng cảnh toàn hoặc cảnh môi trường.
* Chọn clip chất lượng hình tốt nhất có liên quan gần.
* Đánh dấu confidence thấp.

## 12.4. Clip ngắn hơn audio segment

Cách xử lý:

* Ghép nhiều visual items cho cùng segment.
* Dùng thêm candidate khác.
* Làm chậm nhẹ nếu hợp lý.
* Dùng fallback clip nếu cần.

## 12.5. Clip dài hơn audio segment

Cách xử lý:

* Cắt đoạn phù hợp nhất.
* Ưu tiên đoạn giữa clip nếu chưa có phân tích sâu.
* Tránh đoạn đầu/cuối nếu có chuyển động máy không ổn định.

## 12.6. Renderer lỗi do codec hoặc media source

Cách xử lý:

* Kiểm tra media đã được chuẩn hóa chưa.
* Kiểm tra path trong timeline.
* Kiểm tra clip start/end có nằm trong duration video không.
* Xuất log lỗi để debug.

## 13. Kiến trúc phục vụ phát triển song song

Kiến trúc này hỗ trợ nhóm phát triển song song theo cách sau:

* Người làm audio chỉ cần bám `audio_segments.json`.
* Người làm video chỉ cần bám `clip_metadata.json`.
* Người làm matching chỉ cần đọc audio segment, clip metadata và embedding.
* Người làm timeline cần đọc audio segments, clip metadata, media metadata và matching candidates.
* Người làm UI có thể dùng sample timeline để làm trước.
* Người làm renderer có thể dùng sample timeline để render trước.
* Leader quản lý schema, sample data và integration.

Điểm quan trọng là mọi module phải thống nhất data contract. Nếu mỗi người tự định nghĩa output riêng, việc tích hợp sẽ rất khó.

## 14. Kiến trúc MVP và kiến trúc mở rộng

## 14.1. Kiến trúc MVP

Trong MVP, hệ thống ưu tiên:

* Pipeline chạy được từ đầu đến cuối.
* JSON trung gian rõ ràng.
* Matching ở mức baseline.
* UI review đơn giản.
* Renderer ổn định.
* Có demo thực tế.

MVP không yêu cầu matching hoàn hảo hoặc UI phức tạp.

## 14.2. Hướng mở rộng sau MVP

Sau khi MVP ổn định, có thể mở rộng:

* Matching tốt hơn bằng model mạnh hơn.
* Caption cho clip để hiểu nội dung video tốt hơn.
* Action recognition cho hành động phức tạp.
* Timeline planner thông minh hơn.
* UI chỉnh speed, transition, crop mode tốt hơn.
* Preview nhanh từng segment.
* Render cache để không render lại toàn bộ video.
* Đánh giá tự động kết quả tốt hơn.

## 15. Kết luận kiến trúc

Kiến trúc được chọn là pipeline module hóa, giao tiếp bằng dữ liệu trung gian, với `timeline.json` làm trung tâm của bản dựng.

Thiết kế này phù hợp với đồ án nhóm vì:

* Dễ chia việc cho nhiều thành viên.
* Dễ phát triển song song.
* Dễ debug.
* Dễ demo.
* Dễ thay thế từng module.
* Dễ mở rộng sau MVP.
* Phù hợp với hướng sản phẩm bán tự động.

Nguyên tắc quan trọng nhất của toàn bộ kiến trúc là:

**Mỗi module có thể triển khai khác nhau, nhưng input/output phải tuân thủ data contract chung.**
