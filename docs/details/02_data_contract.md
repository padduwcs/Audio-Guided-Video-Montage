# 02. Data Contract

## 1. Mục tiêu của Data Contract

Data Contract là quy ước dữ liệu chung giữa các module trong hệ thống.

Mục tiêu:

* Đảm bảo các module có thể phát triển độc lập nhưng vẫn tích hợp được.
* Mỗi module biết rõ mình cần đọc file nào và phải xuất file nào.
* Giảm lỗi do lệch format dữ liệu khi merge code.
* Giúp leader dễ kiểm tra output của từng thành viên.
* Giúp debug pipeline thông qua các file JSON trung gian.
* Tạo nền cho UI, renderer và evaluation dùng chung dữ liệu.

Nguyên tắc quan trọng:

> Mỗi thành viên có thể tự chọn cách triển khai bên trong module, nhưng input/output phải tuân thủ Data Contract chung.

## 2. Quy ước chung

### 2.1. Định dạng file

Tất cả dữ liệu trung gian dùng JSON.

Mỗi file JSON nên có cấu trúc top-level như sau:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:00:00Z",
  "items": []
}
```

Không nên dùng mảng JSON trần như:

```json
[
  { "...": "..." }
]
```

Lý do: top-level object giúp thêm `schema_version`, `project_id`, `created_at`, `config`, `summary` mà không phá vỡ cấu trúc cũ.

### 2.2. Đơn vị thời gian

Tất cả thời gian dùng đơn vị **giây**.

Ví dụ:

```json
{
  "start": 12.5,
  "end": 18.2,
  "duration": 5.7
}
```

Quy tắc:

* `start >= 0`
* `end > start`
* `duration = end - start`
* Sai số nhỏ do làm tròn được chấp nhận, ví dụ `0.01s`

### 2.3. Score

Tất cả score dùng số thực từ `0.0` đến `1.0`.

Ví dụ:

```json
{
  "semantic_score": 0.84,
  "quality_score": 0.76,
  "final_score": 0.81
}
```

Quy ước:

* `0.0`: rất kém hoặc không có độ tin cậy.
* `1.0`: rất tốt hoặc rất tin cậy.
* Nếu chưa tính được score, dùng `null`, không tự đặt bừa `0`.

### 2.4. Confidence

Confidence dùng ba mức:

```text
high
medium
low
```

Ý nghĩa:

* `high`: hệ thống khá chắc, người dùng có thể không cần sửa.
* `medium`: nên xem lại.
* `low`: cần người dùng kiểm tra.

### 2.5. ID

ID phải ngắn gọn, ổn định và dễ map giữa các file.

Quy ước đề xuất:

```text
project_id: demo_01
video_id: video_01
audio_id: audio_01
segment_id: a001
clip_id: v01_c003
keyframe_id: v01_c003_k01
candidate_set_id: candidates_a001
timeline_item_id: t001_i01
```

Không dùng khoảng trắng trong ID.

### 2.6. Path

Path nên dùng đường dẫn tương đối tính từ root repo hoặc từ thư mục data đã thống nhất.

Ví dụ:

```json
{
  "path": "data/normalized/video_01.mp4"
}
```

Không nên hard-code đường dẫn tuyệt đối của máy cá nhân.

### 2.7. Required và Optional

Trong tài liệu này:

* `required`: bắt buộc phải có.
* `optional`: có thì tốt, không có vẫn chạy được.
* `nullable`: có thể nhận giá trị `null`.

Nếu module chưa tính được field optional thì có thể bỏ qua hoặc để `null`.

## 3. Tổng quan các file dữ liệu

| File                       | Module tạo                   | Module dùng                                 |
| -------------------------- | ---------------------------- | ------------------------------------------- |
| `media_metadata.json`      | Input Processor              | Audio, Video, Renderer, Integration         |
| `audio_segments.json`      | Audio Analyzer               | Matching, Timeline, UI, Evaluation          |
| `clip_metadata.json`       | Video Analyzer               | Embedding, Matching, Timeline, UI, Renderer |
| `embedding_metadata.json`  | Embedding Indexer            | Matching                                    |
| `matching_candidates.json` | Matching Engine              | Timeline, UI, Evaluation                    |
| `timeline.json`            | Timeline Planner / Review UI | Renderer, Evaluation                        |
| `render_config.json`       | User/System                  | Renderer                                    |
| `render_log.json`          | Renderer                     | Integration, Evaluation                     |
| `evaluation_report.json`   | Evaluation                   | Report/Demo                                 |

## 4. `media_metadata.json`

### 4.1. Vai trò

Lưu thông tin về media đầu vào sau khi kiểm tra hoặc chuẩn hóa.

File này giúp các module khác biết:

* Có những video nào.
* Audio chính nằm ở đâu.
* Duration, fps, resolution của từng file.
* File đã chuẩn hóa hay chưa.

### 4.2. Cấu trúc

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:00:00Z",
  "videos": [],
  "audio": {}
}
```

