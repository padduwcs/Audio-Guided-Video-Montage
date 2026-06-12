# 08. Stage 6 - Timeline Planning

## 1. Mục tiêu của stage

Stage 6 - Timeline Planning có nhiệm vụ tạo bản dựng video ban đầu ở dạng `timeline.json`, dựa trên audio segments, clip metadata và kết quả matching từ các stage trước.

Stage này là cầu nối giữa phần phân tích và phần dựng video. Output của stage này phải đủ rõ để Review UI hiển thị, cho người dùng chỉnh sửa và Renderer xuất video cuối mà không cần gọi lại Matching Engine.

Mục tiêu chính:

* Đọc `audio_segments.json`.
* Đọc `clip_metadata.json`.
* Đọc `matching_candidates.json`.
* Đọc `media_metadata.json`.
* Validate mapping giữa `segment_id`, `clip_id`, `video_id` và source path.
* Tạo một timeline segment item cho mỗi audio segment.
* Chọn visual item mặc định dựa trên `selected_clip_id` từ Matching Engine.
* Xử lý clip dài hơn audio segment.
* Xử lý clip ngắn hơn audio segment.
* Cho phép một audio segment có một hoặc nhiều visual items.
* Gán `timeline_start`, `timeline_end`, `clip_start`, `clip_end`.
* Gán `speed`, `transition`, `crop_mode`, `volume`.
* Đánh dấu `needs_review`, `fallback_used`, `confidence`.
* Tạo `timeline.json` đúng Data Contract hiện hành.
* Tạo log phụ để debug quyết định lập timeline nếu cần.

## 2. Vị trí trong pipeline

Stage này nằm sau Matching Engine và trước Review UI:

```text
Audio Analyzer  -- audio_segments.json ------\
Video Analyzer  -- clip_metadata.json -------\
Matching Engine -- matching_candidates.json --+--> Timeline Planner
Input Processor -- media_metadata.json ------/
                                                |
                                                |-- timeline.json
                                                |-- timeline_planning_log.json
                                                |
                                                |--> Review UI
                                                |--> Renderer (if timeline is renderer-ready)
                                                |--> Evaluation (later)
```

Timeline Planner không quyết định lại clip nào phù hợp về mặt ngữ nghĩa. Quyết định ngữ nghĩa nằm ở Matching Engine. Timeline Planner chỉ biến candidate đã chọn thành timeline có thể dựng được.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Timeline Planner cần xử lý các phần sau:

1. Đọc bốn input chính.
2. Validate `schema_version` và `project_id`.
3. Validate audio chính trong `media_metadata.json`.
4. Validate mỗi `audio_segments.items[].segment_id` có candidate set tương ứng nếu Matching Engine đã chạy đầy đủ.
5. Validate candidate `clip_id` tồn tại trong `clip_metadata.json`.
6. Validate clip map được về `video_id`.
7. Validate `video_id` tồn tại trong `media_metadata.json`.
8. Chọn clip mặc định cho mỗi audio segment.
9. Tạo `timeline.items[]` theo đúng thứ tự audio segment.
10. Tính vị trí trên timeline output theo `audio_start` và `audio_end`.
11. Tính đoạn cắt trong video nguồn bằng `clip_start` và `clip_end`.
12. Tính `speed` nếu cần fit duration.
13. Tách một audio segment thành nhiều visual items nếu một clip không đủ dài.
14. Gán transition mặc định.
15. Gán crop mode mặc định hoặc override.
16. Gán volume của audio gốc theo render settings.
17. Đánh dấu fallback và review flag.
18. Xuất `timeline.json`.
19. Xuất `timeline_planning_log.json` để debug nếu cần.

### 3.2. Stage này không làm

Timeline Planner không chịu trách nhiệm cho các phần sau:

* Không chạy ASR.
* Không sửa transcript.
* Không detect scene hoặc shot.
* Không trích keyframe.
* Không tạo embedding.
* Không tính lại semantic similarity.
* Không thay đổi `matching_candidates.json`.
* Không thay đổi `clip_metadata.json`.
* Không render video.
* Không xử lý tương tác của người dùng trên UI.
* Không lưu quyết định chỉnh sửa của người dùng.

Nếu input thiếu hoặc không hợp lệ, Timeline Planner phải báo lỗi hoặc đánh dấu item cần review. Không tự chạy lại các stage trước.

## 4. Input

### 4.1. Input chính

