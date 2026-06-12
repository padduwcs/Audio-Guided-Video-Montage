# 05. Stage 3 - Video Analysis

## 1. Mục tiêu của stage

Stage 3 - Video Analysis có nhiệm vụ phân tích các video nguồn đã được chuẩn hóa từ Stage 1, tách video thành các clip candidate, trích keyframe đại diện, tính quality score cơ bản và tạo `clip_metadata.json` cho các stage phía sau.

Stage này tạo "kho cảnh" để hệ thống dùng khi matching với audio. Audio Analyzer cho biết audio đang nói gì; Video Analyzer cho biết video nguồn có những đoạn hình nào có thể dùng được.

Mục tiêu chính:

* Đọc danh sách video nguồn từ `media_metadata.json`.
* Chỉ xử lý video có `status = ready` hoặc `status = warning`.
* Chạy scene detection hoặc shot detection để tìm ranh giới cảnh.
* Tạo danh sách clip candidate từ video nguồn.
* Loại hoặc đánh dấu clip quá ngắn, lỗi hoặc chất lượng quá thấp.
* Chia nhỏ clip quá dài nếu cần.
* Trích keyframe đại diện cho mỗi clip.
* Tính quality score cơ bản cho clip và keyframe.
* Sinh `clip_id` và `keyframe_id` ổn định.
* Xuất `clip_metadata.json` đúng Data Contract hiện hành.
* Xuất ảnh keyframe vào thư mục thống nhất.
* Xuất log phụ để debug quá trình phân tích video nếu cần.

## 2. Vị trí trong pipeline

Stage này nằm sau Input Processor và chạy song song tương đối độc lập với Audio Analyzer:

```text
Input Processor
        |
        |-- media_metadata.json
        |-- normalized video files
        |
        v
Video Analyzer
        |
        |-- clip_metadata.json
        |-- keyframe image files
        |-- video_analysis_log.json
        |
        |--> Embedding Indexer
        |--> Matching Engine (later, after Embedding Indexer)
        |--> Timeline Planner (later, after Matching Engine)
        |--> Review UI (later, after Timeline Planner)
        |--> Renderer (later, after timeline is ready)
        |--> Evaluation (later)
```

Video Analyzer không cần đọc audio thuyết minh. Stage này chỉ cần video đã chuẩn hóa và metadata liên quan đến video.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Video Analyzer cần xử lý các phần sau:

1. Đọc `media_metadata.json`.
2. Lọc các video usable, tức là video có `status = ready` hoặc `status = warning`.
3. Lấy `videos[*].normalized_path`.
4. Kiểm tra file video normalized tồn tại và đọc được.
5. Chạy scene detection hoặc shot detection.
6. Tạo clip candidate từ ranh giới scene/shot.
7. Chia nhỏ clip quá dài nếu cần.
8. Đánh dấu clip quá ngắn nếu không đủ dùng.
9. Trích keyframe đại diện cho mỗi clip.
10. Tính quality score cơ bản cho keyframe và clip.
11. Sinh `clip_id` theo quy tắc ổn định.
12. Sinh `keyframe_id` theo quy tắc ổn định.
13. Lưu keyframe image files.
14. Xuất `clip_metadata.json`.
15. Xuất `video_analysis_log.json` để debug nếu cần.

### 3.2. Stage này không làm

Video Analyzer không chịu trách nhiệm cho các phần sau:

* Không chuẩn hóa video.
* Không chỉnh sửa hoặc render video cuối.
* Không chạy ASR.
* Không đọc transcript audio.
* Không tạo text query.
* Không tạo embedding.
* Không matching clip với audio segment.
* Không chọn clip mặc định cho timeline.
* Không tạo `timeline.json`.
* Không quyết định transition, speed hoặc crop mode của video cuối.

Stage này chỉ tạo danh sách clip candidate và metadata đi kèm. Việc clip nào khớp với đoạn audio nào thuộc về Matching Engine và Timeline Planner.

## 4. Input

### 4.1. Input chính

Video Analyzer đọc:

```text
data/intermediate/media_metadata.json
```

Video paths thực tế lấy từ:

```text
media_metadata.json -> videos[*].normalized_path
```

(Ví dụ sample: `data/normalized/video_01.mp4`, `data/normalized/video_02.mp4`.)

Không hard-code đường dẫn video trong module.

### 4.2. Điều kiện input hợp lệ

`media_metadata.json` phải thỏa:

* Parse được JSON.
* Có top-level field `schema_version`.
* Có top-level field `project_id`.
* Có array `videos`.
* `videos` có ít nhất một video.
* Mỗi video có `video_id`.
* Mỗi video có `normalized_path`.
* Mỗi video có `duration > 0`.
* Mỗi video có `fps > 0`.
* Mỗi video có `width > 0` và `height > 0`.

Video Analyzer được phép xử lý video có:

```text
status = ready
status = warning
```

Video Analyzer phải bỏ qua video có:

```text
status = error
```

Pipeline phải dừng nếu không có video usable nào.

### 4.3. Cấu hình chạy module

Cấu hình dưới đây là cấu hình nội bộ của Video Analyzer, không phải Data Contract bắt buộc giữa các module.

Ví dụ cấu hình:

```json
{
  "project_id": "demo_01",
  "media_metadata_path": "data/intermediate/media_metadata.json",
  "output_dir": "data/intermediate",
  "keyframe_dir": "data/keyframes",
  "scene_detection": {
    "method": "content",
    "threshold": 27.0
  },
  "clip": {
    "min_clip_duration": 1.5,
    "max_clip_duration": 8.0,
    "split_long_clips": true,
    "keep_low_quality_clips": true
  },
  "keyframes": {
    "positions": ["start", "middle", "end"],
    "image_format": "jpg"
  },
  "quality": {
    "compute_blur_score": true,
    "compute_brightness_score": true,
    "compute_motion_score": true,
    "compute_stability_score": true
  }
}
```