### 4.3. Video item

Required fields:

| Field             | Type    | Ý nghĩa                       |
| ----------------- | ------- | ----------------------------- |
| `video_id`        | string  | ID video nguồn                |
| `original_path`   | string  | Đường dẫn file gốc            |
| `normalized_path` | string  | Đường dẫn file đã chuẩn hóa   |
| `duration`        | number  | Thời lượng video, đơn vị giây |
| `fps`             | number  | Frame rate                    |
| `width`           | integer | Chiều rộng                    |
| `height`          | integer | Chiều cao                     |
| `has_audio`       | boolean | Video có audio gốc không      |
| `status`          | string  | Trạng thái xử lý              |

Optional fields:

| Field      | Type   | Ý nghĩa         |
| ---------- | ------ | --------------- |
| `codec`    | string | Codec video     |
| `bitrate`  | number | Bitrate         |
| `rotation` | number | Góc xoay nếu có |
| `notes`    | string | Ghi chú         |

Allowed `status`:

```text
ready
warning
error
```

### 4.4. Audio object

Required fields:

| Field             | Type    | Ý nghĩa                           |
| ----------------- | ------- | --------------------------------- |
| `audio_id`        | string  | ID audio thuyết minh              |
| `original_path`   | string  | Đường dẫn file audio gốc          |
| `normalized_path` | string  | Đường dẫn file audio đã chuẩn hóa |
| `duration`        | number  | Thời lượng audio                  |
| `sample_rate`     | integer | Sample rate                       |
| `channels`        | integer | Số kênh audio                     |
| `status`          | string  | Trạng thái xử lý                  |

### 4.5. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:00:00Z",
  "videos": [
    {
      "video_id": "video_01",
      "original_path": "data/raw/video_01.mp4",
      "normalized_path": "data/normalized/video_01.mp4",
      "duration": 125.4,
      "fps": 30,
      "width": 1920,
      "height": 1080,
      "has_audio": true,
      "codec": "h264",
      "status": "ready"
    }
  ],
  "audio": {
    "audio_id": "audio_01",
    "original_path": "data/raw/voiceover.mp3",
    "normalized_path": "data/normalized/voiceover.wav",
    "duration": 92.7,
    "sample_rate": 16000,
    "channels": 1,
    "status": "ready"
  }
}
```

## 5. `audio_segments.json`

### 5.1. Vai trò

Lưu transcript có timestamp và các audio segment dùng để matching với video.

Audio Analyzer tạo file này.

### 5.2. Cấu trúc

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "audio_id": "audio_01",
  "language": "vi",
  "created_at": "2026-06-11T10:05:00Z",
  "items": []
}
```

### 5.3. Segment item

Required fields:

| Field            | Type        | Ý nghĩa                     |
| ---------------- | ----------- | --------------------------- |
| `segment_id`     | string      | ID audio segment            |
| `start`          | number      | Thời điểm bắt đầu           |
| `end`            | number      | Thời điểm kết thúc          |
| `duration`       | number      | Thời lượng segment          |
| `text`           | string      | Transcript gốc              |
| `query`          | string      | Câu query dùng cho matching |
| `asr_confidence` | number/null | Độ tin cậy ASR nếu có       |

Optional fields:

| Field              | Type          | Ý nghĩa                                    |
| ------------------ | ------------- | ------------------------------------------ |
| `keywords`         | array[string] | Từ khóa chính                              |
| `translated_query` | string/null   | Query tiếng Anh nếu cần                    |
| `segment_type`     | string        | Loại segment                               |
| `needs_review`     | boolean       | Có cần người dùng xem lại transcript không |
| `notes`            | string        | Ghi chú                                    |

Allowed `segment_type`:

```text
description
action
transition
abstract
unknown
```

### 5.4. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "audio_id": "audio_01",
  "language": "vi",
  "created_at": "2026-06-11T10:05:00Z",
  "items": [
    {
      "segment_id": "a001",
      "start": 0.0,
      "end": 5.2,
      "duration": 5.2,
      "text": "Đây là khu vực cổng chính của khu tham quan.",
      "query": "khu vực cổng chính khu tham quan",
      "translated_query": "main entrance of tourist area",
      "keywords": ["cổng chính", "khu tham quan"],
      "segment_type": "description",
      "asr_confidence": 0.91,
      "needs_review": false
    }
  ]
}
```

## 6. `clip_metadata.json`

### 6.1. Vai trò

Lưu danh sách clip candidate được tách từ video nguồn.

Video Analyzer tạo file này.

### 6.2. Cấu trúc

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:10:00Z",
  "items": []
}
```

### 6.3. Clip item

Required fields:

| Field           | Type          | Ý nghĩa                              |
| --------------- | ------------- | ------------------------------------ |
| `clip_id`       | string        | ID clip candidate                    |
| `video_id`      | string        | Video nguồn chứa clip                |
| `start`         | number        | Thời điểm bắt đầu trong video nguồn  |
| `end`           | number        | Thời điểm kết thúc trong video nguồn |
| `duration`      | number        | Thời lượng clip                      |
| `keyframes`     | array[object] | Danh sách keyframe                   |
| `quality_score` | number/null   | Điểm chất lượng tổng hợp             |

Optional fields:

| Field          | Type          | Ý nghĩa                            |
| -------------- | ------------- | ---------------------------------- |
| `scene_index`  | integer       | Thứ tự scene/shot                  |
| `source_path`  | string        | Đường dẫn video nguồn đã chuẩn hóa |
| `content_tags` | array[string] | Tag mô tả nội dung nếu có          |
| `caption`      | string/null   | Mô tả ngắn clip nếu có             |
| `quality`      | object        | Chi tiết chất lượng                |
| `status`       | string        | Trạng thái clip                    |
| `notes`        | string        | Ghi chú                            |

Allowed `status`:

```text
usable
low_quality
too_short
error
```

### 6.4. Keyframe item

Required fields:

| Field         | Type   | Ý nghĩa                           |
| ------------- | ------ | --------------------------------- |
| `keyframe_id` | string | ID keyframe                       |
| `timestamp`   | number | Vị trí keyframe trong video nguồn |
| `path`        | string | Đường dẫn ảnh keyframe            |

Optional fields:

| Field           | Type        | Ý nghĩa           |
| --------------- | ----------- | ----------------- |
| `position`      | string      | Vị trí trong clip |
| `quality_score` | number/null | Chất lượng frame  |

Allowed `position`:

```text
start
middle
end
extra
```

### 6.5. Quality object

Optional fields:

| Field              | Type        | Ý nghĩa         |
| ------------------ | ----------- | --------------- |
| `blur_score`       | number/null | Độ nét          |
| `brightness_score` | number/null | Độ sáng         |
| `motion_score`     | number/null | Mức chuyển động |
| `stability_score`  | number/null | Độ ổn định      |
| `quality_score`    | number/null | Điểm tổng hợp   |

### 6.6. Ví dụ

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
      "caption": "Cảnh cổng vào khu tham quan với nhiều người đi qua.",
      "status": "usable"
    }
  ]
}
```

## 7. `embedding_metadata.json`

### 7.1. Vai trò

Lưu thông tin mapping giữa audio segment, clip/keyframe và embedding tương ứng.

File này không nhất thiết chứa trực tiếp vector lớn. Vector có thể lưu ở file riêng hoặc index riêng.

### 7.2. Cấu trúc

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "model": {},
  "created_at": "2026-06-11T10:15:00Z",
  "text_embeddings": [],
  "visual_embeddings": [],
  "index": {}
}
```

### 7.3. Model object

Required fields:

| Field       | Type    | Ý nghĩa             |
| ----------- | ------- | ------------------- |
| `name`      | string  | Tên model embedding |
| `type`      | string  | Loại model          |
| `dimension` | integer | Số chiều vector     |

Allowed `type`:

```text
text
image
multimodal
```

### 7.4. Text embedding item

Required fields:

| Field          | Type        | Ý nghĩa                        |
| -------------- | ----------- | ------------------------------ |
| `embedding_id` | string      | ID embedding                   |
| `segment_id`   | string      | Audio segment tương ứng        |
| `source_text`  | string      | Text dùng để embedding         |
| `vector_path`  | string/null | Đường dẫn vector nếu lưu riêng |

### 7.5. Visual embedding item

Required fields:

| Field          | Type        | Ý nghĩa                                        |
| -------------- | ----------- | ---------------------------------------------- |
| `embedding_id` | string      | ID embedding                                   |
| `clip_id`      | string      | Clip tương ứng                                 |
| `keyframe_id`  | string/null | Keyframe tương ứng nếu embedding theo keyframe |
| `vector_path`  | string/null | Đường dẫn vector nếu lưu riêng                 |

### 7.6. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "model": {
    "name": "clip-vit-base-patch32",
    "type": "multimodal",
    "dimension": 512
  },
  "created_at": "2026-06-11T10:15:00Z",
  "text_embeddings": [
    {
      "embedding_id": "emb_text_a001",
      "segment_id": "a001",
      "source_text": "main entrance of tourist area",
      "vector_path": "data/intermediate/embeddings/emb_text_a001.npy"
    }
  ],
  "visual_embeddings": [
    {
      "embedding_id": "emb_visual_v01_c003_k01",
      "clip_id": "v01_c003",
      "keyframe_id": "v01_c003_k01",
      "vector_path": "data/intermediate/embeddings/emb_visual_v01_c003_k01.npy"
    }
  ],
  "index": {
    "type": "faiss",
    "path": "data/intermediate/index/visual.index"
  }
}
```

## 8. `matching_candidates.json`

### 8.1. Vai trò

Lưu top-k clip phù hợp cho từng audio segment.

Matching Engine tạo file này.

### 8.2. Cấu trúc

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "top_k": 5,
  "created_at": "2026-06-11T10:20:00Z",
  "items": []
}
```

### 8.3. Candidate set item

Required fields:

| Field              | Type          | Ý nghĩa                 |
| ------------------ | ------------- | ----------------------- |
| `candidate_set_id` | string        | ID nhóm candidate       |
| `audio_segment_id` | string        | Segment được matching   |
| `selected_clip_id` | string/null   | Clip mặc định được chọn |
| `confidence`       | string        | Độ tin cậy tổng quát    |
| `candidates`       | array[object] | Danh sách top-k clip    |

Optional fields:

| Field           | Type    | Ý nghĩa                |
| --------------- | ------- | ---------------------- |
| `reason`        | string  | Lý do tổng quát        |
| `fallback_used` | boolean | Có dùng fallback không |
| `notes`         | string  | Ghi chú                |

### 8.4. Candidate item

Required fields:

| Field         | Type    | Ý nghĩa        |
| ------------- | ------- | -------------- |
| `rank`        | integer | Thứ hạng       |
| `clip_id`     | string  | Clip candidate |
| `final_score` | number  | Điểm tổng hợp  |

Optional fields:

| Field                  | Type        | Ý nghĩa              |
| ---------------------- | ----------- | -------------------- |
| `semantic_score`       | number/null | Điểm khớp nghĩa      |
| `visual_quality_score` | number/null | Điểm chất lượng hình |
| `duration_fit_score`   | number/null | Điểm khớp thời lượng |
| `continuity_score`     | number/null | Điểm nối cảnh        |
| `diversity_score`      | number/null | Điểm đa dạng         |
| `repetition_penalty`   | number/null | Điểm phạt lặp        |
| `bad_clip_penalty`     | number/null | Điểm phạt clip xấu   |
| `reason`               | string      | Lý do đề xuất        |

### 8.5. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "top_k": 5,
  "created_at": "2026-06-11T10:20:00Z",
  "items": [
    {
      "candidate_set_id": "candidates_a001",
      "audio_segment_id": "a001",
      "selected_clip_id": "v01_c003",
      "confidence": "high",
      "reason": "Clip rank 1 khớp nội dung tốt và chất lượng hình ổn.",
      "fallback_used": false,
      "candidates": [
        {
          "rank": 1,
          "clip_id": "v01_c003",
          "final_score": 0.84,
          "semantic_score": 0.88,
          "visual_quality_score": 0.78,
          "duration_fit_score": 0.80,
          "continuity_score": 0.70,
          "diversity_score": 0.75,
          "repetition_penalty": 0.0,
          "bad_clip_penalty": 0.0,
          "reason": "Khớp nội dung tốt, đủ thời lượng, hình tương đối rõ."
        }
      ]
    }
  ]
}
```

## 9. `timeline.json`

### 9.1. Vai trò

Lưu bản dựng video ở dạng dữ liệu.

Đây là file trung tâm của hệ thống.

Timeline Planner tạo bản đầu tiên. Review UI có thể cập nhật file này. Renderer đọc file này để xuất video cuối.

### 9.2. Cấu trúc

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "audio_id": "audio_01",
  "created_at": "2026-06-11T10:25:00Z",
  "updated_at": "2026-06-11T10:30:00Z",
  "render_settings": {},
  "items": []
}
```

### 9.3. Render settings

Required fields:

| Field    | Type    | Ý nghĩa                 |
| -------- | ------- | ----------------------- |
| `width`  | integer | Chiều rộng video output |
| `height` | integer | Chiều cao video output  |
| `fps`    | number  | FPS output              |
| `format` | string  | Định dạng output        |

Optional fields:

| Field                   | Type    | Ý nghĩa                |
| ----------------------- | ------- | ---------------------- |
| `default_transition`    | string  | Transition mặc định    |
| `crop_mode`             | string  | Cách scale/crop        |
| `keep_original_audio`   | boolean | Có giữ audio gốc không |
| `original_audio_volume` | number  | Âm lượng audio gốc     |

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

### 9.4. Timeline segment item

Required fields:

| Field            | Type          | Ý nghĩa                                  |
| ---------------- | ------------- | ---------------------------------------- |
| `segment_id`     | string        | ID audio segment                         |
| `audio_start`    | number        | Bắt đầu audio segment                    |
| `audio_end`      | number        | Kết thúc audio segment                   |
| `duration`       | number        | Thời lượng segment                       |
| `text`           | string        | Transcript                               |
| `confidence`     | string        | Confidence của lựa chọn hình             |
| `score`          | number/null   | Điểm tổng hợp                            |
| `visual_items`   | array[object] | Danh sách hình ảnh/clip dùng cho segment |
| `candidates_ref` | string/null   | Tham chiếu candidate set                 |