Timeline Planner đọc:

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/matching_candidates.json
data/intermediate/media_metadata.json
```

Trong đó:

* `audio_segments.json` cung cấp thứ tự audio segment, timestamp, duration, transcript và `segment_id`.
* `clip_metadata.json` cung cấp clip source, `video_id`, `start`, `end`, `duration`, `quality_score` và status nếu có.
* `matching_candidates.json` cung cấp candidate set, top-k clip, `selected_clip_id`, score, confidence và fallback flag.
* `media_metadata.json` cung cấp audio chính, video source đã chuẩn hóa và thông tin render tham chiếu như fps/resolution nếu cần.

### 4.2. Điều kiện input hợp lệ

Bốn file chính phải thỏa:

* Parse được JSON.
* Có `schema_version`.
* Có `project_id`.
* `project_id` giữa các file phải giống nhau.

`audio_segments.json` phải có:

* `items` không rỗng.
* Mỗi segment có `segment_id`.
* Mỗi segment có `start`, `end`, `duration`.
* `duration` khớp với `end - start`, chấp nhận sai số nhỏ.
* Segment được sắp theo thời gian tăng dần.
* Segment không overlap bất thường.

`clip_metadata.json` phải có:

* `items` không rỗng.
* Mỗi clip có `clip_id`.
* Mỗi clip có `video_id`.
* Mỗi clip có `source_path` hoặc có thể suy ra source path từ `media_metadata.videos[].normalized_path`.
* Mỗi clip có `start`, `end`, `duration`.
* `duration > 0`.
* Nếu có `status`, status không được là `error` khi dùng làm visual item.

`matching_candidates.json` phải có:

* Có candidate set cho mỗi audio segment trong điều kiện chạy bình thường.
* Mỗi candidate set có `audio_segment_id`.
* `audio_segment_id` tồn tại trong `audio_segments.json`.
* `selected_clip_id` là `null` hoặc tồn tại trong `candidates[].clip_id`.
* Mỗi candidate có `clip_id`, `rank`, `final_score`.
* `confidence` thuộc `high`, `medium`, `low`.

`media_metadata.json` phải có:

* `audio.audio_id`.
* `audio.normalized_path`.
* `audio.duration > 0`.
* Ít nhất một video có `status = ready` hoặc `status = warning`.
* Với video usable, `normalized_path` tồn tại.

### 4.3. Cấu hình chạy module

Cấu hình dưới đây là cấu hình nội bộ của Timeline Planner, không phải Data Contract bắt buộc giữa các module.

Ví dụ cấu hình:

```json
{
  "project_id": "demo_01",
  "audio_segments_path": "data/intermediate/audio_segments.json",
  "clip_metadata_path": "data/intermediate/clip_metadata.json",
  "matching_candidates_path": "data/intermediate/matching_candidates.json",
  "media_metadata_path": "data/intermediate/media_metadata.json",
  "output_dir": "data/intermediate",
  "render_settings": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "format": "mp4",
    "default_transition": "cut",
    "crop_mode": "center_crop",
    "keep_original_audio": false,
    "original_audio_volume": 0.0
  },
  "timing": {
    "min_speed": 0.75,
    "max_speed": 1.25,
    "time_tolerance": 0.01
  },
  "fallback": {
    "enabled": true,
    "allow_low_quality": true,
    "allow_reuse_clip": true
  }
}
```

Trong MVP, các giá trị đề xuất:

| Tham số | Giá trị đề xuất |
| ------- | --------------- |
| `render_settings.width` | `1920` |
| `render_settings.height` | `1080` |
| `render_settings.fps` | `30` |
| `render_settings.format` | `mp4` |
| `render_settings.default_transition` | `cut` |
| `render_settings.crop_mode` | `center_crop` |
| `render_settings.keep_original_audio` | `false` |
| `render_settings.original_audio_volume` | `0.0` |
| `timing.min_speed` | `0.75` |
| `timing.max_speed` | `1.25` |
| `timing.time_tolerance` | `0.01` |

Ghi chú:

* `render_settings` có thể được truyền từ config hoặc dùng default.
* Trong MVP, nên dùng `transition = cut` để giảm rủi ro lệch duration khi render.
* Nếu `keep_original_audio = false`, visual item nên có `volume = 0.0`.
* Nếu `keep_original_audio = true`, visual item nên có `volume = original_audio_volume`.

## 5. Output

Stage này tạo output chính:

```text
data/intermediate/timeline.json
```

Stage này có thể tạo output phụ:

```text
data/intermediate/timeline_planning_log.json
```

`timeline.json` là file trung tâm cho Review UI và Renderer. File này phải được tạo ngay cả khi một số segment cần review, miễn là dữ liệu đủ để pipeline tiếp tục.

Nếu lỗi nghiêm trọng khiến timeline không thể dùng được, module phải dừng và không tạo timeline giả.

## 6. Data Contract cho `timeline.json`

### 6.1. Cấu trúc top-level

`timeline.json` phải có cấu trúc:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "audio_id": "audio_01",
  "created_at": "2026-06-11T10:25:00Z",
  "updated_at": "2026-06-11T10:25:00Z",
  "render_settings": {},
  "items": []
}
```

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `schema_version` | string | Version schema |
| `project_id` | string | ID project |
| `audio_id` | string | ID audio thuyết minh |
| `created_at` | string | Thời điểm tạo file |
| `updated_at` | string | Thời điểm cập nhật cuối |
| `render_settings` | object | Cấu hình render |
| `items` | array[object] | Danh sách timeline segment |

Quy tắc:

* `audio_id` lấy từ `media_metadata.audio.audio_id`.
* `created_at` và `updated_at` dùng ISO 8601 UTC.
* Khi Timeline Planner tạo lần đầu, `created_at` và `updated_at` có thể giống nhau.
* Review UI có thể cập nhật `updated_at` sau khi người dùng chỉnh sửa.

### 6.2. Render settings

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `width` | integer | Chiều rộng video output |
| `height` | integer | Chiều cao video output |
| `fps` | number | FPS output |
| `format` | string | Định dạng output |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `default_transition` | string | Transition mặc định |
| `crop_mode` | string | Cách scale/crop |
| `keep_original_audio` | boolean | Có giữ audio gốc của video không |
| `original_audio_volume` | number | Âm lượng audio gốc nếu giữ |

Allowed `format`:

```text
mp4
```

Allowed `default_transition`:

```text
cut
fade
crossfade
```

Allowed `crop_mode`:

```text
fit
fill
center_crop
blur_background
```

### 6.3. Timeline segment item

Mỗi item trong `items` tương ứng với một audio segment.

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `segment_id` | string | ID audio segment |
| `audio_start` | number | Bắt đầu audio segment |
| `audio_end` | number | Kết thúc audio segment |
| `duration` | number | Thời lượng segment |
| `text` | string | Transcript |
| `confidence` | string | Confidence của lựa chọn hình |
| `score` | number/null | Điểm tổng hợp từ selected candidate |
| `visual_items` | array[object] | Danh sách clip hình cho segment |
| `candidates_ref` | string/null | Tham chiếu candidate set |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `needs_review` | boolean | Có cần người dùng kiểm tra không |
| `fallback_used` | boolean | Có dùng fallback không |
| `user_edited` | boolean | Người dùng đã chỉnh chưa |
| `notes` | string | Ghi chú |

Quy tắc:

* `segment_id` phải tồn tại trong `audio_segments.json`.
* `audio_start` lấy từ `audio_segments.items[].start`.
* `audio_end` lấy từ `audio_segments.items[].end`.
* `duration` lấy từ `audio_segments.items[].duration`.
* `text` lấy từ `audio_segments.items[].text`.
* `confidence` ưu tiên lấy từ matching candidate set, sau đó có thể bị hạ nếu Timeline Planner phải fallback.
* `score` lấy từ selected candidate `final_score`; nếu không có visual item thì dùng `null`.
* `candidates_ref` là `candidate_set_id`, ví dụ `candidates_a001`.
* `user_edited` luôn là `false` khi Timeline Planner tạo lần đầu.

### 6.4. Visual item