Trong MVP, các giá trị đề xuất:

| Tham số | Giá trị đề xuất |
| ------- | --------------- |
| `scene_detection.method` | `content` hoặc thư viện tương đương |
| `min_clip_duration` | `1.5` giây |
| `max_clip_duration` | `8.0` giây |
| `split_long_clips` | `true` |
| `keep_low_quality_clips` | `true` |
| `keyframes.positions` | `start`, `middle`, `end` |
| `keyframes.image_format` | `jpg` |

Ghi chú:

* Không bắt buộc dùng đúng thuật toán scene detection trong ví dụ. Thành viên có thể dùng PySceneDetect, OpenCV hoặc FFmpeg nếu output vẫn đúng contract.
* Không nên xóa hoàn toàn clip chất lượng thấp khỏi metadata nếu vẫn cần debug. Có thể giữ clip đó với `status = low_quality`.
* Nếu chưa tính được một quality score cụ thể, dùng `null`, không tự đặt bừa `0`.
* Nếu chưa làm được caption hoặc content tags, có thể bỏ qua vì đây là optional fields.

## 5. Output

Stage này tạo output chính:

```text
data/intermediate/clip_metadata.json
data/keyframes/v01_c001_k01.jpg
data/keyframes/v01_c001_k02.jpg
data/keyframes/v01_c001_k03.jpg
```

Stage này có thể tạo output phụ:

```text
data/intermediate/video_analysis_log.json
```

Trong đó:

* `clip_metadata.json` là Data Contract chính cho các stage sau.
* Keyframe image files là dữ liệu trực quan phục vụ Embedding Indexer, Matching Engine và Review UI.
* `video_analysis_log.json` là log phụ để debug scene detection, keyframe extraction và quality scoring.

Các module sau chỉ nên phụ thuộc vào `clip_metadata.json` và keyframe paths trong file này. Log phụ không phải contract bắt buộc.

## 6. Data Contract: `clip_metadata.json`

### 6.1. Vai trò

`clip_metadata.json` lưu danh sách clip candidate được tách từ video nguồn.

File này giúp các module sau biết:

* Có những clip candidate nào.
* Mỗi clip nằm trong video nguồn nào.
* Clip bắt đầu và kết thúc ở thời điểm nào.
* Clip có keyframe đại diện nào.
* Clip có chất lượng hình ảnh cơ bản ra sao.
* Clip nào usable, clip nào quá ngắn, chất lượng thấp hoặc lỗi.