Optional fields:

| Field           | Type    | Ý nghĩa                          |
| --------------- | ------- | -------------------------------- |
| `needs_review`  | boolean | Có cần người dùng kiểm tra không |
| `fallback_used` | boolean | Có dùng fallback không           |
| `user_edited`   | boolean | Người dùng đã chỉnh chưa         |
| `notes`         | string  | Ghi chú                          |

### 9.5. Visual item

Required fields:

| Field              | Type   | Ý nghĩa                              |
| ------------------ | ------ | ------------------------------------ |
| `timeline_item_id` | string | ID item trên timeline                |
| `clip_id`          | string | Clip được dùng                       |
| `video_id`         | string | Video nguồn                          |
| `source_path`      | string | Đường dẫn video nguồn đã chuẩn hóa   |
| `clip_start`       | number | Bắt đầu cắt trong video nguồn        |
| `clip_end`         | number | Kết thúc cắt trong video nguồn       |
| `timeline_start`   | number | Vị trí bắt đầu trên timeline output  |
| `timeline_end`     | number | Vị trí kết thúc trên timeline output |
| `speed`            | number | Tốc độ phát                          |
| `transition`       | string | Kiểu transition                      |

Optional fields:

| Field                   | Type         | Ý nghĩa                               |
| ----------------------- | ------------ | ------------------------------------- |
| `effect`                | string/null  | Hiệu ứng đơn giản nếu có              |
| `crop_mode`             | string/null  | Override crop mode                    |
| `volume`                | number/null  | Âm lượng audio gốc của clip           |
| `source_candidate_rank` | integer/null | Clip này lấy từ rank nào trong top-k  |
| `locked`                | boolean      | Người dùng khóa không cho tự động đổi |
| `notes`                 | string       | Ghi chú                               |

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

### 9.6. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "audio_id": "audio_01",
  "created_at": "2026-06-11T10:25:00Z",
  "updated_at": "2026-06-11T10:30:00Z",
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
  "items": [
    {
      "segment_id": "a001",
      "audio_start": 0.0,
      "audio_end": 5.2,
      "duration": 5.2,
      "text": "Đây là khu vực cổng chính của khu tham quan.",
      "confidence": "high",
      "score": 0.84,
      "needs_review": false,
      "fallback_used": false,
      "user_edited": false,
      "candidates_ref": "candidates_a001",
      "visual_items": [
        {
          "timeline_item_id": "t001_i01",
          "clip_id": "v01_c003",
          "video_id": "video_01",
          "source_path": "data/normalized/video_01.mp4",
          "clip_start": 24.5,
          "clip_end": 29.7,
          "timeline_start": 0.0,
          "timeline_end": 5.2,
          "speed": 1.0,
          "transition": "cut",
          "effect": null,
          "crop_mode": "center_crop",
          "volume": 0.0,
          "source_candidate_rank": 1,
          "locked": false
        }
      ]
    }
  ]
}
```

## 10. `render_config.json`

### 10.1. Vai trò

Lưu cấu hình render nếu muốn tách khỏi `timeline.json`.

Trong MVP, có thể đặt render settings trực tiếp trong `timeline.json`. Nếu cần tách riêng, dùng `render_config.json`.

### 10.2. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "output": {
    "path": "data/final/final_video.mp4",
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "format": "mp4"
  },
  "audio": {
    "voiceover_path": "data/normalized/voiceover.wav",
    "keep_original_audio": false,
    "original_audio_volume": 0.0
  },
  "video": {
    "crop_mode": "center_crop",
    "default_transition": "cut"
  }
}
```

## 11. `render_log.json`

### 11.1. Vai trò

Renderer tạo file này để ghi lại quá trình render.

