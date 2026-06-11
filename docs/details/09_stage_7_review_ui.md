# 09. Stage 7 - Review UI

## 1. Mục tiêu của stage

Stage 7 - Review UI có nhiệm vụ cung cấp giao diện để người dùng kiểm tra và chỉnh sửa bản dựng ban đầu do Timeline Planner tạo ra.

UI không phải phần mềm dựng phim đầy đủ. UI trong MVP chỉ cần giúp người dùng xem từng audio segment, xem clip đang được chọn, xem top-k clip thay thế, đổi clip khi cần, chỉnh một số tham số cơ bản và lưu lại `timeline.json` đã cập nhật để Renderer sử dụng.

Mục tiêu chính:

* Đọc `timeline.json`.
* Đọc `matching_candidates.json`.
* Đọc `clip_metadata.json`.
* Đọc `audio_segments.json`.
* Đọc `media_metadata.json` nếu cần preview audio/video source.
* Hiển thị danh sách audio segments theo thứ tự timeline.
* Hiển thị transcript, score, confidence và trạng thái review.
* Hiển thị visual item hiện tại của từng segment.
* Hiển thị top-k candidate clip thay thế.
* Cho phép người dùng đổi clip cho segment.
* Cho phép chỉnh `clip_start`, `clip_end`, `speed`, `transition`, `crop_mode`, `volume` ở mức MVP.
* Cho phép đánh dấu `locked`.
* Cập nhật `user_edited = true` khi người dùng chỉnh.
* Cập nhật `updated_at` khi lưu.
* Validate timeline trước khi lưu.
* Xuất lại `timeline.json` đúng Data Contract đã chốt.

## 2. Vị trí trong pipeline

Stage này nằm sau Timeline Planner và trước Renderer:

```text
Timeline Planner
        |
        |-- timeline.json
        |
Matching Engine
        |
        |-- matching_candidates.json
        |
Video Analyzer
        |
        |-- clip_metadata.json
        |
Audio Analyzer
        |
        |-- audio_segments.json
        |
Input Processor
        |
        |-- media_metadata.json
        |-- normalized media files
        |
        v
Review UI
        |
        |-- updated timeline.json
        |-- review_ui_log.json
        |
        v
Renderer
```

Review UI là stage cho người dùng can thiệp vào bản dựng. Sau khi UI lưu timeline, Renderer chỉ cần đọc `timeline.json` đã cập nhật để xuất `final_video.mp4`.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Review UI cần xử lý các phần sau:

1. Load `timeline.json`.
2. Load `matching_candidates.json`.
3. Load `clip_metadata.json`.
4. Load `audio_segments.json`.
5. Load `media_metadata.json` nếu cần path audio/video.
6. Validate `project_id` giữa các file.
7. Hiển thị toàn bộ timeline items.
8. Highlight item có `needs_review = true`.
9. Highlight item có `confidence = low`.
10. Hiển thị clip hiện tại của segment.
11. Hiển thị top-k candidate dựa trên `candidates_ref`.
12. Cho phép đổi clip từ danh sách candidate.
13. Cho phép chỉnh tham số timeline được phép chỉnh.
14. Validate chỉnh sửa trước khi lưu.
15. Cập nhật `timeline.items[].user_edited`.
16. Cập nhật `visual_items[].locked` nếu người dùng khóa clip.
17. Cập nhật `updated_at`.
18. Lưu lại `timeline.json`.
19. Ghi log thao tác review nếu cần.

### 3.2. Stage này không làm

Review UI không chịu trách nhiệm cho các phần sau:

* Không chạy ASR.
* Không detect scene hoặc shot.
* Không tạo embedding.
* Không tính lại matching score.
* Không sửa `matching_candidates.json`.
* Không sửa `clip_metadata.json`.
* Không render `final_video.mp4`.
* Không tự chọn lại clip dựa trên model.
* Không thay đổi schema.
* Không chỉnh `audio_start`, `audio_end` nếu chưa có chức năng sửa audio segment.
* Không chỉnh file video/audio nguồn.

Nếu người dùng muốn đổi clip, UI chỉ cập nhật `timeline.json`. Matching Engine output vẫn được giữ nguyên để truy vết top-k ban đầu.

## 4. Input

### 4.1. Input chính

Review UI đọc:

```text
data/intermediate/timeline.json
data/intermediate/matching_candidates.json
data/intermediate/clip_metadata.json
data/intermediate/audio_segments.json
data/intermediate/media_metadata.json
```

Trong đó:

* `timeline.json` là bản dựng hiện tại.
* `matching_candidates.json` cung cấp top-k clip thay thế.
* `clip_metadata.json` cung cấp metadata của clip để preview và validate.
* `audio_segments.json` cung cấp transcript/timing gốc để đối chiếu.
* `media_metadata.json` cung cấp path audio thuyết minh và video đã chuẩn hóa.

### 4.2. Input media

UI có thể cần đọc media files:

```text
data/normalized/*.mp4
data/normalized/*.wav
```

Mục đích:

* Preview clip hiện tại.
* Preview candidate clip.
* Preview audio segment.
* Preview đoạn dựng đơn giản trong UI nếu có.

UI chỉ preview media. UI không xuất video cuối.

### 4.3. Điều kiện input hợp lệ

Các file JSON phải thỏa:

* Parse được JSON.
* Có `schema_version`.
* Có `project_id`.
* `project_id` giữa các file phải giống nhau.

`timeline.json` phải có:

* `audio_id`.
* `render_settings`.
* `items` không rỗng.
* Mỗi item có `segment_id`.
* Mỗi item có `audio_start`, `audio_end`, `duration`.
* Mỗi item có `visual_items`.

`matching_candidates.json` phải có:

* `items`.
* Mỗi candidate set có `candidate_set_id`.
* Mỗi candidate set có `audio_segment_id`.
* Mỗi candidate có `rank`, `clip_id`, `final_score`.

`clip_metadata.json` phải có:

* `items`.
* Mỗi clip có `clip_id`.
* Mỗi clip có `video_id`.
* Mỗi clip có `start`, `end`, `duration`.

`audio_segments.json` phải có:

* Segment tương ứng với `timeline.items[].segment_id`.
* Timing khớp với timeline trong sai số nhỏ.

`media_metadata.json` phải có:

* Audio chính nếu UI preview voice-over.
* Video source đã chuẩn hóa nếu clip thiếu `source_path`.

Nếu input có lỗi nhẹ:

* UI vẫn nên mở ở read-only mode nếu có thể.
* Hiển thị lỗi rõ segment nào hoặc file nào có vấn đề.
* Không cho lưu nếu việc lưu có thể làm timeline sai contract.

Nếu input lỗi nghiêm trọng:

* UI dừng load project.
* Hiển thị lỗi parse/validate.
* Không tạo timeline mới.

## 5. Output

### 5.1. Output chính

Review UI tạo output chính:

```text
data/intermediate/timeline.json
```

Đây là `timeline.json` đã được cập nhật sau khi người dùng chỉnh.

Renderer sẽ đọc file này để render video cuối.

### 5.2. Output phụ

Review UI có thể tạo output phụ:

```text
data/intermediate/review_ui_log.json
```

File này không thuộc Data Contract chính, nhưng hữu ích để debug ai đã chỉnh gì.