### 6.2. Cấu trúc top-level

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:10:00Z",
  "items": []
}
```

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `schema_version` | string | Phiên bản schema |
| `project_id` | string | ID dự án đang xử lý |
| `created_at` | string | Thời điểm tạo file |
| `items` | array[object] | Danh sách clip candidate |

Quy ước:

* `schema_version` dùng `"1.0"` trong MVP.
* `project_id` lấy từ `media_metadata.json`.
* `items` phải có ít nhất một clip usable nếu phân tích video thành công.

### 6.3. Clip item

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `clip_id` | string | ID clip candidate |
| `video_id` | string | Video nguồn chứa clip |
| `start` | number | Thời điểm bắt đầu trong video nguồn |
| `end` | number | Thời điểm kết thúc trong video nguồn |
| `duration` | number | Thời lượng clip |
| `keyframes` | array[object] | Danh sách keyframe |
| `quality_score` | number/null | Điểm chất lượng tổng hợp |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `scene_index` | integer | Thứ tự scene/shot |
| `source_path` | string | Đường dẫn video nguồn đã chuẩn hóa |
| `content_tags` | array[string] | Tag mô tả nội dung nếu có |
| `caption` | string/null | Mô tả ngắn clip nếu có |
| `quality` | object | Chi tiết chất lượng |
| `status` | string | Trạng thái clip |
| `notes` | string | Ghi chú |

Allowed `status`:

```text
usable
low_quality
too_short
error
```

Trong Data Contract tổng, `status` là optional field. Tuy nhiên, với implementation MVP của Stage 3, nên ghi `status` cho mọi clip để các module sau không phải tự suy luận clip nào usable, clip nào cần penalty hoặc clip nào phải bỏ qua.

Tương tự, `source_path` là optional field trong Data Contract tổng, nhưng MVP nên ghi `source_path` cho mọi clip để Timeline Planner, Review UI và Renderer dễ map clip về file video normalized.

### 6.4. Keyframe item

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `keyframe_id` | string | ID keyframe |
| `timestamp` | number | Vị trí keyframe trong video nguồn |
| `path` | string | Đường dẫn ảnh keyframe |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `position` | string | Vị trí trong clip |
| `quality_score` | number/null | Chất lượng frame |

Allowed `position`:

```text
start
middle
end
extra
```

### 6.5. Quality object

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `blur_score` | number/null | Độ nét |
| `brightness_score` | number/null | Độ sáng |
| `motion_score` | number/null | Mức chuyển động |
| `stability_score` | number/null | Độ ổn định |
| `quality_score` | number/null | Điểm tổng hợp |

Quy ước:

* Tất cả score dùng số thực từ `0.0` đến `1.0`.
* Score càng cao nghĩa là càng tốt, trừ khi tài liệu module ghi rõ ngược lại.
* Nếu chưa tính được score, dùng `null`.
* `quality_score` ở cấp clip nên khớp với `quality.quality_score` nếu cả hai cùng tồn tại.

## 7. Quy tắc timestamp

Tất cả thời gian trong `clip_metadata.json` dùng đơn vị giây.

Quy tắc bắt buộc:

* `start >= 0`
* `end > start`
* `duration = end - start`
* `end` không được vượt quá duration video quá sai số nhỏ.
* Keyframe `timestamp` phải nằm trong khoảng `[start, end]` của clip.
* Clip trong cùng một video nên được sắp xếp tăng dần theo `start`.

Sai số làm tròn chấp nhận được:

```text
0.01s
```

Gợi ý làm tròn:

* `start`, `end`, `duration`, `timestamp`: làm tròn 2 hoặc 3 chữ số thập phân.
* Khi tính `duration`, nên dùng cùng độ chính xác với `start` và `end` để tránh lệch nhỏ khó debug.

## 8. Quy tắc đặt ID

ID cần ngắn gọn, ổn định và dễ map giữa các file.

Với MVP, quy tắc đề xuất:

```text
video_id: video_01
clip_id: v01_c001, v01_c002, v01_c003, ...
keyframe_id: v01_c001_k01, v01_c001_k02, ...
```

Quy tắc sinh `clip_id`:

* Dựa trên `video_id`.
* Với `video_01`, prefix clip nên là `v01`.
* Đánh số clip theo thứ tự thời gian trong video.
* Dùng padding 3 chữ số trong MVP: `v01_c001`, `v01_c002`.
* Nếu chạy lại với cùng video và cùng rule detection, ID nên giữ ổn định.

Quy tắc sinh `keyframe_id`:

* Dựa trên `clip_id`.
* Đánh số keyframe theo thứ tự trong clip.
* Dùng padding 2 chữ số trong MVP: `v01_c001_k01`, `v01_c001_k02`.

Không dùng tên file gốc hoặc timestamp làm ID chính, vì dễ thay đổi và khó map giữa các file.

## 9. Quy trình xử lý đề xuất

### 9.1. Bước 1 - Đọc metadata

Video Analyzer đọc `media_metadata.json` và lấy:

* `project_id`
* `videos[*].video_id`
* `videos[*].normalized_path`
* `videos[*].duration`
* `videos[*].fps`
* `videos[*].width`
* `videos[*].height`
* `videos[*].status`

Nếu video có `status = warning`, module vẫn xử lý tiếp nhưng ghi lại warning trong `video_analysis_log.json`.

### 9.2. Bước 2 - Lọc video usable

Video usable là video có:

```text
status = ready
status = warning
```

Video có `status = error` phải bị bỏ qua.

Nếu không có video usable nào, module phải dừng và báo lỗi rõ ràng.

### 9.3. Bước 3 - Validate video file

Với từng video usable, kiểm tra:

* File trong `normalized_path` tồn tại.
* File đọc được.
* Duration thực tế gần với duration trong metadata.
* Video có stream hình ảnh hợp lệ.
* FPS đọc được.
* Width và height đọc được.

Nếu duration thực tế lệch nhẹ do encode/decode, có thể tiếp tục. Nếu lệch lớn, nên ghi warning hoặc bỏ qua video tùy mức độ.

Gợi ý:

```text
Lệch <= 0.1s: chấp nhận
Lệch > 0.1s và <= 1.0s: warning
Lệch > 1.0s: cần xem lại, có thể bỏ qua video nếu ảnh hưởng timestamp
```

### 9.4. Bước 4 - Chạy scene/shot detection

Chạy scene detection hoặc shot detection để tìm ranh giới cảnh trong video.

Output nội bộ tối thiểu cần có:

* scene/shot index
* start time
* end time
* duration

Yêu cầu:

* Timestamp phải tương ứng với video normalized.
* Không cắt hoặc thay đổi video trong bước này.
* Nếu không detect được scene nào, có thể fallback bằng cách chia video theo khoảng thời gian cố định.

Gợi ý fallback:

```text
Nếu video không có scene boundary rõ:
chia video thành các clip dài khoảng 4-6 giây.
```

### 9.5. Bước 5 - Tạo clip candidate

Từ ranh giới scene/shot, tạo clip candidate.

Clip tốt nên thỏa:

* Có duration đủ để dùng trong timeline.
* Không quá dài so với một audio segment thông thường.
* Có hình ảnh đọc được.
* Có ít nhất một keyframe đại diện.

Gợi ý duration:

```text
min_clip_duration: 1.5s
max_clip_duration: 8.0s
```

Quy tắc:

* Clip ngắn hơn `min_clip_duration` nên được đánh dấu `too_short` hoặc gộp với clip lân cận nếu hợp lý.
* Clip dài hơn `max_clip_duration` nên được chia nhỏ nếu có thể.
* Không tự loại bỏ hoàn toàn clip chỉ vì nội dung có vẻ không liên quan đến audio.
* Không tạo clip có `duration <= 0`.

### 9.6. Bước 6 - Xử lý clip quá ngắn

Clip quá ngắn thường khó dùng trong timeline vì gây cảm giác cắt cảnh quá nhanh.

Quy tắc đề xuất:

* Nếu clip quá ngắn nhưng nằm giữa hai clip cùng cảnh, có thể gộp với clip trước hoặc sau.
* Nếu không thể gộp, vẫn có thể ghi vào `clip_metadata.json` với `status = too_short`.
* Matching Engine và Timeline Planner có thể bỏ qua clip `too_short` hoặc dùng với penalty.

Không nên xóa clip quá ngắn khỏi mọi log, vì khi debug scene detection sẽ khó biết vì sao clip biến mất.

### 9.7. Bước 7 - Chia clip quá dài

Clip quá dài có thể chứa nhiều nội dung hoặc làm matching kém chính xác.

Quy tắc đề xuất:

* Nếu scene/shot dài hơn `max_clip_duration`, chia thành nhiều clip con.
* Mỗi clip con nên có duration khoảng `4-8s` nếu có thể.
* Clip con phải giữ `video_id` gốc.
* `scene_index` có thể giữ scene gốc hoặc dùng index mới, miễn là ghi nhất quán.
* `start`, `end`, `duration` phải là timestamp trong video nguồn.

Ví dụ:

```text
Scene 3: 24.0s -> 42.0s
```

Có thể chia thành:

```text
v01_c003: 24.0s -> 30.0s
v01_c010: 30.0s -> 36.0s
v01_c011: 36.0s -> 42.0s
```

(Ví dụ logic chia clip; timestamp thật xem `docs/samples/clip_metadata_sample.json`.)

### 9.8. Bước 8 - Trích keyframe

Mỗi clip cần có ít nhất một keyframe nếu clip không lỗi.

MVP nên trích 3 keyframe:

```text
start
middle
end
```

Quy tắc timestamp keyframe:

* `start`: gần đầu clip nhưng tránh frame đầu nếu có transition hoặc blur, ví dụ `start + 0.2s`.
* `middle`: gần giữa clip.
* `end`: gần cuối clip nhưng tránh frame cuối, ví dụ `end - 0.2s`.
* Nếu clip quá ngắn, có thể chỉ trích 1 keyframe ở giữa.
* Keyframe timestamp phải nằm trong `[clip.start, clip.end]`.

Output keyframe (ví dụ `v01_c003`; mẫu chuẩn có `k01`, `k02` — xem `clip_metadata_sample.json`):

```text
data/keyframes/v01_c003_k01.jpg
data/keyframes/v01_c003_k02.jpg
```

MVP mục tiêu 3 keyframe (`start` / `middle` / `end`) khi clip đủ dài; clip ngắn có thể chỉ 1–2 keyframe.

Path trong JSON phải là relative path.

### 9.9. Bước 9 - Tính quality score

Quality score giúp Matching Engine và Timeline Planner ưu tiên clip hình ảnh tốt hơn.

Các score nên tính trong MVP:

| Score | Ý nghĩa |
| ----- | ------- |
| `blur_score` | Độ nét của frame/clip |
| `brightness_score` | Độ sáng có đủ nhìn rõ không |
| `motion_score` | Mức chuyển động có quá mạnh không |
| `stability_score` | Độ ổn định, ít rung |
| `quality_score` | Điểm tổng hợp |

Quy ước:

* Tất cả score nằm trong `0.0` đến `1.0`.
* Score cao hơn nghĩa là tốt hơn.
* Nếu chưa tính được score nào, dùng `null`.
* Không dùng score ngoài khoảng `0.0` đến `1.0`.

Gợi ý tổng hợp:

```text
quality_score = trung bình có trọng số của blur, brightness, motion, stability
```

MVP không cần công thức quá phức tạp. Quan trọng là score nhất quán và giải thích được.

### 9.10. Bước 10 - Gán status cho clip

Allowed `status`:

```text
usable
low_quality
too_short
error
```

Quy tắc đề xuất:

* `usable`: clip dùng được cho matching/timeline.
* `low_quality`: clip đọc được nhưng chất lượng hình thấp.
* `too_short`: clip quá ngắn để dùng bình thường.
* `error`: clip lỗi, không trích được keyframe hoặc timestamp không hợp lệ.

Các module sau được phép sử dụng clip có:

```text
status = usable
status = low_quality
```

Clip `low_quality` vẫn có thể dùng trong trường hợp thiếu footage, nhưng nên bị penalty ở Matching Engine hoặc Timeline Planner.

Clip `too_short` và `error` không nên được chọn mặc định trong MVP. Nếu cần giữ trong metadata để debug, phải ghi rõ status.

### 9.11. Bước 11 - Ghi `clip_metadata.json`

Trước khi ghi file, cần kiểm tra:

* Có đủ top-level fields.
* `items` không rỗng nếu có video usable.
* Mỗi clip có đủ required fields.
* `clip_id` không trùng.
* `video_id` tồn tại trong `media_metadata.json`.
* `source_path` nên có với mọi clip và trỏ về video normalized tương ứng.
* `start`, `end`, `duration` hợp lệ.
* `keyframes` không rỗng với clip usable.
* Mỗi keyframe có đủ required fields.
* Keyframe path là relative path.
* Keyframe file thực sự tồn tại.
* `quality_score` là number trong `0.0` đến `1.0` hoặc `null`.
* `status` nên có với mọi clip và phải thuộc allowed values.

## 10. Quy tắc scene/clip chi tiết

### 10.1. Scene detection không cần hoàn hảo

MVP không yêu cầu scene detection chính xác tuyệt đối.

Yêu cầu quan trọng hơn là:

* Không tạo clip lỗi timestamp.
* Không bỏ sót toàn bộ video.
* Tạo được clip candidate đủ dùng cho matching.
* Có log để debug khi detect scene quá ít hoặc quá nhiều.

Nếu scene detection chưa tốt, có thể fallback bằng chia fixed-window theo thời gian.

### 10.2. Không cắt clip theo audio ở Stage 3

Stage 3 không biết audio segment đang cần cảnh gì, nên không được cắt clip dựa trên transcript hoặc audio duration.

Ví dụ không nên:

```text
Audio segment dài 5.2s nên cắt mọi clip thành 5.2s.
```

Việc căn duration với audio thuộc về Timeline Planner.

### 10.3. Không tự loại clip vì "không liên quan"

Video Analyzer không nên quyết định một clip có liên quan đến audio hay không.

Stage này chỉ đánh giá:

* Clip có tồn tại không.
* Clip nằm ở đâu trong video.
* Clip có keyframe không.
* Clip có chất lượng hình ảnh cơ bản ra sao.

Độ liên quan ngữ nghĩa thuộc về Embedding Indexer và Matching Engine.

### 10.4. Ưu tiên giữ dữ liệu có trạng thái rõ

Nếu clip có vấn đề nhưng vẫn đọc được, nên giữ lại với status phù hợp thay vì xóa im lặng.

Ví dụ:

* Clip quá ngắn: `status = too_short`.
* Clip tối hoặc mờ: `status = low_quality`.
* Clip lỗi keyframe: `status = error`.

Cách này giúp leader debug dễ hơn và giúp Evaluation có dữ liệu phân tích.

## 11. Quy tắc keyframe chi tiết

### 11.1. Keyframe phải đại diện cho clip

Keyframe nên giúp các module sau hiểu nội dung clip.

MVP nên lấy:

* Một frame gần đầu clip.
* Một frame giữa clip.
* Một frame gần cuối clip.

Nếu một frame bị lỗi hoặc quá mờ, có thể lấy frame lân cận.

### 11.2. Không lấy frame ngoài clip

Keyframe timestamp phải nằm trong khoảng clip.

Không dùng:

```text
keyframe.timestamp < clip.start
keyframe.timestamp > clip.end
```

### 11.3. Keyframe path phải ổn định

Path keyframe nên dựa trên `keyframe_id`.

Ví dụ:

```text
data/keyframes/v01_c003_k01.jpg
```

Không dùng tên file chứa timestamp dài hoặc ký tự đặc biệt nếu không cần thiết.

### 11.4. Keyframe cho clip lỗi

Nếu không trích được keyframe cho clip:

* Không đánh dấu clip là `usable`.
* Gán `status = error` hoặc ghi rõ `notes`.
* Không tạo path giả.
* Không đưa keyframe item nếu file ảnh không tồn tại.

## 12. Quy tắc quality score

### 12.1. `blur_score`

`blur_score` phản ánh độ nét.

Gợi ý:

* `1.0`: rất nét.
* `0.0`: rất mờ.

Có thể dùng variance of Laplacian hoặc phương pháp tương đương rồi normalize về `0.0` đến `1.0`.

### 12.2. `brightness_score`

`brightness_score` phản ánh độ sáng có đủ nhìn rõ hay không.

Gợi ý:

* Clip quá tối hoặc quá cháy sáng nên điểm thấp.
* Clip sáng vừa phải nên điểm cao.

### 12.3. `motion_score`

`motion_score` phản ánh mức chuyển động có phù hợp không.

Quy ước trong MVP:

* Score cao nghĩa là chuyển động vừa phải, dễ xem.
* Score thấp nghĩa là chuyển động quá mạnh, rung lắc hoặc gần như không có thông tin nếu cần cảnh hành động.

Nếu nhóm chưa thống nhất được cách tính motion tốt, có thể để `motion_score = null`.

### 12.4. `stability_score`

`stability_score` phản ánh độ ổn định của cảnh.

Gợi ý:

* Video ít rung: điểm cao.
* Video rung mạnh: điểm thấp.

Nếu chưa tính được stability, có thể để `stability_score = null`.

### 12.5. `quality_score`

`quality_score` là điểm tổng hợp.

Quy tắc:

* Nếu có đủ score thành phần, tính trung bình có trọng số.
* Nếu chỉ có một vài score thành phần, có thể tính trung bình các score có giá trị.
* Nếu không có score nào, dùng `null`.
* Không dùng `0` để thay cho "chưa tính".

## 13. Output phụ: `video_analysis_log.json`

### 13.1. Vai trò

`video_analysis_log.json` là file log phụ của Stage 3, dùng để debug scene detection, clip splitting, keyframe extraction và quality scoring.

File này không phải Data Contract chính giữa các module. Các module sau không nên phụ thuộc vào file này để chạy logic chính.

Nên dùng file này để ghi:

* Video nào được xử lý.
* Video nào bị bỏ qua vì `status = error`.
* Scene detection method và threshold.
* Số scene/shot detect được.
* Số clip candidate tạo ra.
* Số clip usable, low quality, too short, error.
* Clip nào bị split từ scene dài.
* Clip nào không trích được keyframe.
* Quality score summary.
* Thời gian chạy module nếu cần.

### 13.2. Cấu trúc đề xuất

Đây là cấu trúc đề xuất, không bắt buộc phải xem là schema liên module:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:10:00Z",
  "config": {
    "scene_detection_method": "content",
    "threshold": 27.0,
    "min_clip_duration": 1.5,
    "max_clip_duration": 8.0
  },
  "summary": {
    "video_count": 2,
    "processed_video_count": 2,
    "clip_count": 34,
    "usable_count": 28,
    "low_quality_count": 4,
    "too_short_count": 2,
    "error_count": 0
  },
  "videos": [
    {
      "video_id": "video_01",
      "path": "data/normalized/video_01.mp4",
      "scene_count": 12,
      "clip_count": 16,
      "warnings": []
    }
  ],
  "warnings": [],
  "errors": []
}
```