Mỗi visual item mô tả một đoạn video được đặt lên timeline.

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `timeline_item_id` | string | ID item trên timeline |
| `clip_id` | string | Clip được dùng |
| `video_id` | string | Video nguồn |
| `source_path` | string | Đường dẫn video nguồn đã chuẩn hóa |
| `clip_start` | number | Bắt đầu cắt trong video nguồn |
| `clip_end` | number | Kết thúc cắt trong video nguồn |
| `timeline_start` | number | Vị trí bắt đầu trên timeline output |
| `timeline_end` | number | Vị trí kết thúc trên timeline output |
| `speed` | number | Tốc độ phát |
| `transition` | string | Kiểu transition |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `effect` | string/null | Hiệu ứng đơn giản nếu có |
| `crop_mode` | string/null | Override crop mode |
| `volume` | number/null | Âm lượng audio gốc của clip |
| `source_candidate_rank` | integer/null | Clip này lấy từ rank nào trong top-k |
| `locked` | boolean | Người dùng khóa không cho tự động đổi |
| `notes` | string | Ghi chú |

Allowed `speed` trong MVP:

```text
0.75 đến 1.25
```

Allowed `transition`:

```text
cut
fade
crossfade
```

Allowed `effect` trong MVP:

```text
null
none
```

Quy tắc:

* `clip_id` phải tồn tại trong `clip_metadata.json`.
* `video_id` phải khớp với clip trong `clip_metadata.json`.
* `source_path` ưu tiên lấy từ `clip_metadata.items[].source_path`.
* Nếu clip không có `source_path`, lấy từ `media_metadata.videos[].normalized_path` theo `video_id`.
* `clip_start` và `clip_end` là timestamp trong video nguồn đã chuẩn hóa.
* `timeline_start` và `timeline_end` là timestamp trong output video.
* `timeline_end > timeline_start`.
* `clip_end > clip_start`.
* `speed` phải nằm trong khoảng cho phép.
* `locked` luôn là `false` khi Timeline Planner tạo lần đầu.

## 7. Quy tắc ID

Timeline Planner phải tạo ID ổn định và dễ map.

### 7.1. Timeline item ID

Định dạng đề xuất:

```text
t{segment_index_3_digits}_i{visual_index_2_digits}
```

Ví dụ:

```text
t001_i01
t001_i02
t002_i01
```

Trong đó:

* `segment_index_3_digits` là thứ tự audio segment sau khi sort theo `start`, bắt đầu từ `001`.
* `visual_index_2_digits` là thứ tự visual item trong segment, bắt đầu từ `01`.

Quy tắc:

* Nếu input không đổi và thứ tự audio segment không đổi, `timeline_item_id` phải giữ ổn định.
* Không dùng random UUID trong MVP.
* Không dùng khoảng trắng trong ID.

### 7.2. Candidate reference

`candidates_ref` phải map về candidate set:

```text
matching_candidates.items[].candidate_set_id
→ timeline.items[].candidates_ref
```

Ví dụ:

```json
{
  "segment_id": "a001",
  "candidates_ref": "candidates_a001"
}
```

Nếu không có candidate set tương ứng:

* `candidates_ref = null`.
* `needs_review = true`.
* `fallback_used = true`.
* Ghi warning vào `timeline_planning_log.json`.

## 8. Quy trình xử lý

### 8.1. Bước 1 - Load và validate input

Module cần:

1. Load `media_metadata.json`.
2. Load `audio_segments.json`.
3. Load `clip_metadata.json`.
4. Load `matching_candidates.json`.
5. Kiểm tra `project_id`.
6. Kiểm tra required fields.
7. Tạo lookup map cho audio segments, clips, videos và candidate sets.

Lookup map đề xuất:

```text
segments_by_id[segment_id]
clips_by_id[clip_id]
videos_by_id[video_id]
candidate_sets_by_segment_id[audio_segment_id]
```

Nếu lỗi ở bước này là lỗi cấu trúc nghiêm trọng, module phải dừng.

### 8.2. Bước 2 - Chuẩn bị render settings

Module cần xác định `render_settings`.

Thứ tự ưu tiên:

1. Config người dùng truyền vào.
2. Config mặc định của module.
3. Thông tin suy ra từ video đầu tiên usable trong `media_metadata.json`.

Trong MVP, nên dùng default ổn định:

```json
{
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "format": "mp4",
  "default_transition": "cut",
  "crop_mode": "center_crop",
  "keep_original_audio": false,
  "original_audio_volume": 0.0
}
```

Nếu suy ra từ video nguồn:

* Chỉ dùng video có `status = ready` hoặc `status = warning`.
* Không dùng video `status = error`.
* Nếu nhiều video khác resolution/fps, MVP vẫn nên normalize output theo config cố định để Renderer đơn giản.

### 8.3. Bước 3 - Duyệt audio segment

Timeline Planner phải tạo một timeline item cho mỗi audio segment.

Quy tắc:

* Duyệt theo thứ tự `audio_segments.items[]` sau khi sort theo `start`.
* `timeline.items[].audio_start = segment.start`.
* `timeline.items[].audio_end = segment.end`.
* `timeline.items[].duration = segment.duration`.
* `timeline.items[].text = segment.text`.
* Không tự gộp hoặc tách audio segment ở Stage 6.

Nếu audio segment có lỗi nhẹ nhưng vẫn có thể biểu diễn:

* Vẫn tạo timeline item.
* Gán `needs_review = true`.
* Ghi `notes`.

Nếu audio segment thiếu `segment_id`, `start`, `end` hoặc `duration`:

* Đây là lỗi nghiêm trọng.
* Module phải dừng và yêu cầu sửa Stage 2.

### 8.4. Bước 4 - Chọn clip mặc định

Thứ tự chọn clip:

1. Dùng `selected_clip_id` từ candidate set nếu hợp lệ.
2. Nếu `selected_clip_id = null`, dùng candidate rank 1 nếu candidate hợp lệ.
3. Nếu rank 1 không hợp lệ, thử candidate rank tiếp theo.
4. Nếu không có candidate hợp lệ, dùng fallback clip từ `clip_metadata.json` nếu fallback được bật.
5. Nếu vẫn không có clip, tạo timeline item với `visual_items = []` và đánh dấu cần review.

Candidate hợp lệ khi:

* `clip_id` tồn tại trong `clip_metadata.json`.
* Clip không có `status = error`.
* Clip có `duration > 0`.
* Clip map được về video source hợp lệ.
* Source path tồn tại hoặc được ghi đúng để Renderer xử lý sau.

Trong MVP:

* Clip `usable` được chọn bình thường.
* Clip `low_quality` chỉ nên dùng nếu không có lựa chọn tốt hơn hoặc đã được Matching Engine chọn.
* Clip `too_short` không nên dùng làm lựa chọn đầu tiên, trừ khi cần lấp khoảng ngắn và vẫn fit được duration.
* Clip `error` không bao giờ được dùng.