Ví dụ:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:40:00Z",
  "items": [
    {
      "timestamp": "2026-06-11T10:41:12Z",
      "action": "replace_clip",
      "segment_id": "a001",
      "before_clip_id": "v01_c003",
      "after_clip_id": "v02_c004",
      "source_candidate_rank": 2
    }
  ]
}
```

Log không nên thay thế `timeline.json`. Renderer không đọc log này.

## 6. Data Contract UI được phép chỉnh

Review UI chỉ được chỉnh các field đã được Data Contract cho phép.

### 6.1. Field UI được phép chỉnh trong timeline item

UI được phép chỉnh:

| Field | Ý nghĩa |
| ----- | ------- |
| `visual_items` | Clip/đoạn hình được chọn cho segment |
| `user_edited` | Đánh dấu người dùng đã chỉnh segment |
| `needs_review` | Có thể tắt nếu người dùng đã xác nhận hoặc bật nếu chỉnh còn vấn đề |
| `notes` | Ghi chú của người dùng hoặc UI |

UI không nên chỉnh:

| Field | Lý do |
| ----- | ---- |
| `segment_id` | ID dùng để map giữa các file |
| `audio_start` | Thuộc audio segment gốc |
| `audio_end` | Thuộc audio segment gốc |
| `duration` | Thuộc audio segment gốc |
| `text` | Transcript do Audio Analyzer tạo, trừ khi có mode sửa transcript riêng |
| `candidates_ref` | Dùng để map top-k candidate |
| `score` | Score do Matching Engine/Timeline Planner tạo |
| `confidence` | Có thể hiển thị, không nên tự nâng score/confidence bằng tay |

Ghi chú:

* Nếu người dùng xác nhận một segment có `confidence = low`, UI có thể đặt `needs_review = false`, nhưng không nên đổi `confidence` thành `high`.
* `confidence` phản ánh độ tin cậy của hệ thống, không phải quyết định cuối cùng của người dùng.

### 6.2. Field UI được phép chỉnh trong visual item

UI được phép chỉnh:

| Field | Ý nghĩa |
| ----- | ------- |
| `clip_id` | Khi người dùng đổi clip |
| `video_id` | Cập nhật theo clip mới |
| `source_path` | Cập nhật theo clip mới |
| `clip_start` | Chỉnh điểm bắt đầu cắt |
| `clip_end` | Chỉnh điểm kết thúc cắt |
| `speed` | Chỉnh tốc độ phát |
| `transition` | Chỉnh kiểu transition |
| `effect` | Chỉ `null` hoặc `none` trong MVP |
| `crop_mode` | Override crop mode |
| `volume` | Âm lượng audio gốc |
| `source_candidate_rank` | Rank nếu clip đến từ top-k |
| `locked` | Khóa lựa chọn của người dùng |
| `notes` | Ghi chú |

UI không nên chỉnh:

| Field | Lý do |
| ----- | ---- |
| `timeline_item_id` | ID ổn định do Timeline Planner tạo |
| `timeline_start` | Phụ thuộc audio segment và layout timeline |
| `timeline_end` | Phụ thuộc audio segment và layout timeline |

Trong MVP, khi đổi clip cho một segment có một visual item, UI nên giữ nguyên:

```text
timeline_start = audio_start
timeline_end = audio_end
```

Sau đó UI tính lại:

```text
clip_start
clip_end
speed
video_id
source_path
source_candidate_rank
```

### 6.3. Field top-level UI được phép chỉnh

UI được phép chỉnh:

| Field | Ý nghĩa |
| ----- | ------- |
| `updated_at` | Cập nhật khi lưu |
| `render_settings` | Chỉ các setting render cơ bản nếu UI có màn cấu hình |

UI không nên chỉnh:

| Field | Lý do |
| ----- | ---- |
| `schema_version` | Thuộc Data Contract |
| `project_id` | ID project |
| `audio_id` | ID audio chính |
| `created_at` | Thời điểm tạo timeline ban đầu |

Nếu UI hỗ trợ chỉnh `render_settings`, chỉ cho phép giá trị trong Data Contract:

```text
format: mp4
default_transition: cut, fade, crossfade
crop_mode: fit, fill, center_crop, blur_background
```

## 7. Luồng sử dụng chính

### 7.1. Mở project

Khi mở project, UI cần:

1. Load `timeline.json`.
2. Load các file phụ.
3. Validate mapping cơ bản.
4. Tạo danh sách segment.
5. Tự chọn segment đầu tiên cần review nếu có.
6. Nếu không có segment cần review, chọn segment đầu tiên.

Segment cần review là segment có:

```text
needs_review = true
confidence = low
fallback_used = true
visual_items = []
```

### 7.2. Review một segment

Khi người dùng chọn segment:

UI hiển thị:

* Transcript.
* Audio start/end/duration.
* Confidence.
* Score.
* Fallback status.
* Clip hiện tại.
* Preview clip hiện tại.
* Top-k candidates.
* Các control chỉnh cơ bản.
* Cảnh báo validation nếu có.

### 7.3. Đổi clip từ top-k

Khi người dùng chọn một candidate:

UI cần:

1. Kiểm tra candidate `clip_id` tồn tại trong `clip_metadata.json`.
2. Lấy `video_id`, `source_path`, `start`, `end`, `duration`.
3. Tính `clip_start`, `clip_end`, `speed` để fit segment.
4. Cập nhật visual item hiện tại hoặc tạo visual item mới nếu segment chưa có hình.
5. Gán `source_candidate_rank = candidate.rank`.
6. Gán `user_edited = true`.
7. Gán `locked = true` nếu người dùng chọn khóa clip.
8. Giữ nguyên `candidates_ref`.
9. Validate timeline item.

UI không sửa `matching_candidates.json`.

### 7.4. Chỉnh timing trong clip

Người dùng có thể chỉnh:

```text
clip_start
clip_end
```

UI cần đảm bảo:

* `clip_start >= clip_metadata.start`.
* `clip_end <= clip_metadata.end`.
* `clip_end > clip_start`.
* `speed` sau khi chỉnh vẫn nằm trong `[0.75, 1.25]`.

Công thức:

```text
source_duration = clip_end - clip_start
timeline_duration = timeline_end - timeline_start
speed = source_duration / timeline_duration
```

Nếu chỉnh timing làm speed vượt giới hạn:

* UI hiển thị warning.
* Không cho lưu ở trạng thái renderer-invalid, hoặc tự yêu cầu người dùng chỉnh lại.

### 7.5. Chỉnh speed

Người dùng có thể chỉnh `speed` trong khoảng:

```text
0.75 đến 1.25
```

Khi speed thay đổi, UI nên cập nhật `clip_end` theo:

```text
clip_end = clip_start + (timeline_duration * speed)
```

Sau đó validate:

* `clip_end <= clip_metadata.end`.
* `clip_end > clip_start`.

Nếu không đủ source duration:

* UI báo lỗi.
* Không lưu thay đổi đó.

### 7.6. Chỉnh transition, crop mode và volume

UI có thể cho chỉnh:

```text
transition: cut, fade, crossfade
crop_mode: fit, fill, center_crop, blur_background
volume: 0.0 đến 1.0
```

Trong MVP:

* `transition = cut` nên là default.
* Nếu Renderer chưa hỗ trợ `fade` hoặc `crossfade`, UI nên disable option đó.
* `effect` chỉ nên là `null` hoặc `none`.
* Nếu `render_settings.keep_original_audio = false`, volume nên giữ `0.0`.

### 7.7. Xác nhận segment đã review

UI nên có action đơn giản:

```text
Mark as reviewed
```

Khi người dùng xác nhận:

* `needs_review = false`.
* `user_edited = true`.
* `updated_at` sẽ được cập nhật khi save.

Không đổi:

* `confidence`.
* `score`.
* `candidates_ref`.

Lý do: người dùng xác nhận không làm score của hệ thống thay đổi.

### 7.8. Lưu timeline

Khi người dùng bấm Save:

UI cần:

1. Validate toàn bộ `timeline.json`.
2. Cập nhật `updated_at`.
3. Ghi `timeline.json`.
4. Ghi `review_ui_log.json` nếu có.
5. Hiển thị trạng thái save thành công hoặc lỗi.

Không nên ghi file liên tục sau mỗi phím gõ trong MVP. Nên dùng explicit Save để tránh làm hỏng timeline khi người dùng đang thử chỉnh.

## 8. Bố cục UI đề xuất

### 8.1. Layout tổng quan

MVP UI nên có 4 vùng chính:

```text
+---------------------------------------------------------------+
| Header: project_id, save status, render settings, Save button  |
+----------------------+----------------------+-----------------+
| Segment list         | Current preview      | Candidates      |
| - transcript short   | - video preview      | - rank/score    |
| - confidence         | - audio controls     | - reason        |
| - needs_review flag  | - current clip info  | - choose button |
+----------------------+----------------------+-----------------+
| Inspector: clip_start, clip_end, speed, transition, crop, lock |
+---------------------------------------------------------------+
```

### 8.2. Segment list

Mỗi segment trong danh sách nên hiển thị:

* `segment_id`.
* Transcript rút gọn.
* Time range.
* Confidence.
* Score nếu có.
* Badge `needs_review`.
* Badge `fallback_used`.
* Badge `edited` nếu `user_edited = true`.
* Badge `missing visual` nếu `visual_items = []`.

Sort mặc định:

```text
theo timeline order
```

Filter nên có:

* All.
* Needs review.
* Low confidence.
* Edited.
* Missing visual.

### 8.3. Current preview

Vùng preview hiện tại nên hiển thị:

* Video source của visual item đang chọn.
* Đoạn clip từ `clip_start` đến `clip_end`.
* Transcript/audio segment liên quan.
* Clip ID và video ID.
* Timeline time range.
* Warning nếu source path lỗi.

MVP có thể preview bằng HTML video/audio hoặc player local tương đương.

Không yêu cầu:

* Render preview chính xác toàn bộ transition.
* Composite nhiều visual items phức tạp.
* Export video từ UI.

### 8.4. Candidate list

Candidate list lấy từ:

```text
timeline.items[].candidates_ref
→ matching_candidates.items[].candidate_set_id
```

Mỗi candidate nên hiển thị:

* Rank.
* Clip ID.
* Final score.
* Semantic score nếu có.
* Visual quality score nếu có.
* Duration fit score nếu có.
* Reason nếu có.
* Preview thumbnail hoặc keyframe nếu có path.
* Button chọn clip.

Nếu candidate clip đang được dùng:

* Hiển thị trạng thái `selected`.

Nếu candidate không hợp lệ:

* Disable chọn.
* Hiển thị lý do, ví dụ clip missing, source missing, status error.

### 8.5. Inspector

Inspector hiển thị và cho chỉnh:

* `clip_start`.
* `clip_end`.
* `speed`.
* `transition`.
* `crop_mode`.
* `volume`.
* `locked`.
* `notes`.

Inspector phải hiển thị validation trực tiếp:

* Speed ngoài range.
* Clip end vượt range clip.
* Source path thiếu.
* Visual duration không khớp audio segment.

### 8.6. Render settings panel

Nếu UI có render settings panel, chỉ cần MVP:

* Width.
* Height.
* FPS.
* Format.
* Crop mode mặc định.
* Keep original audio.
* Original audio volume.

UI phải validate allowed values trước khi lưu.

Không cần hỗ trợ preset phức tạp trong MVP.

## 9. Quy tắc preview

### 9.1. Preview audio segment

UI có thể dùng audio chính:

```text
media_metadata.audio.normalized_path
```

Để preview audio segment:

```text
start = timeline.items[].audio_start
end = timeline.items[].audio_end
```

### 9.2. Preview visual item

UI dùng:

```text
visual_items[].source_path
visual_items[].clip_start
visual_items[].clip_end
visual_items[].speed
```

MVP có thể preview clip hiện tại bằng cách seek video tới `clip_start` và dừng ở `clip_end`.

Nếu player không hỗ trợ speed chính xác:

* Vẫn hiển thị speed value.
* Ghi rõ preview có thể không chính xác 100%.
* Không thay đổi timeline.

### 9.3. Preview candidate

Khi preview candidate:

* Không cập nhật timeline ngay.
* Chỉ khi người dùng bấm Choose/Apply mới cập nhật visual item.

Candidate preview nên dùng clip metadata:

```text
clip_metadata.items[].source_path
clip_metadata.items[].start
clip_metadata.items[].end
```

Nếu `source_path` không có trong clip metadata, resolve qua `media_metadata.videos[].normalized_path`.

### 9.4. Preview nhiều visual items

Trong MVP, nếu một segment có nhiều visual items:

* UI có thể hiển thị danh sách visual items.
* Người dùng chọn từng item để preview.
* Không bắt buộc preview liên tục toàn segment.

Nếu làm preview liên tục:

* Không được thay đổi timeline duration.
* Không tự merge visual items.

## 10. Quy tắc chỉnh clip

### 10.1. Segment có một visual item

Đây là case chính của MVP.

Khi đổi clip:

* Thay visual item hiện tại bằng clip mới.
* Giữ nguyên `timeline_item_id`.
* Giữ nguyên `timeline_start`.
* Giữ nguyên `timeline_end`.
* Cập nhật `clip_id`, `video_id`, `source_path`.
* Tính lại `clip_start`, `clip_end`, `speed`.
* Cập nhật `source_candidate_rank`.
* Set `locked` theo lựa chọn người dùng.
* Set `user_edited = true`.

### 10.2. Segment chưa có visual item

Nếu `visual_items = []`, khi người dùng chọn clip:

* Tạo visual item mới.
* `timeline_item_id` dùng format ổn định, ví dụ `t003_i01`.
* `timeline_start = audio_start`.
* `timeline_end = audio_end`.
* Tính `clip_start`, `clip_end`, `speed`.
* `source_candidate_rank` lấy từ candidate nếu có.
* `locked = true` nếu người dùng chọn khóa.
* `user_edited = true`.
* `needs_review = false` nếu visual item hợp lệ và người dùng xác nhận.

### 10.3. Segment có nhiều visual items

Trong MVP, UI có thể hỗ trợ tối thiểu:

* Hiển thị từng visual item.
* Cho chọn item đang chỉnh.
* Cho đổi clip của từng item.
* Không tự thay đổi ranh giới `timeline_start/timeline_end` nếu chưa có editor phức tạp.

Nếu người dùng muốn chuyển segment nhiều visual items thành một visual item:

* UI chỉ nên cho phép nếu clip mới đủ fit toàn segment.
* Khi đó có thể thay `visual_items` bằng một item duy nhất.
* Cần validate timeline sau khi thay.

### 10.4. Clip ngoài top-k

MVP không bắt buộc chọn clip ngoài top-k.

Nếu UI hỗ trợ chọn clip ngoài top-k:

* Clip phải tồn tại trong `clip_metadata.json`.
* `source_candidate_rank = null`.
* `notes` nên ghi `Selected outside top-k`.
* `user_edited = true`.
* `needs_review` tùy người dùng xác nhận.

Không được thêm candidate ngoài top-k vào `matching_candidates.json`.

## 11. Validation trước khi lưu

### 11.1. Validate top-level

Trước khi lưu, UI cần kiểm tra:

* `schema_version` tồn tại.
* `project_id` không đổi.
* `audio_id` không đổi.
* `created_at` không bị xóa.
* `updated_at` hợp lệ.
* `render_settings` hợp lệ.
* `items` không rỗng.

### 11.2. Validate timeline item

Mỗi timeline item phải thỏa:

* `segment_id` tồn tại trong `audio_segments.json`.
* `audio_start >= 0`.
* `audio_end > audio_start`.
* `duration = audio_end - audio_start` trong sai số cho phép.
* `confidence` thuộc `high`, `medium`, `low`.
* `visual_items` là array.
* `candidates_ref` là string hoặc `null`.

### 11.3. Validate visual item

Mỗi visual item phải thỏa:

* `timeline_item_id` không rỗng.
* `clip_id` tồn tại trong `clip_metadata.json`.
* `video_id` khớp với clip.
* `source_path` không rỗng.
* `clip_start >= clip_metadata.start`.
* `clip_end <= clip_metadata.end`.
* `clip_end > clip_start`.
* `timeline_start >= audio_start`.
* `timeline_end <= audio_end`.
* `timeline_end > timeline_start`.
* `speed` trong `[0.75, 1.25]`.
* `transition` thuộc `cut`, `fade`, `crossfade`.
* `effect` là `null` hoặc `none` trong MVP.
* `crop_mode` là `null` hoặc thuộc allowed list.

### 11.4. Validate timeline continuity

Trong từng segment:

* Visual items không overlap.
* Visual items không có gap lớn nếu segment được xem là renderer-ready.
* Tổng visual duration gần bằng `duration`.

Toàn timeline:

* Items giữ đúng thứ tự audio.
* Không thiếu segment.
* Không tạo duplicate `segment_id`.

### 11.5. Mức lỗi

UI nên phân lỗi thành ba mức:

| Mức | Ý nghĩa | Cho lưu không |
| --- | ------- | ------------- |
| `error` | Timeline sai contract hoặc Renderer chắc chắn lỗi | Không |
| `warning` | Timeline hợp lệ nhưng cần người dùng xem lại | Có |
| `info` | Thông tin phụ | Có |

Ví dụ `error`:

* `clip_id` không tồn tại.
* `speed = 1.6`.
* `clip_end <= clip_start`.
* `transition = dissolve`.

Ví dụ `warning`:

* `confidence = low`.
* `fallback_used = true`.
* `source path` chưa kiểm tra được trong môi trường hiện tại.
* Clip `low_quality`.

## 12. Save behavior

### 12.1. Save explicit

MVP nên dùng nút Save rõ ràng.

Quy trình:

1. Người dùng chỉnh.
2. UI giữ state trong memory.
3. Người dùng bấm Save.
4. UI validate toàn bộ timeline.
5. Nếu có error, UI không lưu.
6. Nếu chỉ có warning, UI cho lưu.
7. UI cập nhật `updated_at`.
8. UI ghi `timeline.json`.

### 12.2. Dirty state

UI cần biết timeline có thay đổi chưa.

Dirty state bật khi:

* Đổi clip.
* Chỉnh timing.
* Chỉnh speed.
* Chỉnh transition.
* Chỉnh crop mode.
* Chỉnh volume.
* Đổi locked.
* Đổi needs_review.
* Đổi notes.
* Đổi render settings.

Nếu người dùng rời trang khi dirty:

* UI phải cảnh báo chưa lưu.

### 12.3. Backup

Khuyến nghị khi lưu lần đầu trong phiên review:

```text
data/intermediate/timeline.before_review.json
```

File backup không thuộc Data Contract chính.

Mục đích:

* Có thể quay lại timeline ban đầu.
* Tránh mất bản Timeline Planner tạo ra.

Không bắt buộc MVP, nhưng nên có nếu thời gian cho phép.

### 12.4. Không ghi đè schema

Khi lưu, UI phải preserve các field không liên quan.

Ví dụ:

* Không xóa field optional mà UI không hiểu.
* Không sort lại object key theo cách gây khó diff nếu không cần.
* Không xóa `notes` cũ nếu người dùng không sửa.

## 13. State management

### 13.1. State cần có

UI nên quản lý các state chính:

```text
project
timeline
candidate_sets
clips_by_id
segments_by_id
videos_by_id
selected_segment_id
selected_visual_item_id
dirty
validation_errors
save_status
```

### 13.2. Derived data

Không nên lưu trùng dữ liệu nếu có thể derive.

Derived data:

* Candidate list của segment hiện tại.
* Clip metadata của visual item hiện tại.
* Segment review status.
* Timeline coverage status.
* Renderer readiness.

### 13.3. Update transaction

Mỗi thao tác chỉnh nên được xem như một transaction nhỏ.

Ví dụ đổi clip:

```text
replaceClip(segment_id, visual_item_id, new_clip_id)
```

Hàm này phải cập nhật đồng thời:

* `clip_id`
* `video_id`
* `source_path`
* `clip_start`
* `clip_end`
* `speed`
* `source_candidate_rank`
* `locked`
* `user_edited`
* validation state

Không nên cập nhật từng field rời rạc ở nhiều nơi vì dễ làm timeline inconsistent.

## 14. Component/module đề xuất

Nếu làm web UI, cấu trúc module đề xuất:

```text
review_ui/
  src/
    App.*
    data/
      loadProject.*
      saveTimeline.*
      validateTimeline.*
      resolveMediaPath.*
    timeline/
      timelineStore.*
      timelineEditing.*
      durationFit.*
    components/
      SegmentList.*
      SegmentDetail.*
      VideoPreview.*
      CandidateList.*
      TimelineInspector.*
      RenderSettingsPanel.*
      ValidationPanel.*
    types/
      timeline.*
      candidates.*
      clips.*