### 13.3. Nguyên tắc sử dụng

`clip_metadata.json` là nguồn dữ liệu chính cho các module sau. `video_analysis_log.json` chỉ dùng để:

* Debug vì sao clip bị chia quá nhiều hoặc quá ít.
* Debug vì sao clip bị `low_quality`, `too_short` hoặc `error`.
* Kiểm tra keyframe có được trích đúng không.
* Hỗ trợ leader review chất lượng stage.

Nếu `clip_metadata.json` và `video_analysis_log.json` có thông tin mâu thuẫn, các module pipeline phải ưu tiên `clip_metadata.json`.

## 14. Ví dụ `clip_metadata.json`

**Mẫu chuẩn:** `docs/samples/clip_metadata_sample.json`.

Ví dụ rút gọn một clip (sample có thêm `v01_c004`, `v01_c005`, `v02_c001`, ...):

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:10:00Z",
  "items": [
    {
      "clip_id": "v01_c003",
      "video_id": "video_01",
      "source_path": "data/normalized/video_01.mp4",
      "scene_index": 3,
      "start": 24.5,
      "end": 31.2,
      "duration": 6.7,
      "keyframes": [
        {
          "keyframe_id": "v01_c003_k01",
          "timestamp": 24.8,
          "position": "start",
          "path": "data/keyframes/v01_c003_k01.jpg",
          "quality_score": 0.78
        },
        {
          "keyframe_id": "v01_c003_k02",
          "timestamp": 27.8,
          "position": "middle",
          "path": "data/keyframes/v01_c003_k02.jpg",
          "quality_score": 0.83
        }
      ],
      "quality": {
        "blur_score": 0.83,
        "brightness_score": 0.71,
        "motion_score": 0.45,
        "stability_score": 0.76,
        "quality_score": 0.78
      },
      "quality_score": 0.78,
      "content_tags": ["entrance", "outdoor", "people"],
      "caption": "Main entrance area with people passing by.",
      "status": "usable"
    }
  ]
}
```

## 15. Quan hệ với các module khác

### 15.1. Input Processor

Video Analyzer đọc:

```text
media_metadata.json
videos[*].normalized_path
```

Video Analyzer không tự tìm video raw và không tự normalize lại video.

### 15.2. Embedding Indexer

Embedding Indexer đọc:

```text
clip_metadata.json
items[*].clip_id
items[*].keyframes
items[*].keyframes[*].path
```

Embedding Indexer dùng keyframe image files để tạo visual embeddings.

Nếu clip có nhiều keyframe, Embedding Indexer có thể:

* Tạo embedding cho từng keyframe.
* Tổng hợp nhiều keyframe thành embedding đại diện cho clip.

### 15.3. Matching Engine

Matching Engine đọc:

```text
clip_metadata.json
items[*].clip_id
items[*].duration
items[*].quality_score
items[*].status
```

Matching Engine có thể:

* Ưu tiên clip `usable`.
* Dùng clip `low_quality` nếu thiếu lựa chọn nhưng áp dụng penalty.
* Bỏ qua clip `too_short` và `error` trong MVP.
* Dùng `quality_score` làm một phần của `final_score`.

### 15.4. Timeline Planner

Timeline Planner đọc:

```text
clip_metadata.json
items[*].video_id
items[*].source_path
items[*].start
items[*].end
items[*].duration
items[*].status
```

Timeline Planner dùng metadata clip để quyết định cắt đoạn nào khi tạo `timeline.json`.

### 15.5. Review UI

Review UI đọc:

```text
clip_metadata.json
items[*].keyframes
items[*].quality_score
items[*].status
```

UI có thể hiển thị keyframe để người dùng chọn clip thay thế trong top-k.

### 15.6. Renderer

Renderer không nên phụ thuộc trực tiếp vào Video Analyzer để phân tích lại video.

Renderer có thể dùng `clip_metadata.json` hoặc thông tin đã được copy sang `timeline.json` để:

* Tìm video nguồn normalized.
* Cắt đúng `clip_start` và `clip_end`.
* Kiểm tra clip tồn tại trong metadata nếu cần validate.

### 15.7. Evaluation

Evaluation có thể dùng `clip_metadata.json` để:

* Tính số clip candidate.
* Tính tỷ lệ clip low quality.
* Tính repetition rate theo `clip_id`.
* Phân tích matching quality theo `quality_score`.

## 16. Điều kiện handoff output

Stage 3 được phép bàn giao `clip_metadata.json` cho Embedding Indexer; các module về sau như Matching Engine, Timeline Planner và Review UI có thể dùng cùng output này khi thỏa các điều kiện sau:

```text
clip_metadata.json parse được
clip_metadata.json có đủ top-level required fields
items không rỗng
mỗi clip có đủ required fields
clip_id không trùng
timestamp hợp lệ
keyframe path của clip usable tồn tại
quality_score là number trong [0.0, 1.0] hoặc null
status có ở mọi clip và thuộc allowed values
source_path của mỗi clip trỏ về video normalized tương ứng
```

Trong MVP, điều kiện handoff nên kiểm tra `status` như một field bắt buộc ở cấp implementation, dù trong Data Contract tổng nó là optional.

Nếu không tạo được clip usable nào:

* Module nên báo lỗi rõ ràng hoặc tạo log giải thích.
* Pipeline không nên chạy matching bình thường vì không có kho clip usable.
* Có thể vẫn giữ metadata các clip lỗi để debug, nhưng integration pipeline phải xem đây là lỗi chặn.

Nếu một số clip có `status = low_quality`, pipeline vẫn được chạy tiếp. Đây là cảnh báo cho Matching Engine, Timeline Planner và UI, không phải lỗi chặn pipeline.

## 17. Ràng buộc kỹ thuật

### 17.1. Không làm lệch video timeline

Video Analyzer không được thay đổi file video normalized trong quá trình phân tích.

Không được:

* Cắt video rồi ghi đè file normalized.
* Thay đổi speed video.
* Dịch timestamp theo cảm tính.

Nếu có tạo file tạm để phân tích, timestamp output vẫn phải map về video normalized gốc.

### 17.2. Không bịa quality score

Nếu chưa tính được score, dùng:

```json
"quality_score": null
```

Không dùng:

```json
"quality_score": 1.0
```

chỉ vì clip được tạo thành công.

### 17.3. Không tạo keyframe path giả

Nếu file ảnh keyframe không tồn tại, không được ghi path giả vào `clip_metadata.json`.

Với clip usable, keyframe path phải trỏ đến file có thật.

### 17.4. Không phụ thuộc vào log phụ

Các module sau không được phụ thuộc vào `video_analysis_log.json` để chạy logic chính.

Nếu thông tin cần thiết cho Embedding, Matching, Timeline hoặc UI, thông tin đó phải nằm trong `clip_metadata.json`.

## 18. Re-run behavior

Video Analyzer cần có quy tắc rõ ràng khi chạy lại với cùng `project_id`.

### 18.1. Mục tiêu

Chạy lại module không được làm `clip_id` và `keyframe_id` thay đổi bất ngờ nếu video và rule detection không đổi.

Yêu cầu:

* Nếu input video và cấu hình scene detection không đổi, clip order và `clip_id` nên giữ ổn định.
* Nếu đổi threshold hoặc rule split clip, clip boundary có thể thay đổi, nhưng cần ghi trong `video_analysis_log.json`.
* Không ghi đè output cũ nếu người chạy chưa cho phép.

### 18.2. Quy tắc đề xuất

Nếu chạy lại với cùng `project_id`:

* Nếu có flag `--overwrite`, module được phép ghi đè `clip_metadata.json`, keyframe image files và `video_analysis_log.json`.
* Nếu không có `--overwrite`, module nên báo output đã tồn tại và dừng an toàn, hoặc yêu cầu người dùng chọn output/run khác.
* Nếu đã có `embedding_metadata.json`, `matching_candidates.json` hoặc `timeline.json` dựa trên `clip_metadata.json` cũ, nên chạy lại các stage sau để tránh lệch `clip_id`, keyframe path hoặc timestamp.

## 19. Gợi ý cấu trúc code

Đây là gợi ý tổ chức module, không bắt buộc nếu nhóm đã có style code riêng.

```text
video_analyzer/
│
├── __init__.py
├── main.py
├── config.py
├── video_probe.py
├── scene_detector.py
├── clip_builder.py
├── keyframe_extractor.py
├── quality_scorer.py
├── clip_metadata_writer.py
└── validator.py
```

Vai trò từng file:

| File | Vai trò |
| ---- | ------- |
| `main.py` | Entry point chạy module |
| `config.py` | Đọc và validate cấu hình chạy module |
| `video_probe.py` | Kiểm tra video normalized và metadata thực tế |
| `scene_detector.py` | Detect scene/shot boundary |
| `clip_builder.py` | Tạo clip candidate, split/merge nếu cần |
| `keyframe_extractor.py` | Trích keyframe image files |
| `quality_scorer.py` | Tính quality score cho keyframe/clip |
| `clip_metadata_writer.py` | Tạo và ghi `clip_metadata.json` |
| `validator.py` | Kiểm tra input và output theo quy tắc hiện hành |

Nếu nhóm dùng ngôn ngữ hoặc framework khác, vẫn cần giữ nguyên trách nhiệm logic tương đương.

## 20. Gợi ý CLI

CLI tối thiểu:

```text
python -m video_analyzer.main \
  --media-metadata data/intermediate/media_metadata.json \
  --output-dir data/intermediate \
  --keyframe-dir data/keyframes