### 8.5. Bước 5 - Tạo visual items

Với mỗi audio segment, Timeline Planner cần tạo một hoặc nhiều visual items để phủ duration của segment.

Mục tiêu:

```text
sum(visual timeline duration) ~= segment.duration
```

Sai số chấp nhận:

```text
0.01s
```

Timeline output của visual item đầu tiên bắt đầu tại `segment.start`. Visual item cuối cùng kết thúc tại `segment.end`.

Ví dụ:

```text
segment a001: 0.0s -> 5.2s
visual item 1: timeline_start 0.0, timeline_end 5.2
```

Nếu một segment có nhiều visual items:

```text
segment a002: 5.2s -> 12.0s
visual item 1: timeline_start 5.2, timeline_end 8.5
visual item 2: timeline_start 8.5, timeline_end 12.0
```

Các visual items trong cùng segment phải:

* Không overlap.
* Không có gap lớn hơn `time_tolerance`.
* Có thứ tự tăng dần theo `timeline_start`.
* Có `timeline_start` và `timeline_end` nằm trong `[audio_start, audio_end]`.

### 8.6. Bước 6 - Gán score, confidence và review flag

Với mỗi timeline item:

* `score` lấy từ `final_score` của candidate được chọn.
* `confidence` mặc định lấy từ candidate set.
* `fallback_used` mặc định lấy từ candidate set hoặc được Timeline Planner gán nếu phải fallback thêm.
* `needs_review` được tính từ confidence, fallback và chất lượng timeline.
* `user_edited = false`.

Quy tắc `needs_review`:

```text
needs_review = true nếu:
- confidence = low
- fallback_used = true
- không có visual item
- selected_clip_id không hợp lệ và phải chọn candidate khác
- dùng clip low_quality
- duration không fit sạch trong speed range
- phải reuse cùng clip quá gần nhau
- source path không tồn tại tại thời điểm tạo timeline
```

```text
needs_review = false nếu:
- confidence = high hoặc medium
- không fallback
- visual item hợp lệ
- duration fit sạch
- source path hợp lệ
```

Nếu Timeline Planner phát hiện vấn đề mới, có thể hạ confidence:

* `high` xuống `medium` nếu clip hợp lệ nhưng có cảnh báo nhỏ.
* `medium` xuống `low` nếu cần fallback hoặc source path không chắc chắn.
* Không nâng `low` lên `medium` hoặc `high` ở Stage 6.

## 9. Quy tắc xử lý duration

### 9.1. Công thức cơ bản

Với một visual item:

```text
source_duration = clip_end - clip_start
timeline_duration = timeline_end - timeline_start
speed = source_duration / timeline_duration
```

Ví dụ:

```text
source_duration = 4.0s
timeline_duration = 5.0s
speed = 0.8
```

Ý nghĩa:

* `speed = 1.0`: phát bình thường.
* `speed < 1.0`: phát chậm để kéo dài clip.
* `speed > 1.0`: phát nhanh để rút ngắn clip.

Trong MVP, `speed` phải nằm trong:

```text
0.75 <= speed <= 1.25
```

### 9.2. Clip dài hơn audio segment

Nếu clip đủ dài để phủ toàn bộ audio segment:

```text
clip.duration >= segment.duration
```

MVP xử lý:

* Dùng `speed = 1.0`.
* Cắt một đoạn có duration bằng `segment.duration`.
* `clip_start` mặc định là `clip.start` từ `clip_metadata.json`.
* `clip_end = clip_start + segment.duration`.

Ví dụ:

```text
segment.duration = 5.2
clip.start = 24.5
clip.end = 40.0

clip_start = 24.5
clip_end = 29.7
speed = 1.0
```

Nếu sau này có keyframe hoặc saliency score, có thể chọn đoạn đẹp hơn trong clip. MVP không bắt buộc.

### 9.3. Clip ngắn hơn audio segment nhưng có thể fit bằng speed

Nếu clip ngắn hơn segment:

```text
clip.duration < segment.duration
```

Timeline Planner thử fit bằng cách giảm speed:

```text
speed = clip.duration / segment.duration
```

Nếu:

```text
speed >= 0.75
```

thì có thể dùng một visual item duy nhất.

Ví dụ:

```text
segment.duration = 5.0
clip.duration = 4.0
speed = 4.0 / 5.0 = 0.8
```

Kết quả:

* `clip_start = clip.start`.
* `clip_end = clip.end`.
* `timeline_start = segment.start`.
* `timeline_end = segment.end`.
* `speed = 0.8`.

Nếu speed quá gần ngưỡng, có thể gán `needs_review = true` để người dùng kiểm tra.

### 9.4. Clip quá ngắn để fit bằng speed

Nếu:

```text
clip.duration / segment.duration < 0.75
```

thì không nên kéo giãn clip đó quá mức.

MVP xử lý theo thứ tự:

1. Dùng clip được chọn cho phần đầu segment.
2. Lấy candidate tiếp theo để phủ phần còn lại.
3. Nếu candidate tiếp theo cũng không đủ, tiếp tục lấy candidate rank tiếp theo.
4. Nếu hết candidate, dùng fallback clip nếu được bật.
5. Nếu vẫn không đủ, để phần còn lại thiếu visual hoặc dùng clip tốt nhất với `needs_review = true`.

Khuyến nghị cho MVP:

* Ưu tiên tạo nhiều visual items hơn là giảm speed dưới `0.75`.
* Không loop cùng một đoạn clip nhiều lần trong cùng segment, trừ khi đã đánh dấu fallback.
* Nếu buộc phải reuse clip, ghi `notes`.

### 9.5. Clip quá dài nhưng muốn dùng nhiều phần

Trong MVP, một audio segment chỉ cần dùng một phần của clip dài.

Không cần tự chia clip dài thành nhiều visual items nếu không có lý do rõ ràng.

Trường hợp có thể chia:

* Segment rất dài.
* Candidate rank 1 có nhiều đoạn hình khác nhau nhưng cùng `clip_id`.
* Muốn tránh một shot quá dài gây nhàm chán.

Nếu chưa có rule rõ, không nên tự thêm logic này vào MVP vì dễ làm timeline khó debug.

### 9.6. Transition và duration

Trong MVP:

* `transition = cut` là mặc định.
* `fade` và `crossfade` được phép theo Data Contract, nhưng Renderer phải thống nhất cách tính duration.

Để tránh lệch thời gian:

* Timeline Planner không trừ duration cho transition trong MVP.
* `timeline_start` và `timeline_end` vẫn biểu diễn vị trí tuyệt đối của visual item.
* Renderer chịu trách nhiệm áp dụng transition mà không làm thay đổi tổng duration output.

Nếu dùng `crossfade` thật sự làm overlap clip:

* Cần update rule ở cả Timeline Planner và Renderer.
* Không tự bật trong MVP nếu Renderer chưa hỗ trợ.

## 10. Quy tắc fallback

### 10.1. Khi nào cần fallback

Fallback được dùng khi:

* Candidate set không tồn tại.
* Candidate set có `selected_clip_id = null`.
* Candidate được chọn không tồn tại trong `clip_metadata.json`.
* Candidate được chọn có `status = error`.
* Candidate được chọn không map được source path.
* Clip được chọn quá ngắn và không đủ candidate khác để phủ segment.
* Matching Engine đã đánh dấu `fallback_used = true`.

### 10.2. Thứ tự fallback

Thứ tự fallback đề xuất:

1. Candidate rank tiếp theo trong cùng candidate set.
2. Clip `usable` có `quality_score` cao trong cùng video với candidate tốt nhất.
3. Clip `usable` có `quality_score` cao trong toàn bộ `clip_metadata.json`.
4. Clip `low_quality` nếu `allow_low_quality = true`.
5. Không chọn clip, để `visual_items = []`.

Mỗi lần fallback phải ghi rõ trong `notes` hoặc `timeline_planning_log.json`.

### 10.3. Timeline item không có visual item

Nếu không tìm được clip nào hợp lệ, Timeline Planner vẫn nên tạo timeline item:

```json
{
  "segment_id": "a003",
  "audio_start": 10.4,
  "audio_end": 14.0,
  "duration": 3.6,
  "text": "Đoạn này chưa tìm được hình phù hợp.",
  "confidence": "low",
  "score": null,
  "needs_review": true,
  "fallback_used": true,
  "user_edited": false,
  "candidates_ref": null,
  "visual_items": [],
  "notes": "No valid visual candidate found."
}
```

Lý do:

* UI vẫn hiển thị được audio segment cần xử lý.
* Người dùng có thể chọn clip thủ công.
* Evaluation biết segment nào bị thiếu hình.

Renderer có thể từ chối render nếu còn item không có visual item, hoặc render placeholder nếu được cấu hình riêng. Quyết định này thuộc Renderer, không thuộc Timeline Planner.

## 11. Quy tắc source path và audio gốc

### 11.1. Source path

`visual_items[].source_path` phải là path video nguồn đã chuẩn hóa.

Thứ tự lấy path:

1. `clip_metadata.items[].source_path` nếu có.
2. `media_metadata.videos[].normalized_path` theo `video_id`.

Không dùng:

* `original_path` nếu đã có `normalized_path`.
* Path tuyệt đối của máy cá nhân.
* Path tới keyframe image.

Nếu source path không tồn tại:

* Vẫn có thể ghi path nếu path đúng theo contract nhưng file chưa được mount trong môi trường test.
* Gán `needs_review = true`.
* Ghi warning vào log.

Nếu source path không xác định được:

* Không tạo visual item đó.
* Thử fallback.

### 11.2. Audio gốc của video

Trong MVP:

* Voice-over là audio chính.
* Renderer luôn dùng audio thuyết minh từ `media_metadata.audio.normalized_path`.
* Audio gốc của video chỉ dùng nếu `render_settings.keep_original_audio = true`.

Quy tắc gán `volume`:

```text
keep_original_audio = false
→ visual_items[].volume = 0.0

keep_original_audio = true
→ visual_items[].volume = original_audio_volume
```

Nếu video không có audio gốc:

* Visual item vẫn hợp lệ.
* `volume` có thể là `0.0` hoặc `null`.
* Không cần đánh dấu warning chỉ vì video không có audio gốc.

## 12. Output phụ `timeline_planning_log.json`

Log debug; khuyến nghị có khi tích hợp.

Đường dẫn đề xuất:

```text
data/intermediate/timeline_planning_log.json
```