```

Nếu làm Python/FastAPI + frontend:

```text
review_ui/
  backend/
    app.py
    project_loader.py
    timeline_writer.py
    validators.py
  frontend/
    src/
```

Không bắt buộc đúng cấu trúc này. Nhưng cần tách rõ:

* Load/save data.
* Validate data.
* Logic chỉnh timeline.
* Component hiển thị.

## 15. API nội bộ đề xuất

Nếu UI cần backend local, API tối thiểu:

```text
GET  /api/project
GET  /api/media/video?path=...
GET  /api/media/audio?path=...
POST /api/timeline/validate
POST /api/timeline/save
```

### 15.1. `GET /api/project`

Trả về bundle dữ liệu:

```json
{
  "timeline": {},
  "matching_candidates": {},
  "clip_metadata": {},
  "audio_segments": {},
  "media_metadata": {}
}
```

### 15.2. `POST /api/timeline/validate`

Input:

```json
{
  "timeline": {}
}
```

Output:

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### 15.3. `POST /api/timeline/save`

Input:

```json
{
  "timeline": {}
}
```

Output:

```json
{
  "ok": true,
  "path": "data/intermediate/timeline.json",
  "updated_at": "2026-06-11T10:45:00Z"
}
```

Backend phải validate trước khi ghi file.

## 16. CLI/dev server đề xuất

Lệnh chạy UI tham khảo:

```bash
python -m review_ui.cli \
  --project-id demo_01 \
  --timeline data/intermediate/timeline.json \
  --matching-candidates data/intermediate/matching_candidates.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --audio-segments data/intermediate/audio_segments.json \
  --media-metadata data/intermediate/media_metadata.json \
  --host 127.0.0.1 \
  --port 7860