Dùng để debug khi render lỗi.

### 11.2. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "started_at": "2026-06-11T10:40:00Z",
  "finished_at": "2026-06-11T10:42:30Z",
  "status": "success",
  "output_path": "data/final/final_video.mp4",
  "duration": 92.7,
  "render_time": 150.0,
  "warnings": [],
  "errors": []
}
```

Allowed `status`:

```text
success
warning
failed
```

## 12. `evaluation_report.json`

### 12.1. Vai trò

Lưu kết quả đánh giá định lượng và định tính.

Evaluation có thể làm sau MVP, nhưng nên thống nhất sớm để phục vụ báo cáo.

### 12.2. Ví dụ

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T11:00:00Z",
  "metrics": {
    "segment_coverage": 1.0,
    "average_semantic_score": 0.76,
    "low_confidence_rate": 0.18,
    "repetition_rate": 0.12,
    "average_duration_error": 0.08,
    "user_edit_count": 4
  },
  "qualitative_scores": {
    "semantic_alignment": 4,
    "visual_quality": 4,
    "editing_rhythm": 3,
    "ease_of_editing": 4,
    "final_usefulness": 4
  },
  "notes": "Video cuối tương đối khớp audio, một số đoạn trừu tượng cần người dùng chỉnh clip."
}
```

## 13. Quy tắc mapping giữa các file

### 13.1. Mapping audio segment

```text
audio_segments.items[].segment_id
→ matching_candidates.items[].audio_segment_id
→ timeline.items[].segment_id
```

Nếu `segment_id` không khớp, Timeline Planner hoặc UI sẽ không biết candidate nào thuộc segment nào.

### 13.2. Mapping clip

```text
clip_metadata.items[].clip_id
→ matching_candidates.items[].candidates[].clip_id
→ timeline.items[].visual_items[].clip_id
```

Nếu `clip_id` không khớp, Renderer sẽ không biết cần cắt clip nào.

### 13.3. Mapping video

```text
media_metadata.videos[].video_id
→ clip_metadata.items[].video_id
→ timeline.items[].visual_items[].video_id
```

Nếu `video_id` không khớp, Renderer sẽ không tìm được video nguồn.

### 13.4. Mapping candidate set

```text
matching_candidates.items[].candidate_set_id
→ timeline.items[].candidates_ref
```

Mapping này giúp UI mở đúng danh sách top-k candidate cho từng segment.

## 14. Quy tắc kiểm tra dữ liệu

### 14.1. Kiểm tra `media_metadata.json`

Cần đảm bảo:

* Mỗi `video_id` là duy nhất.
* Mỗi `normalized_path` tồn tại.
* `duration > 0`.
* `fps > 0`.
* `width > 0`, `height > 0`.
* Audio chính tồn tại và `duration > 0`.

### 14.2. Kiểm tra `audio_segments.json`

Cần đảm bảo:

* Mỗi `segment_id` là duy nhất.
* `start >= 0`.
* `end > start`.
* Segment không bị overlap bất thường.
* `text` không rỗng.
* `query` không rỗng.
* `duration` khớp với `end - start`.

### 14.3. Kiểm tra `clip_metadata.json`

Cần đảm bảo:

* Mỗi `clip_id` là duy nhất.
* `video_id` tồn tại trong `media_metadata.json`.
* `start >= 0`.
* `end > start`.
* `end` không vượt quá duration của video nguồn.
* Mỗi clip có ít nhất một keyframe nếu dùng embedding hình ảnh.
* Keyframe path tồn tại.

### 14.4. Kiểm tra `matching_candidates.json`

Cần đảm bảo:

* Mỗi `audio_segment_id` tồn tại trong `audio_segments.json`.
* Mỗi `clip_id` tồn tại trong `clip_metadata.json`.
* `rank` bắt đầu từ 1 và tăng dần.
* `final_score` nằm trong `[0.0, 1.0]`.
* `selected_clip_id` nằm trong danh sách candidates hoặc là `null`.
* `confidence` thuộc `high`, `medium`, `low`.