Nội dung đề xuất:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:25:00Z",
  "summary": {
    "segments_total": 12,
    "segments_with_visual": 11,
    "segments_needing_review": 3,
    "fallback_count": 2,
    "empty_visual_count": 1
  },
  "items": [
    {
      "segment_id": "a001",
      "candidate_set_id": "candidates_a001",
      "selected_clip_id": "v01_c003",
      "visual_item_count": 1,
      "decision": "selected_clip_used",
      "warnings": []
    }
  ]
}
```

Log nên ghi:

* Segment nào dùng selected clip.
* Segment nào phải dùng candidate rank khác.
* Segment nào dùng fallback ngoài candidate set.
* Segment nào không có visual item.
* Segment nào bị hạ confidence.
* Segment nào dùng nhiều visual items.
* Source path nào không tồn tại.
* Lý do `needs_review = true`.

Không nên đưa vector embedding, transcript dài hoặc dữ liệu nặng vào log.

## 13. Ví dụ `timeline.json`

**Mẫu chuẩn:** `docs/samples/timeline_sample.json`. Segment `a003` minh họa một audio segment với nhiều visual items.

```json
{
  "segment_id": "a003",
  "audio_start": 10.8,
  "audio_end": 16.0,
  "duration": 5.2,
  "text": "Khach tham quan di chuyen sang khu trai nghiem tiep theo.",
  "confidence": "low",
  "score": 0.63,
  "candidates_ref": "candidates_a003",
  "visual_items": [
    {
      "timeline_item_id": "t003_i01",
      "clip_id": "v01_c005",
      "clip_start": 55.0,
      "clip_end": 57.6,
      "timeline_start": 10.8,
      "timeline_end": 13.4,
      "speed": 1.0,
      "source_candidate_rank": 1
    },
    {
      "timeline_item_id": "t003_i02",
      "clip_id": "v02_c002",
      "clip_start": 20.0,
      "clip_end": 22.6,
      "timeline_start": 13.4,
      "timeline_end": 16.0,
      "speed": 1.0,
      "source_candidate_rank": 2
    }
  ]
}
```

Quy tắc bắt buộc khi tạo timeline:

* `text` copy chính xác từ `audio_segments.json` (cùng `segment_id`).
* Tổng `timeline_end - timeline_start` của các visual item trong segment = `duration` segment.
* `(clip_end - clip_start) / speed` = `timeline_end - timeline_start` cho từng visual item.

## 14. Quan hệ với các module khác

### 14.1. Với Audio Analyzer

Timeline Planner dùng:

* `segment_id`
* `start`
* `end`
* `duration`
* `text`

Timeline Planner không sửa transcript và không chia lại segment.

Nếu muốn chỉnh transcript hoặc segment, phải xử lý ở Stage 2 hoặc qua Review UI với rule riêng.

### 14.2. Với Video Analyzer

Timeline Planner dùng:

* `clip_id`
* `video_id`
* `source_path`
* `start`
* `end`
* `duration`
* `quality_score`
* `status`

Timeline Planner không tạo clip mới ngoài danh sách trong `clip_metadata.json`.

Nếu clip quá dài, Stage 6 có thể chọn một subrange trong clip bằng `clip_start` và `clip_end`, nhưng `clip_start` và `clip_end` vẫn phải nằm trong range của clip gốc.

### 14.3. Với Matching Engine

Timeline Planner dùng:

* `candidate_set_id`
* `audio_segment_id`
* `selected_clip_id`
* `candidates[].clip_id`
* `candidates[].rank`
* `candidates[].final_score`
* `confidence`
* `fallback_used`

Timeline Planner phải ưu tiên `selected_clip_id` nếu hợp lệ.

Nếu phải chọn khác `selected_clip_id`, phải:

* Ghi log.
* Đánh dấu `needs_review = true`.
* Có thể giữ `candidates_ref` để UI hiển thị top-k gốc.

### 14.4. Với Review UI

Review UI đọc `timeline.json` để hiển thị bản dựng ban đầu.

UI cần dùng:

* `timeline.items[]` để hiển thị theo audio segment.
* `visual_items[]` để hiển thị clip đã chọn.
* `candidates_ref` để mở danh sách top-k từ `matching_candidates.json`.
* `needs_review` để highlight segment cần người dùng kiểm tra.
* `locked` để giữ clip người dùng đã khóa sau khi chỉnh.

Timeline Planner phải tạo timeline đủ rõ để UI không cần suy luận lại matching.

### 14.5. Với Renderer

Renderer đọc `timeline.json` để render video.

Renderer cần dùng:

* `render_settings`
* `audio_id`
* `visual_items[].source_path`
* `visual_items[].clip_start`
* `visual_items[].clip_end`
* `visual_items[].timeline_start`
* `visual_items[].timeline_end`
* `visual_items[].speed`
* `visual_items[].transition`
* `visual_items[].crop_mode`
* `visual_items[].volume`

Renderer không đọc `matching_candidates.json` để quyết định clip. Nếu timeline sai, Renderer nên báo lỗi timeline, không tự sửa logic matching.

### 14.6. Với Evaluation

Evaluation có thể dùng `timeline.json` để đo:

* Segment nào có visual item.
* Segment nào dùng fallback.
* Segment nào cần review.
* Score trung bình của selected clips.
* Tỷ lệ segment có confidence cao.
* Tỷ lệ timeline coverage.

Timeline Planner nên giữ `score`, `confidence`, `fallback_used` và `candidates_ref` để Evaluation truy vết quyết định.

## 15. Điều kiện handoff sang Review UI và Renderer

Stage 6 được phép bàn giao cho Review UI khi:

* `timeline.json` parse được.
* `project_id` đúng.
* `audio_id` đúng.
* Có `render_settings` required fields.
* Có một timeline item cho mỗi audio segment.
* Mỗi item có `segment_id`, `audio_start`, `audio_end`, `duration`, `text`.
* `needs_review` được gán rõ cho các item có vấn đề.
* `candidates_ref` map được về `matching_candidates.json` nếu có candidate set.

Stage 6 được phép bàn giao cho Renderer khi:

* Tất cả điều kiện cho Review UI đều đạt.
* Mỗi item cần render có ít nhất một visual item.
* Mỗi visual item có đủ required fields.
* `source_path` tồn tại hoặc môi trường render có thể resolve được path.
* `clip_start`, `clip_end` hợp lệ.
* `timeline_start`, `timeline_end` liên tục và không overlap sai.
* `speed` nằm trong khoảng cho phép.
* `transition` thuộc danh sách cho phép.
* Tổng timeline gần bằng duration audio chính.

Nếu còn item có `visual_items = []`, UI vẫn có thể mở, nhưng Renderer có thể chưa render được bản cuối. Trạng thái này phải được thể hiện bằng `needs_review = true`.

## 16. Ràng buộc kỹ thuật

### 16.1. Không thay đổi schema hiện hành

Timeline Planner phải xuất `timeline.json` theo Data Contract hiện tại.

Không tự thêm required field mới vào `timeline.json`. Nếu cần metadata bổ sung, ưu tiên:

* Dùng field optional `notes`.
* Ghi vào `timeline_planning_log.json`.
* Đề xuất thay đổi Data Contract riêng nếu thật sự cần.

### 16.2. Không dùng path tuyệt đối

Path trong timeline phải là path tương đối.

Ví dụ đúng:

```json
"source_path": "data/normalized/video_01.mp4"
```

Ví dụ không nên dùng:

```json
"source_path": "/Users/name/project/data/normalized/video_01.mp4"
```

### 16.3. Không tạo visual item từ keyframe

Keyframe chỉ phục vụ phân tích và matching.

Timeline visual item phải trỏ về video clip, không trỏ về ảnh keyframe.

Sai:

```json
"source_path": "data/intermediate/keyframes/v01_c003_k01.jpg"
```

Đúng:

```json
"source_path": "data/normalized/video_01.mp4"
```

### 16.4. Không tự ý bỏ audio segment

Mỗi audio segment phải có một timeline item.

Nếu không có visual phù hợp:

* Vẫn tạo item.
* `visual_items = []`.
* `needs_review = true`.
* `confidence = low`.

Không bỏ qua segment vì điều đó làm UI và Evaluation khó phát hiện thiếu sót.

### 16.5. Sai số thời gian

Tất cả thời gian dùng giây.

Sai số chấp nhận khi so duration:

```text
0.01s
```

Module nên round số thời gian ở mức hợp lý, ví dụ 3 chữ số thập phân.

Không nên round quá thô vì có thể làm lệch render.

## 17. Re-run behavior

Nếu chạy lại Timeline Planner với cùng `project_id`:

* Nếu không có `--overwrite` và `timeline.json` đã tồn tại, module nên dừng an toàn hoặc yêu cầu output path khác.
* Nếu có `--overwrite`, module được phép ghi đè `timeline.json` do Timeline Planner tạo trước đó.
* Nếu timeline đã được Review UI chỉnh sửa, không được ghi đè im lặng.
* Có thể phát hiện timeline đã được chỉnh bằng `user_edited = true` hoặc metadata/log bên ngoài.
* Nếu input và config không đổi, `timeline_item_id` phải giữ ổn định.
* Nếu thứ tự audio segment không đổi, thứ tự `items` phải giữ ổn định.

Khuyến nghị:

* Timeline Planner chỉ tạo bản draft ban đầu.
* Sau khi Review UI đã chỉnh, nên lưu file mới hoặc yêu cầu xác nhận trước khi overwrite.
* Không tự merge timeline cũ và timeline mới trong MVP nếu chưa có rule rõ ràng.

## 18. Cấu trúc code đề xuất

Module nên đặt trong:

```text
timeline_planner/
```

Cấu trúc tham khảo:

```text
timeline_planner/
  __init__.py
  planner.py
  duration_fit.py
  fallback.py
  validators.py
  io.py
  cli.py
  tests/