```

Tham số nên có:

| Tham số | Ý nghĩa |
| ------- | ------- |
| `--project-id` | Project ID cần review |
| `--timeline` | Path tới `timeline.json` |
| `--matching-candidates` | Path tới `matching_candidates.json` |
| `--clip-metadata` | Path tới `clip_metadata.json` |
| `--audio-segments` | Path tới `audio_segments.json` |
| `--media-metadata` | Path tới `media_metadata.json` |
| `--host` | Host dev server |
| `--port` | Port dev server |
| `--readonly` | Mở UI chỉ để xem, không cho save |
| `--backup-on-save` | Tạo backup trước khi save |

CLI phải fail rõ ràng nếu:

* File input không tồn tại.
* JSON lỗi format.
* `project_id` không khớp.
* Port đã bị chiếm.

## 17. Quan hệ với các module khác

### 17.1. Với Timeline Planner

Timeline Planner tạo `timeline.json` ban đầu.

Review UI đọc file này và chỉ sửa những field được phép.

UI không nên phá các quyết định quan trọng:

* Không đổi `segment_id`.
* Không đổi `audio_start/audio_end`.
* Không xóa `candidates_ref`.
* Không xóa toàn bộ visual item nếu không có hành động rõ ràng của người dùng.

### 17.2. Với Matching Engine

UI dùng `matching_candidates.json` để hiển thị top-k.

UI không sửa:

* `candidate_set_id`.
* `selected_clip_id`.
* `final_score`.
* `rank`.
* `reason`.

Khi người dùng chọn candidate khác, UI chỉ cập nhật `timeline.json`.

### 17.3. Với Video Analyzer

UI dùng `clip_metadata.json` để:

* Resolve clip.
* Preview source.
* Validate `clip_start/clip_end`.
* Hiển thị thông tin clip.

UI không tạo clip metadata mới trong MVP.

### 17.4. Với Input Processor

UI dùng `media_metadata.json` để:

* Resolve normalized video path.
* Resolve voice-over audio path.
* Kiểm tra video/audio source tồn tại.

UI không normalize media.

### 17.5. Với Renderer

Renderer dùng `timeline.json` sau khi UI lưu.

UI phải đảm bảo timeline đã lưu:

* Đúng schema.
* Không có field ngoài allowed value.
* Visual items đủ thông tin render.
* Segment thiếu visual được đánh dấu rõ.

Renderer không đọc UI state trong memory. Chỉ file `timeline.json` là contract giữa UI và Renderer.

## 18. Điều kiện handoff sang Renderer

Review UI được phép bàn giao sang Renderer khi:

* `timeline.json` parse được.
* `project_id` đúng.
* `render_settings` hợp lệ.
* Mỗi segment cần render có ít nhất một visual item.
* Không còn validation error.
* `source_path` resolve được.
* `clip_start/clip_end` hợp lệ.
* `timeline_start/timeline_end` hợp lệ.
* `speed` hợp lệ.
* `transition` hợp lệ.
* `updated_at` đã được cập nhật sau lần save cuối.

Nếu vẫn còn `needs_review = true`:

* UI có thể cảnh báo.
* Vẫn có thể cho render nếu không có error kỹ thuật.

Nếu còn `visual_items = []`:

* UI phải cảnh báo rõ.
* Không nên cho bấm Render nếu Renderer chưa hỗ trợ placeholder.

## 19. Test cases bắt buộc

### 19.1. Test load project hợp lệ

Input:

* Đủ 5 file JSON hợp lệ.

Kỳ vọng:

* UI load được project.
* Segment list hiển thị đúng số item.
* Segment đầu tiên được chọn.
* Không có validation error.

### 19.2. Test project_id không khớp

Input:

* `timeline.json` và `matching_candidates.json` khác `project_id`.

Kỳ vọng:

* UI báo lỗi.
* Không cho save.
* Không tự sửa project_id.

### 19.3. Test highlight needs_review

Input:

* Một segment có `needs_review = true`.

Kỳ vọng:

* Segment được highlight.
* Có thể filter Needs review.

### 19.4. Test hiển thị candidate list

Input:

* Timeline item có `candidates_ref = candidates_a001`.
* Matching file có candidate set tương ứng.

Kỳ vọng:

* UI hiển thị đúng top-k.
* Candidate sort theo rank.
* Score và reason hiển thị nếu có.

### 19.5. Test đổi clip từ candidate

Input:

* Segment có visual item hiện tại.
* Candidate rank 2 hợp lệ.

Kỳ vọng:

* UI cập nhật `clip_id`.
* UI cập nhật `video_id`.
* UI cập nhật `source_path`.
* UI cập nhật `source_candidate_rank = 2`.
* `user_edited = true`.
* Timeline vẫn validate được.

### 19.6. Test segment không có visual item

Input:

* Segment có `visual_items = []`.
* Candidate hợp lệ.

Kỳ vọng:

* UI cho chọn candidate.
* UI tạo visual item mới.
* `timeline_item_id` hợp lệ.
* `needs_review` có thể tắt sau khi người dùng xác nhận.

### 19.7. Test chỉnh clip_start/clip_end

Input:

* Người dùng chỉnh `clip_start` và `clip_end`.

Kỳ vọng:

* UI tính lại hoặc validate `speed`.
* Nếu `clip_end <= clip_start`, báo error.
* Nếu vượt range clip, báo error.

### 19.8. Test chỉnh speed

Input:

* Người dùng chỉnh speed thành `1.1`.

Kỳ vọng:

* UI cập nhật `clip_end` theo speed.
* Nếu `clip_end` vượt clip range, báo error.
* Nếu speed ngoài `[0.75, 1.25]`, không cho lưu.

### 19.9. Test save timeline

Input:

* Người dùng đổi clip rồi bấm Save.

Kỳ vọng:

* UI validate trước khi lưu.
* `updated_at` thay đổi.
* `timeline.json` được ghi.
* Reload lại UI vẫn thấy chỉnh sửa.

### 19.10. Test không xóa candidates_ref

Input:

* Người dùng đổi clip.

Kỳ vọng:

* `candidates_ref` vẫn giữ nguyên.
* Candidate list vẫn hiển thị được sau reload.

### 19.11. Test read-only mode

Input:

* UI chạy với `--readonly`.

Kỳ vọng:

* Load và preview được.
* Control chỉnh sửa disabled.
* Save disabled.

### 19.12. Test validation trước Renderer

Input:

* Một visual item có `speed = 1.5`.

Kỳ vọng:

* UI báo validation error.
* Không cho save hoặc không cho handoff sang Renderer.

## 20. Tiêu chí nghiệm thu

Module Review UI được xem là đạt yêu cầu MVP khi:

1. Load được `timeline.json`.
2. Load được `matching_candidates.json`.
3. Load được `clip_metadata.json`.
4. Load được `audio_segments.json`.
5. Load được `media_metadata.json`.
6. Validate được `project_id` giữa các file.
7. Hiển thị được danh sách timeline items.
8. Hiển thị transcript và timing từng segment.
9. Hiển thị `confidence`, `score`, `needs_review`, `fallback_used`.
10. Highlight được segment cần review.
11. Hiển thị được visual item hiện tại.
12. Preview được clip hiện tại ở mức MVP.
13. Hiển thị được top-k candidates theo `candidates_ref`.
14. Hiển thị rank, score và reason của candidate nếu có.
15. Cho phép đổi clip từ top-k.
16. Khi đổi clip, cập nhật đúng `clip_id`, `video_id`, `source_path`.
17. Khi đổi clip, cập nhật đúng `clip_start`, `clip_end`, `speed`.
18. Khi đổi clip, cập nhật đúng `source_candidate_rank`.
19. Khi người dùng chỉnh, set `user_edited = true`.
20. Cho phép chỉnh `clip_start`, `clip_end` trong range hợp lệ.
21. Cho phép chỉnh `speed` trong `[0.75, 1.25]`.
22. Cho phép chỉnh `transition` trong allowed list.
23. Cho phép chỉnh `crop_mode` trong allowed list.
24. Cho phép chỉnh `volume`.
25. Cho phép set `locked`.
26. Không sửa `matching_candidates.json`.
27. Không sửa `clip_metadata.json`.
28. Không sửa `audio_segments.json`.
29. Không thay đổi `segment_id`, `audio_start`, `audio_end`.
30. Validate timeline trước khi save.
31. Cập nhật `updated_at` khi save.
32. Ghi lại `timeline.json` đúng Data Contract.
33. Có cảnh báo khi còn item thiếu visual.
34. Có read-only/error state rõ ràng.
35. Renderer có thể dùng timeline sau khi UI save.

## 21. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 7 cần tự kiểm tra:

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc được timeline.json
[ ] Đọc được matching_candidates.json
[ ] Đọc được clip_metadata.json
[ ] Đọc được audio_segments.json
[ ] Đọc được media_metadata.json
[ ] Validate project_id các file khớp nhau
[ ] Hiển thị segment list theo timeline order
[ ] Hiển thị transcript từng segment
[ ] Hiển thị confidence/score/fallback/needs_review
[ ] Filter được segment needs_review
[ ] Hiển thị visual item hiện tại
[ ] Preview được clip hiện tại ở mức MVP
[ ] Map candidates_ref sang candidate_set_id
[ ] Hiển thị top-k candidates đúng rank
[ ] Hiển thị candidate score/reason nếu có
[ ] Disable candidate không hợp lệ
[ ] Đổi clip từ candidate được
[ ] Cập nhật clip_id/video_id/source_path khi đổi clip
[ ] Cập nhật clip_start/clip_end/speed khi đổi clip
[ ] Cập nhật source_candidate_rank khi đổi clip từ top-k
[ ] Giữ nguyên candidates_ref sau khi đổi clip
[ ] Set user_edited = true khi có chỉnh sửa
[ ] Set locked theo thao tác người dùng
[ ] Chỉnh clip_start/clip_end có validate range
[ ] Chỉnh speed có validate [0.75, 1.25]
[ ] Chỉnh transition chỉ dùng allowed values
[ ] Chỉnh crop_mode chỉ dùng allowed values
[ ] Chỉnh volume hợp lệ
[ ] Mark as reviewed không tự đổi confidence
[ ] Validate toàn bộ timeline trước khi save
[ ] Không cho save nếu có error nghiêm trọng
[ ] Cập nhật updated_at khi save
[ ] Preserve schema_version/project_id/audio_id/created_at
[ ] Không sửa matching_candidates.json
[ ] Không sửa clip_metadata.json
[ ] Không sửa audio_segments.json
[ ] Có dirty state
[ ] Có cảnh báo khi rời trang chưa save
[ ] Có read-only mode hoặc error state rõ ràng
[ ] Có test với dữ liệu mẫu nhỏ
[ ] Timeline sau save đưa được cho Renderer
```

## 22. Ghi chú triển khai MVP

MVP của Review UI nên tập trung vào khả năng review và sửa nhanh các segment xấu, không cần làm editor phức tạp.

Thứ tự ưu tiên nên là:

1. Load và validate dữ liệu chắc.
2. Hiển thị segment list rõ ràng.
3. Highlight segment cần review.
4. Hiển thị clip hiện tại.
5. Hiển thị top-k candidates.
6. Cho đổi clip từ top-k.
7. Validate timeline trước khi lưu.
8. Lưu `timeline.json` đúng contract.
9. Preview đơn giản.
10. Chỉnh timing/speed/crop/transition sau khi luồng đổi clip ổn định.

Không nên đưa logic matching mới vào UI. Nếu UI bắt đầu tự tính lại clip phù hợp, ranh giới module sẽ bị lệch và khó debug tích hợp. UI chỉ nên giúp người dùng chọn từ dữ liệu đã có và lưu quyết định đó vào `timeline.json`.