```

Output mong đợi:

```text
data/intermediate/clip_metadata.json
data/intermediate/video_analysis_log.json
data/keyframes/v01_c001_k01.jpg
data/keyframes/v01_c001_k02.jpg
data/keyframes/v01_c001_k03.jpg
```

CLI nên trả về:

* exit code `0` nếu xử lý thành công.
* exit code khác `0` nếu lỗi chặn pipeline.
* message ngắn gọn cho người dùng.
* log chi tiết hơn cho developer nếu cần debug.

CLI nên có thêm flag:

```text
--overwrite
```

Flag này cho phép ghi đè output cũ khi chạy lại cùng `project_id`.

## 21. Test cases bắt buộc

### 21.1. Test một video hợp lệ

Input:

```text
media_metadata.json
video_01.mp4
```

Kỳ vọng:

* Tạo được `clip_metadata.json`.
* Tạo được ít nhất một clip usable.
* Tạo được keyframe image files.
* Top-level có đúng `project_id`.
* Mỗi clip usable có đủ required fields.

### 21.2. Test nhiều video hợp lệ

Kỳ vọng:

* Tạo clip cho từng video usable.
* `video_id` trong mỗi clip map đúng về `media_metadata.json`.
* `clip_id` không trùng giữa các video.

### 21.3. Test video có status warning

Kỳ vọng:

* Video Analyzer vẫn xử lý video đó.
* Warning được ghi vào `video_analysis_log.json`.
* Nếu phân tích thành công, vẫn tạo clip metadata.

### 21.4. Test video có status error

Kỳ vọng:

* Module bỏ qua video đó.
* Không tạo clip usable từ video lỗi.
* Nếu không còn video usable nào, module dừng và báo lỗi.

### 21.5. Test timestamp hợp lệ

Kỳ vọng:

* `start >= 0`.
* `end > start`.
* `duration = end - start`.
* Clip không vượt quá duration video quá sai số cho phép.
* Keyframe timestamp nằm trong khoảng clip.

### 21.6. Test scene detection không tìm được boundary

Kỳ vọng:

* Module dùng fallback fixed-window nếu được cấu hình.
* Vẫn tạo được clip candidate hợp lệ.
* Ghi rõ fallback trong `video_analysis_log.json`.

### 21.7. Test clip quá ngắn

Kỳ vọng:

* Clip quá ngắn được gộp nếu hợp lý hoặc đánh dấu `status = too_short`.
* Không chọn clip quá ngắn làm usable mặc định nếu không đủ duration.

### 21.8. Test clip quá dài

Kỳ vọng:

* Clip dài được chia nhỏ nếu `split_long_clips = true`.
* Clip con có timestamp hợp lệ.
* `clip_id` giữ thứ tự thời gian.

### 21.9. Test keyframe path

Kỳ vọng:

* Mỗi keyframe item có `keyframe_id`, `timestamp`, `path`.
* File ảnh tại `path` tồn tại.
* Path là relative path.
* Không có path giả.

### 21.10. Test quality score

Kỳ vọng:

* `quality_score` là number trong `[0.0, 1.0]` hoặc `null`.
* Không dùng score ngoài khoảng.
* Không dùng `0` để thay cho "chưa tính".

### 21.11. Test status clip

Kỳ vọng:

* Mọi clip đều có `status`.
* `status` thuộc allowed values.
* Không sinh giá trị ngoài danh sách như `ready`, `warning`, `bad`, `normal`.

### 21.12. Test source_path

Kỳ vọng:

* Mỗi clip có `source_path` trong MVP.
* `source_path` là relative path.
* `source_path` trỏ về đúng video normalized tương ứng với `video_id`.
* File tại `source_path` tồn tại.

### 21.13. Test chạy lại module

Kỳ vọng:

* Nếu chạy lại không có `--overwrite` và output đã tồn tại, module dừng an toàn hoặc yêu cầu chọn output khác.
* Nếu chạy lại có `--overwrite`, module được phép ghi đè output cũ.
* Nếu input và rule detection không đổi, ID giữ ổn định.

## 22. Tiêu chí nghiệm thu

Module Video Analyzer được xem là đạt yêu cầu MVP khi:

1. Đọc được `media_metadata.json`.
2. Lấy đúng `videos[*].normalized_path`.
3. Chạy được với video có `status = ready` hoặc `warning`.
4. Bỏ qua đúng video có `status = error`.
5. Tạo được clip candidate từ video nguồn.
6. Tạo `clip_metadata.json` đúng schema hiện hành.
7. Mỗi clip có `clip_id`, `video_id`, `start`, `end`, `duration`, `keyframes`, `quality_score`.
8. Tất cả thời gian dùng giây.
9. Clip và keyframe timestamp hợp lệ.
10. `clip_id` ổn định nếu input và rule detection không đổi.
11. Mỗi clip usable có ít nhất một keyframe thật.
12. Keyframe path là relative path và file tồn tại.
13. `quality_score` là số từ `0.0` đến `1.0` hoặc `null`.
14. Mọi clip đều có `status` và giá trị thuộc allowed values.
15. Data Contract tổng để `status` là optional, nhưng implementation MVP phải ghi field này để tích hợp dễ hơn.
16. MVP nên ghi `source_path` cho mọi clip.
17. Clip `usable` và `low_quality` có thể đưa sang Matching Engine.
18. Clip `too_short` và `error` không được chọn mặc định trong MVP.
19. Tạo `video_analysis_log.json` để hỗ trợ debug.
20. Embedding Indexer có thể dùng keyframe để tạo embedding.
21. Matching Engine có thể dùng clip metadata để xếp hạng.
22. Review UI có thể hiển thị keyframe clip.
23. Renderer hoặc Timeline Planner có thể dùng timestamp để cắt video.
24. Có quy tắc rõ ràng khi chạy lại cùng `project_id`.

## 23. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 3 cần tự kiểm tra:

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc được media_metadata.json
[ ] Lấy đúng videos[*].normalized_path
[ ] Chỉ xử lý video ready/warning
[ ] Bỏ qua video error
[ ] Validate được video normalized tồn tại và đọc được
[ ] Chạy được scene/shot detection hoặc fallback fixed-window
[ ] Tạo được clip candidate
[ ] Không tạo clip có duration <= 0
[ ] Split được clip quá dài nếu cần
[ ] Xử lý được clip quá ngắn bằng merge hoặc status too_short
[ ] Sinh đúng clip_id dạng v01_c001, v01_c002, ...
[ ] Sinh đúng keyframe_id dạng v01_c001_k01, ...
[ ] Ghi source_path cho mọi clip trong MVP
[ ] Tính đúng start, end, duration bằng giây
[ ] Keyframe timestamp nằm trong clip
[ ] Keyframe path là relative path
[ ] File keyframe thật sự tồn tại
[ ] Tính được quality_score hoặc để null đúng quy tắc
[ ] Không bịa quality_score nếu chưa tính được
[ ] Gán status clip đúng allowed values cho mọi clip trong MVP
[ ] Ghi đúng clip_metadata.json
[ ] Ghi được video_analysis_log.json
[ ] Không hard-code path cá nhân
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương khi chạy lại
[ ] Có test với video mẫu ngắn
[ ] Output có thể đưa cho Embedding Indexer chạy tiếp; Matching Engine, Timeline Planner và Review UI có thể dùng ở các bước sau
```

## 24. Ghi chú triển khai MVP

Trong MVP, không cần làm Video Analyzer quá phức tạp. Ưu tiên quan trọng nhất là tạo được `clip_metadata.json` ổn định, có clip candidate hợp lệ, có keyframe thật và có quality score cơ bản.

Thứ tự ưu tiên nên là:

1. Đọc đúng video normalized từ `media_metadata.json`.
2. Tạo clip candidate hợp lệ.
3. Trích keyframe thật cho clip.
4. Ghi `clip_metadata.json` đúng schema.
5. Tính quality score cơ bản nếu làm được.
6. Đánh dấu clip quá ngắn, chất lượng thấp hoặc lỗi bằng status rõ ràng.
7. Ghi log dễ debug.
8. Tối ưu scene detection và quality scoring sau.

Nếu có tranh luận giữa việc detect scene thật chính xác và việc đảm bảo pipeline end-to-end chạy được, MVP nên ưu tiên pipeline chạy được trước. Scene detection có thể cải thiện dần miễn là contract không đổi.