```

Gợi ý trách nhiệm:

* `io.py`: đọc/ghi JSON.
* `validators.py`: validate schema, project_id, mapping.
* `planner.py`: orchestration chính.
* `duration_fit.py`: tính clip_start, clip_end, speed, multi visual items.
* `fallback.py`: chọn fallback clip.
* `cli.py`: entrypoint chạy module.
* `tests/`: unit tests và sample integration tests.

Không bắt buộc phải đúng cấu trúc này, nhưng module cần tách rõ phần validate, planning và IO để dễ test.

## 19. CLI đề xuất

CLI tối thiểu:

```bash
python -m timeline_planner.cli \
  --project-id demo_01 \
  --media-metadata data/intermediate/media_metadata.json \
  --audio-segments data/intermediate/audio_segments.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --matching-candidates data/intermediate/matching_candidates.json \
  --output data/intermediate/timeline.json
```

Tham số nên có:

| Tham số | Ý nghĩa |
| ------- | ------- |
| `--project-id` | Project ID cần xử lý |
| `--media-metadata` | Path tới `media_metadata.json` |
| `--audio-segments` | Path tới `audio_segments.json` |
| `--clip-metadata` | Path tới `clip_metadata.json` |
| `--matching-candidates` | Path tới `matching_candidates.json` |
| `--output` | Path output `timeline.json` |
| `--log-output` | Path output log phụ |
| `--width` | Output width |
| `--height` | Output height |
| `--fps` | Output fps |
| `--transition` | Transition mặc định |
| `--crop-mode` | Crop mode mặc định |
| `--keep-original-audio` | Có giữ audio gốc không |
| `--original-audio-volume` | Volume audio gốc |
| `--overwrite` | Cho phép ghi đè output |

CLI phải fail rõ ràng nếu:

* File input không tồn tại.
* JSON lỗi format.
* `project_id` không khớp.
* Output đã tồn tại nhưng không có `--overwrite`.
* `render_settings` có giá trị không hợp lệ.

## 20. Test cases bắt buộc

### 20.1. Test happy path một segment một clip

Input:

* Một audio segment 5 giây.
* Một candidate selected clip dài hơn 5 giây.

Kỳ vọng:

* Tạo được `timeline.json`.
* Có một timeline item.
* Có một visual item.
* `speed = 1.0`.
* `clip_end - clip_start = 5.0`.
* `timeline_end - timeline_start = 5.0`.

### 20.2. Test clip ngắn nhưng fit bằng speed

Input:

* Segment 5 giây.
* Clip 4 giây.

Kỳ vọng:

* Dùng một visual item.
* `speed = 0.8`.
* `needs_review` tùy ngưỡng config nhưng không fail.
* `speed` nằm trong `[0.75, 1.25]`.

### 20.3. Test clip quá ngắn cần nhiều visual items

Input:

* Segment 8 giây.
* Candidate rank 1 dài 3 giây.
* Candidate rank 2 dài 5 giây.

Kỳ vọng:

* Tạo hai visual items.
* Visual items liên tục trên timeline.
* Tổng duration bằng 8 giây trong sai số cho phép.
* `source_candidate_rank` lần lượt là 1 và 2.

### 20.4. Test selected_clip_id không hợp lệ

Input:

* Candidate set có `selected_clip_id` không tồn tại trong `clip_metadata.json`.
* Candidate rank 1 hợp lệ.

Kỳ vọng:

* Module chọn candidate hợp lệ tiếp theo.
* `needs_review = true`.
* Log ghi rõ selected clip không hợp lệ.

### 20.5. Test không có candidate hợp lệ

Input:

* Một segment không có candidate hợp lệ.
* Fallback bị tắt hoặc không có clip fallback.

Kỳ vọng:

* Vẫn tạo timeline item.
* `visual_items = []`.
* `confidence = low`.
* `score = null`.
* `needs_review = true`.
* `fallback_used = true`.

### 20.6. Test fallback clip

Input:

* Candidate set rỗng.
* Có clip usable trong `clip_metadata.json`.
* Fallback bật.

Kỳ vọng:

* Timeline Planner dùng fallback clip.
* `fallback_used = true`.
* `confidence = low`.
* `source_candidate_rank = null`.
* Log ghi rõ fallback source.

### 20.7. Test clip error

Input:

* Candidate selected clip có `status = error`.

Kỳ vọng:

* Không dùng clip đó.
* Thử candidate khác hoặc fallback.
* Nếu không có clip khác, `visual_items = []`.
* `needs_review = true`.

### 20.8. Test source path

Input:

* Clip thiếu `source_path`.
* `media_metadata.videos[].normalized_path` có path hợp lệ.

Kỳ vọng:

* Visual item dùng `normalized_path`.
* Không dùng `original_path`.

### 20.9. Test project_id không khớp

Input:

* Một trong bốn file có `project_id` khác.

Kỳ vọng:

* Module dừng.
* Không tạo timeline giả.
* Báo lỗi rõ ràng.

### 20.10. Test render settings không hợp lệ

Input:

* `format = mov` hoặc `transition = dissolve`.

Kỳ vọng:

* Module dừng hoặc fallback về default theo config rõ ràng.
* Không xuất giá trị ngoài allowed list vào `timeline.json`.

### 20.11. Test timeline continuity

Input:

* Nhiều audio segments liên tiếp.

Kỳ vọng:

* `timeline.items[].audio_start/audio_end` khớp với audio segments.
* Visual items không overlap sai.
* Tổng timeline gần bằng duration audio.

### 20.12. Test chạy lại module

Kỳ vọng:

* Nếu output tồn tại và không có `--overwrite`, module dừng an toàn.
* Nếu có `--overwrite`, module ghi đè.
* Nếu input không đổi, `timeline_item_id` giữ ổn định.
* Nếu timeline cũ có `user_edited = true`, module không ghi đè im lặng.

## 21. Tiêu chí nghiệm thu

Module Timeline Planner được xem là đạt yêu cầu MVP khi:

1. Đọc được `media_metadata.json`.
2. Đọc được `audio_segments.json`.
3. Đọc được `clip_metadata.json`.
4. Đọc được `matching_candidates.json`.
5. Validate được `project_id` khớp giữa các file.
6. Tạo được một timeline item cho mỗi audio segment.
7. Giữ đúng `segment_id`, `audio_start`, `audio_end`, `duration`, `text`.
8. Ưu tiên dùng `selected_clip_id` từ Matching Engine nếu hợp lệ.
9. Fallback sang candidate khác khi selected clip không hợp lệ.
10. Không dùng clip có `status = error`.
11. Map được `clip_id` về `video_id`.
12. Map được `video_id` về source path chuẩn hóa.
13. Tạo được visual item có đủ required fields.
14. Tính đúng `clip_start` và `clip_end`.
15. Tính đúng `timeline_start` và `timeline_end`.
16. Tính `speed` trong `[0.75, 1.25]`.
17. Xử lý được clip dài hơn segment.
18. Xử lý được clip ngắn hơn segment bằng speed nếu hợp lệ.
19. Xử lý được clip quá ngắn bằng nhiều visual items hoặc fallback.
20. Gán `transition` thuộc allowed list.
21. Gán `crop_mode` hợp lệ.
22. Gán `volume` theo `keep_original_audio`.
23. Gán `score` từ selected candidate hoặc `null`.
24. Gán `confidence` thuộc `high`, `medium`, `low`.
25. Gán `needs_review` đúng rule.
26. Gán `fallback_used` đúng rule.
27. Gán `user_edited = false` khi tạo lần đầu.
28. Gán `candidates_ref` đúng `candidate_set_id`.
29. Tạo `timeline.json` đúng Data Contract.
30. Tạo `timeline_planning_log.json` để hỗ trợ debug.
31. Review UI có thể mở timeline và hiển thị item cần review.
32. Renderer có thể đọc timeline để render khi không còn item thiếu visual.
33. Có quy tắc rõ ràng khi chạy lại cùng `project_id`.

## 22. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 6 cần tự kiểm tra:

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc được media_metadata.json
[ ] Đọc được audio_segments.json
[ ] Đọc được clip_metadata.json
[ ] Đọc được matching_candidates.json
[ ] Kiểm tra project_id các file khớp nhau
[ ] Tạo lookup map theo segment_id
[ ] Tạo lookup map theo clip_id
[ ] Tạo lookup map theo video_id
[ ] Tạo lookup map theo audio_segment_id cho candidate set
[ ] Có một timeline item cho mỗi audio segment
[ ] Không tự bỏ audio segment
[ ] Dùng selected_clip_id nếu hợp lệ
[ ] Fallback sang candidate khác nếu selected clip lỗi
[ ] Không dùng clip status error
[ ] Xử lý clip low_quality bằng needs_review hoặc log
[ ] Xử lý clip dài hơn segment
[ ] Xử lý clip ngắn hơn segment bằng speed
[ ] Xử lý clip quá ngắn bằng nhiều visual items hoặc fallback
[ ] Speed luôn nằm trong [0.75, 1.25]
[ ] timeline_start/timeline_end liên tục trong từng segment
[ ] clip_start/clip_end nằm trong range clip
[ ] source_path là video normalized, không phải keyframe
[ ] Gán transition hợp lệ
[ ] Gán crop_mode hợp lệ
[ ] Gán volume theo keep_original_audio
[ ] Gán score từ final_score hoặc null
[ ] Gán confidence high/medium/low
[ ] Gán needs_review đúng rule
[ ] Gán fallback_used đúng rule
[ ] Gán user_edited = false
[ ] Gán locked = false cho visual item mới
[ ] Gán source_candidate_rank đúng rank hoặc null
[ ] Gán candidates_ref đúng candidate_set_id
[ ] Sinh timeline_item_id ổn định
[ ] Ghi đúng timeline.json
[ ] Ghi được timeline_planning_log.json
[ ] Không hard-code path cá nhân
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương khi chạy lại
[ ] Không ghi đè timeline đã user_edited im lặng
[ ] Có test với dữ liệu mẫu nhỏ
[ ] Output có thể đưa cho Review UI
[ ] Output có thể đưa cho Renderer nếu mọi item có visual
```

## 23. Ghi chú triển khai MVP

Trong MVP, Timeline Planner nên ưu tiên timeline đơn giản, ổn định và dễ render.

Thứ tự ưu tiên nên là:

1. Validate input và mapping thật chắc.
2. Tạo đủ timeline item theo audio segments.
3. Dùng `selected_clip_id` từ Matching Engine.
4. Tính timing đúng.
5. Dùng `transition = cut`.
6. Dùng `speed = 1.0` khi clip đủ dài.
7. Chỉ dùng speed khác `1.0` khi cần fit clip ngắn.
8. Dùng nhiều visual items khi clip quá ngắn.
9. Đánh dấu `needs_review` minh bạch.
10. Ghi log đủ để debug.

Không nên làm quá nhiều logic dựng phim phức tạp trong MVP. Timeline Planner cần tạo bản dựng đầu tiên có thể kiểm tra được, không cần thay thế vai trò của editor.

Nếu phải chọn giữa timeline đẹp hơn nhưng khó debug và timeline đơn giản nhưng đúng contract, MVP nên chọn timeline đơn giản. Sau khi Review UI và Renderer chạy ổn định, có thể cải thiện logic nhịp dựng, tránh lặp clip, chọn subrange đẹp hơn và transition nâng cao.