### 14.5. Kiểm tra `timeline.json`

Cần đảm bảo:

* Mỗi `segment_id` tồn tại trong `audio_segments.json`.
* `audio_start`, `audio_end` khớp với audio segment.
* Mỗi `visual_items[].clip_id` tồn tại trong `clip_metadata.json`.
* `clip_start`, `clip_end` nằm trong khoảng của video nguồn.
* `timeline_start`, `timeline_end` liên tục và không overlap sai.
* `speed` nằm trong khoảng cho phép.
* Tổng timeline gần bằng duration audio.
* `source_path` tồn tại.
* `transition` thuộc danh sách cho phép.

## 15. Quy tắc khi UI chỉnh timeline

UI được phép chỉnh:

* `selected clip` thông qua `visual_items`.
* `clip_start`, `clip_end` nếu cần.
* `speed`.
* `transition`.
* `crop_mode`.
* `volume`.
* `user_edited`.
* `locked`.
* `updated_at`.

UI không nên chỉnh:

* `audio_start`, `audio_end` nếu chưa có chức năng sửa audio segment.
* `segment_id`.
* `video_id` nếu không đổi clip.
* Schema version.
* Các file video nguồn.

Khi người dùng đổi clip, UI cần đảm bảo:

* Clip mới tồn tại trong `clip_metadata.json`.
* Nếu clip đến từ top-k, lưu `source_candidate_rank`.
* Cập nhật `user_edited = true`.
* Không làm mất `candidates_ref`.

## 16. Quy tắc khi Renderer đọc timeline

Renderer chỉ tin vào `timeline.json` và media source.

Renderer cần kiểm tra trước khi render:

* `source_path` tồn tại.
* `clip_start < clip_end`.
* `clip_end` không vượt quá duration video.
* `timeline_start < timeline_end`.
* `speed` hợp lệ.
* Audio voice-over tồn tại.
* Output config hợp lệ.

Renderer không được tự chọn lại clip dựa trên score. Nếu timeline chọn clip nào, renderer dùng clip đó.

## 17. Quy tắc thay đổi schema

Nếu cần thay đổi schema:

1. Thảo luận với leader.
2. Cập nhật `docs/details/02_data_contract.md`.
3. Cập nhật file schema tương ứng trong `docs/schemas/`.
4. Cập nhật sample JSON trong `docs/samples/`.
5. Thông báo cho các module bị ảnh hưởng.
6. Chỉ merge code sau khi các module liên quan đã điều chỉnh.

Không tự ý đổi tên field trong code mà chưa cập nhật tài liệu.

## 18. Data Contract tối thiểu cho MVP

Trong MVP đầu tiên, bắt buộc cần ổn định các file sau:

```text
media_metadata.json
audio_segments.json
clip_metadata.json
matching_candidates.json
timeline.json
```

Các file có thể làm sau:

```text
embedding_metadata.json
render_log.json
evaluation_report.json
```

Tuy nhiên, ngay cả khi chưa triển khai đầy đủ, vẫn nên giữ tên file và ý nghĩa trong tài liệu để kiến trúc không bị lệch.

## 19. Kết luận

Data Contract là phần quan trọng nhất để nhóm có thể phát triển song song.

Mỗi module có thể dùng thư viện, model và cách xử lý khác nhau, nhưng phải đảm bảo:

* Đọc đúng input đã thống nhất.
* Xuất đúng output đã thống nhất.
* Giữ ID nhất quán giữa các file.
* Dùng đúng đơn vị thời gian, score và confidence.
* Không tự ý đổi schema khi chưa thống nhất.

Nguyên tắc cuối cùng:

**Nếu output của một module đúng Data Contract, module sau phải có thể đọc và sử dụng được mà không cần biết module trước được triển khai như thế nào.**
