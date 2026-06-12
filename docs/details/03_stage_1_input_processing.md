# 03. Stage 1 - Input Processing

## 1. Mục tiêu của stage

Stage 1 - Input Processing có nhiệm vụ tiếp nhận video nguồn và audio thuyết minh, kiểm tra tính hợp lệ, chuẩn hóa file nếu cần, trích metadata cơ bản và tạo `media_metadata.json` cho các stage phía sau.

Stage này là cổng vào của toàn bộ pipeline. Nếu dữ liệu đầu vào không được kiểm tra và chuẩn hóa tốt, các module sau như Audio Analyzer, Video Analyzer, Timeline Planner và Renderer sẽ dễ bị lỗi do lệch định dạng, thiếu metadata hoặc đường dẫn file không thống nhất.

Mục tiêu chính:

* Đảm bảo hệ thống nhận được ít nhất một video nguồn và một audio thuyết minh hợp lệ.
* Kiểm tra video/audio có đọc được, có thời lượng hợp lệ và có định dạng nằm trong phạm vi hỗ trợ.
* Trích metadata cơ bản của từng file media.
* Chuẩn hóa video/audio về dạng dễ xử lý trong pipeline.
* Sinh ID ổn định cho video và audio.
* Xuất `media_metadata.json` đúng Data Contract hiện hành.
* Lưu các file normalized vào cấu trúc thư mục thống nhất để các module sau sử dụng.

## 2. Vị trí trong pipeline

Stage này nằm ngay sau input ban đầu của người dùng:

```text
Input video/audio
        |
        v
Input Processor
        |
        |-- media_metadata.json
        |-- input_processing_log.json
        |-- normalized video files
        |-- normalized audio file
        |
        |--> Audio Analyzer
        |--> Video Analyzer
        |--> Timeline Planner (later consumer)
        |--> Review UI (later consumer)
        |--> Renderer (later consumer)
        |--> Integration pipeline (later consumer)
```

Các module phía sau không nên đọc trực tiếp file raw nếu không cần thiết. Thay vào đó, các module nên ưu tiên dùng đường dẫn trong `media_metadata.json`, đặc biệt là `normalized_path`.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Input Processor cần xử lý các phần sau:

1. Nhận danh sách video nguồn và audio thuyết minh.
2. Kiểm tra file có tồn tại và đọc được.
3. Kiểm tra định dạng file có nằm trong danh sách hỗ trợ.
4. Trích metadata bằng công cụ phù hợp, ví dụ FFprobe.
5. Kiểm tra duration, fps, width, height, sample rate, số kênh audio.
6. Chuẩn hóa video nếu cần.
7. Chuẩn hóa audio nếu cần.
8. Sinh ID cho từng video và audio.
9. Lưu file normalized vào thư mục output.
10. Xuất `media_metadata.json`.
11. Xuất `input_processing_log.json` để hỗ trợ debug nếu cần.

### 3.2. Stage này không làm

Input Processor không chịu trách nhiệm cho các phần sau:

* Không chạy ASR.
* Không tạo transcript.
* Không chia audio segment.
* Không detect scene/shot.
* Không trích keyframe.
* Không tính quality score cho clip.
* Không tạo embedding.
* Không matching audio với video.
* Không tạo `timeline.json`.
* Không render `final_video.mp4`.

Các phần trên thuộc về các module sau trong pipeline.

## 4. Input

### 4.1. Video nguồn

Input Processor nhận một hoặc nhiều video nguồn.

Định dạng hỗ trợ trong MVP:

```text
.mp4
.mov
.mkv
```

Yêu cầu tối thiểu:

* File tồn tại.
* File đọc được.
* Có duration lớn hơn `0`.
* Có stream video hợp lệ.
* Width và height lớn hơn `0`.
* FPS đọc được hoặc có thể suy ra được.

Video có thể có hoặc không có audio gốc. Audio gốc của video nguồn không phải kênh âm thanh chính của video cuối, nhưng thông tin `has_audio` vẫn cần ghi lại để Renderer có thể quyết định giữ, tắt hoặc giảm âm lượng audio gốc nếu cấu hình yêu cầu.

### 4.2. Audio thuyết minh

Input Processor nhận đúng một file audio thuyết minh chính.

Định dạng hỗ trợ trong MVP:

```text
.wav
.mp3
.m4a
```

Yêu cầu tối thiểu:

* File tồn tại.
* File đọc được.
* Có duration lớn hơn `0`.
* Có stream audio hợp lệ.
* Sample rate đọc được.
* Số kênh audio đọc được.

Audio thuyết minh là audio chính của video cuối. Các stage sau sẽ dùng audio này để:

* Chạy ASR.
* Chia audio segment.
* Căn thời lượng timeline.
* Ghép vào video final khi render.

### 4.3. Cấu hình chạy module

Cấu hình dưới đây là cấu hình nội bộ của Input Processor, không phải Data Contract bắt buộc giữa các module.

Ví dụ cấu hình:

```json
{
  "project_id": "demo_01",
  "video_paths": [
    "data/raw/video_01.mp4",
    "data/raw/video_02.mov"
  ],
  "audio_path": "data/raw/voiceover.mp3",
  "output_dir": "data",
  "normalize_video": true,
  "normalize_audio": true,
  "target_video": {
    "format": "mp4",
    "codec": "h264",
    "fps": 30,
    "preserve_original_audio": true
  },
  "target_audio": {
    "format": "wav",
    "sample_rate": 16000,
    "channels": 1
  }
}
```

Trong MVP, các giá trị mặc định nên dùng:

| Tham số                | Giá trị đề xuất |
| ---------------------- | --------------- |
| `normalize_video`      | `true`          |
| `normalize_audio`      | `true`          |
| `target_video.format`  | `mp4`           |
| `target_video.codec`   | `h264`          |
| `target_video.fps`     | `30`            |
| `target_video.preserve_original_audio` | `true` |
| `target_audio.format`  | `wav`           |
| `target_audio.sample_rate` | `16000`     |
| `target_audio.channels` | `1`            |

Ghi chú:

* Không bắt buộc resize video ở Stage 1 nếu chưa cần. Renderer sẽ chịu trách nhiệm scale/crop theo `timeline.json` và `render_settings`.
* Nếu muốn resize toàn bộ video về `1920x1080` ngay từ Stage 1, cần thống nhất trước vì việc này có thể làm tăng thời gian xử lý và giảm chất lượng nếu source có độ phân giải khác.
* Với MVP, ưu tiên chuẩn hóa codec, container và fps để các module sau đọc ổn định.

## 5. Output

Stage này tạo ba nhóm output chính:

```text
data/normalized/video_01.mp4
data/normalized/video_02.mp4
data/normalized/voiceover.wav
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
```

Trong đó:

* `data/normalized/` chứa các file video/audio đã chuẩn hóa.
* `data/intermediate/media_metadata.json` chứa metadata dùng chung cho pipeline.
* `data/intermediate/input_processing_log.json` chứa log xử lý chi tiết phục vụ debug và tích hợp.

Nếu repo thống nhất vị trí khác cho file JSON trung gian, có thể đổi đường dẫn lưu file, nhưng tên và schema của `media_metadata.json` phải giữ đúng Data Contract. `input_processing_log.json` là output phụ, không phải Data Contract chính giữa các module.

## 6. Data Contract: `media_metadata.json`

### 6.1. Vai trò

`media_metadata.json` mô tả toàn bộ media đầu vào sau khi được kiểm tra hoặc chuẩn hóa.

File này giúp các module sau biết:

* Dự án đang xử lý video nào.
* Audio thuyết minh nằm ở đâu.
* File raw và file normalized nằm ở đâu.
* Duration, fps, resolution của từng video.
* Sample rate và số kênh của audio.
* File nào sẵn sàng xử lý tiếp, file nào có cảnh báo hoặc lỗi.

### 6.2. Cấu trúc top-level

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:00:00Z",
  "videos": [],
  "audio": {}
}
```

Required fields:

| Field            | Type          | Ý nghĩa                          |
| ---------------- | ------------- | -------------------------------- |
| `schema_version` | string        | Phiên bản schema                 |
| `project_id`     | string        | ID dự án đang xử lý              |
| `created_at`     | string        | Thời điểm tạo file metadata      |
| `videos`         | array[object] | Danh sách video nguồn            |
| `audio`          | object        | Audio thuyết minh chính          |

Quy ước:

* `schema_version` dùng `"1.0"` trong MVP.
* `created_at` dùng ISO 8601, ưu tiên UTC.
* `videos` phải có ít nhất một item.
* `audio` phải có đúng một audio object.

### 6.3. Video item

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

### 6.4. Audio object

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

Allowed `status`:

```text
ready
warning
error
```

## 7. Quy tắc đặt ID

ID cần ngắn gọn, ổn định và dễ map giữa các file.

Với MVP, quy tắc đề xuất:

```text
project_id: demo_01
video_id: video_01, video_02, video_03, ...
audio_id: audio_01
```

Quy tắc sinh `video_id`:

* Nếu người dùng nhập nhiều video, đánh số theo thứ tự input.
* Nếu input lấy từ thư mục, nên sort tên file trước khi đánh số để kết quả ổn định.
* Không dùng tên file gốc làm ID chính vì tên file có thể chứa dấu tiếng Việt, khoảng trắng hoặc ký tự đặc biệt.

Quy tắc sinh `audio_id`:

* MVP chỉ có một audio thuyết minh chính, dùng `audio_01`.

Không dùng khoảng trắng trong ID.

## 8. Quy tắc path

Tất cả path trong `media_metadata.json` nên dùng đường dẫn tương đối.

Ví dụ:

```json
{
  "original_path": "data/raw/video_01.mp4",
  "normalized_path": "data/normalized/video_01.mp4"
}
```

Không nên ghi path tuyệt đối như:

```text
C:/Users/Name/Desktop/project/data/raw/video_01.mp4
/home/user/project/data/raw/video_01.mp4
```

Lý do:

* Dễ chạy trên máy thành viên khác.
* Dễ demo trên môi trường khác.
* Dễ đưa vào integration pipeline.
* Tránh lỗi do đường dẫn cá nhân.

## 9. Quy trình xử lý đề xuất

### 9.1. Bước 1 - Nhận input

Input Processor nhận:

* `project_id`
* danh sách `video_paths`
* `audio_path`
* cấu hình normalize nếu có

Kiểm tra ban đầu:

* `video_paths` không được rỗng.
* `audio_path` phải tồn tại.
* Không nhận thư mục thay cho file, trừ khi integration pipeline có bước expand thư mục thành danh sách file.

### 9.2. Bước 2 - Validate file

Với từng video:

* Kiểm tra file tồn tại.
* Kiểm tra extension có thuộc `.mp4`, `.mov`, `.mkv`.
* Kiểm tra file có đọc được bằng FFprobe hoặc thư viện tương đương.
* Kiểm tra có video stream.
* Kiểm tra duration lớn hơn `0`.
* Kiểm tra width, height lớn hơn `0`.
* Kiểm tra fps có đọc được.

Với audio:

* Kiểm tra file tồn tại.
* Kiểm tra extension có thuộc `.wav`, `.mp3`, `.m4a`.
* Kiểm tra file có đọc được.
* Kiểm tra có audio stream.
* Kiểm tra duration lớn hơn `0`.
* Kiểm tra sample rate và channels có đọc được.

### 9.3. Bước 3 - Trích metadata gốc

Metadata video cần lấy:

* duration
* fps
* width
* height
* codec nếu có
* bitrate nếu có
* rotation nếu có
* có audio stream hay không

Metadata audio cần lấy:

* duration
* sample rate
* channels
* codec nếu cần ghi vào log nội bộ
* bitrate nếu cần ghi vào log nội bộ

Metadata gốc nên được lưu vào `input_processing_log.json` để debug. Không đưa `original_metadata` vào `media_metadata.json` trong MVP, vì `media_metadata.json` là contract chính cho các module sau và nên giữ gọn theo schema hiện hành.

### 9.4. Bước 4 - Chuẩn hóa video

Nếu `normalize_video = true`, mỗi video nên được chuyển về dạng dễ xử lý:

```text
container: mp4
video codec: h264
fps: 30
audio: giữ audio stream gốc nếu video có audio
```

Output:

```text
data/normalized/video_01.mp4
data/normalized/video_02.mp4
```

Gợi ý xử lý:

* Nếu video đã đúng format, có thể copy sang `data/normalized/` thay vì transcode lại.
* Mặc định giữ audio stream gốc trong normalized video nếu video có audio.
* Renderer sẽ quyết định dùng, tắt hoặc giảm âm lượng audio gốc dựa trên `timeline.json` hoặc `render_config.json`.
* Nếu Stage 1 loại bỏ audio gốc khỏi normalized video, Renderer sẽ không thể hỗ trợ tính năng giữ audio gốc cho video đó.
* Nếu video có rotation metadata, cần xử lý để output hiển thị đúng chiều.
* Nếu fps là variable frame rate, nên xuất về constant frame rate để cắt ghép ổn định hơn.
* Không tự ý cắt ngắn video ở Stage 1.
* Không tự ý loại bỏ video chỉ vì video dài hơn audio.
* Không tự ý loại bỏ video chỉ vì video ngắn hơn audio.

### 9.5. Bước 5 - Chuẩn hóa audio

Nếu `normalize_audio = true`, audio thuyết minh nên được chuyển về:

```text
format: wav
sample rate: 16000
channels: 1
```

Output:

```text
data/normalized/voiceover.wav
```

Gợi ý xử lý:

* Chuẩn hóa về mono giúp ASR ổn định hơn.
* Sample rate `16000` phù hợp cho nhiều pipeline speech-to-text trong MVP.
* Không cắt bỏ khoảng lặng ở đầu hoặc cuối audio trong Stage 1, vì việc đó sẽ làm lệch timestamp so với file gốc.
* Không thay đổi tốc độ audio.
* Không tự động lọc nhiễu mạnh nếu chưa thống nhất, vì có thể làm ảnh hưởng chất lượng giọng nói.

### 9.6. Bước 6 - Trích metadata sau chuẩn hóa

Sau khi normalize, cần đọc lại metadata từ file normalized, không chỉ dùng metadata của file raw.

Lý do:

* FPS có thể đã thay đổi.
* Codec có thể đã thay đổi.
* Audio sample rate/channels có thể đã thay đổi.
* Duration có thể lệch rất nhỏ sau khi transcode.

`media_metadata.json` nên ghi metadata của file normalized cho các field như `duration`, `fps`, `width`, `height`, `sample_rate`, `channels`.

### 9.7. Bước 7 - Ghi `media_metadata.json`

Tạo file JSON theo đúng schema:

```text
data/intermediate/media_metadata.json
```

Trước khi ghi file, cần kiểm tra:

* Có đủ top-level fields.
* `videos` có ít nhất một item.
* `audio` không rỗng.
* Mỗi video có đủ required fields.
* Audio có đủ required fields.
* Tất cả path là relative path.
* Tất cả duration dùng đơn vị giây.
* `status` chỉ dùng `ready`, `warning`, `error`.

Sau khi ghi `media_metadata.json`, nên ghi thêm `input_processing_log.json` để lưu thông tin debug như file nào được copy, file nào được transcode và metadata gốc trước normalize.

## 10. Quy tắc status và lỗi

Nguyên tắc tích hợp:

```text
Media có status = ready hoặc warning được xem là usable.
Chỉ media có status = error mới bị loại khỏi pipeline.
```

Các module sau như Audio Analyzer, Video Analyzer, Timeline Planner và Renderer được phép sử dụng media có `status = ready` hoặc `status = warning`.

`warning` có nghĩa là media vẫn xử lý được nhưng có điểm cần lưu ý. `warning` không có nghĩa là media bị lỗi hoặc phải bị bỏ qua.

### 10.1. `ready`

Dùng `ready` khi file đã xử lý thành công và có thể đưa sang stage sau.

Ví dụ:

* Video đọc được, có duration hợp lệ, đã có normalized file.
* Audio đọc được, có duration hợp lệ, đã có normalized file.
* Video không có audio gốc nhưng visual stream hợp lệ.

Với bài toán này, audio gốc của video nguồn không bắt buộc vì voice-over là audio chính của video cuối. Vì vậy, `has_audio = false` không tự động làm video chuyển sang `warning`.

### 10.2. `warning`

Dùng `warning` khi file vẫn có thể xử lý tiếp nhưng có vấn đề cần ghi chú.

Ví dụ video:

* FPS không đúng target nhưng vẫn đọc được.
* Resolution quá thấp nhưng vẫn có thể dùng.
* Video không có audio gốc trong khi cấu hình render hoặc demo yêu cầu giữ audio gốc.
* Bitrate thấp.
* Có rotation metadata và đã được xử lý.
* Normalize thành công nhưng có thay đổi đáng kể so với file gốc, ví dụ đổi FPS từ `29.97` sang `30`.

Ví dụ audio:

* Audio sample rate gốc thấp.
* Audio nhiều kênh và đã được convert về mono.
* Duration audio dài hơn tổng duration video nguồn.

`warning` không nhất thiết chặn pipeline.

### 10.3. `error`

Dùng `error` khi file không thể dùng cho pipeline.

Ví dụ video:

* File không tồn tại.
* File không đọc được.
* Không có video stream.
* Duration bằng `0` hoặc không đọc được.
* Normalize thất bại.

Ví dụ audio:

* File không tồn tại.
* File không đọc được.
* Không có audio stream.
* Duration bằng `0` hoặc không đọc được.
* Normalize thất bại.

Nếu audio có `status = error`, pipeline phải dừng vì audio là input bắt buộc.

Nếu một video có `status = error` nhưng vẫn còn video khác `ready` hoặc `warning`, integration pipeline có thể cho chạy tiếp, nhưng cần báo rõ trong log. Nếu tất cả video đều `error`, pipeline phải dừng.

## 11. Output phụ: `input_processing_log.json`

### 11.1. Vai trò

`input_processing_log.json` là file log phụ của Stage 1, dùng để debug và hỗ trợ leader khi tích hợp pipeline.

File này không phải Data Contract chính giữa các module. Các module sau không nên phụ thuộc vào file này để chạy logic chính.

Nên dùng file này để ghi:

* File nào được normalize.
* File nào được copy thẳng vì đã đúng format.
* File nào bị lỗi.
* Cảnh báo về codec, FPS, resolution, rotation.
* Metadata gốc trước khi normalize.
* Metadata sau khi normalize.
* Lệnh FFmpeg/FFprobe hoặc tham số xử lý nếu cần debug.
* Lý do gán `status = warning` hoặc `status = error`.

### 11.2. Cấu trúc đề xuất

Đây là cấu trúc đề xuất, không bắt buộc phải xem là schema liên module:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:00:00Z",
  "items": [
    {
      "video_id": "video_01",
      "media_type": "video",
      "original_path": "data/raw/video_01.mp4",
      "normalized_path": "data/normalized/video_01.mp4",
      "action": "transcoded",
      "status": "ready",
      "original_metadata": {
        "duration": 125.3,
        "fps": 29.97,
        "width": 1920,
        "height": 1080,
        "codec": "hevc",
        "has_audio": true
      },
      "normalized_metadata": {
        "duration": 125.4,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "codec": "h264",
        "has_audio": true
      },
      "warnings": [],
      "error": null
    }
  ]
}
```

Allowed `action` đề xuất:

```text
copied
transcoded
skipped
failed
```

### 11.3. Nguyên tắc sử dụng

`media_metadata.json` là nguồn dữ liệu chính cho các module sau. `input_processing_log.json` chỉ dùng để:

* Debug khi output bị lệch mong đợi.
* Kiểm tra vì sao một media bị `warning` hoặc `error`.
* So sánh metadata gốc và metadata sau normalize.
* Hỗ trợ viết báo cáo hoặc demo quy trình xử lý.

Nếu `media_metadata.json` và `input_processing_log.json` có thông tin mâu thuẫn, các module pipeline phải ưu tiên `media_metadata.json`.

## 12. Ví dụ `media_metadata.json`

**Mẫu chuẩn:** `docs/samples/media_metadata_sample.json`.

Ví dụ dưới đây khớp sample dùng cho validate/tích hợp (`audio.duration = 16.0s` = tổng thời lượng `audio_segments`):

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
    },
    {
      "video_id": "video_02",
      "original_path": "data/raw/video_02.mp4",
      "normalized_path": "data/normalized/video_02.mp4",
      "duration": 88.0,
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
    "duration": 16.0,
    "sample_rate": 16000,
    "channels": 1,
    "status": "ready"
  }
}
```

## 13. Điều kiện handoff output

Stage 1 được phép bàn giao `media_metadata.json` cho Audio Analyzer và Video Analyzer; các module về sau như Timeline Planner, Review UI, Renderer và Integration pipeline có thể dùng cùng output này khi thỏa các điều kiện sau:

```text
audio.status != error
có ít nhất một video có status != error
mọi normalized_path của media usable đều tồn tại
media_metadata.json parse được
media_metadata.json có đủ required fields
```

Trong đó, media usable là media có:

```text
status = ready
status = warning
```

Quy tắc handoff cụ thể:

* Audio Analyzer chỉ được chạy nếu `audio.status` là `ready` hoặc `warning`.
* Video Analyzer chỉ xử lý các video có `status` là `ready` hoặc `warning`.
* Video có `status = error` phải bị bỏ qua ở stage sau.
* Nếu không có video usable nào, pipeline phải dừng.
* Nếu audio bị `error`, pipeline phải dừng dù video hợp lệ.
* Nếu có media `warning`, pipeline vẫn chạy tiếp nhưng UI/log nên hiển thị cảnh báo để người dùng hoặc leader biết.

Stage sau không cần tự validate lại toàn bộ raw input, nhưng vẫn nên kiểm tra file trong `normalized_path` có tồn tại trước khi xử lý để tránh lỗi runtime.

## 14. Quan hệ với các module khác

### 14.1. Audio Analyzer

Audio Analyzer đọc:

```text
media_metadata.json
audio.normalized_path
```

Audio Analyzer không cần tự tìm file audio trong thư mục raw.

### 14.2. Video Analyzer

Video Analyzer đọc:

```text
media_metadata.json
videos[*].normalized_path
```

Video Analyzer dùng `video_id` từ `media_metadata.json` để tạo `clip_id`.

Ví dụ:

```text
video_id = video_01
clip_id = v01_c003
```

### 14.3. Timeline Planner

Timeline Planner đọc `media_metadata.json` để biết:

* Duration audio tổng.
* Duration video nguồn.
* Video nào đang usable, tức là `ready` hoặc `warning`.
* Đường dẫn video normalized phục vụ mapping timeline.

### 14.4. Renderer

Renderer đọc:

```text
timeline.json
media_metadata.json
normalized video files
normalized audio file
```

Renderer không chạy lại normalize. Renderer chỉ dùng các file đã được Input Processor tạo.

### 14.5. Integration pipeline

Integration pipeline dùng `media_metadata.json` để quyết định:

* Có được chạy stage tiếp theo không.
* Có bao nhiêu video usable.
* Audio có sẵn sàng xử lý không.
* Có cần báo lỗi đầu vào cho người dùng không.

## 15. Ràng buộc kỹ thuật

### 15.1. Thời gian

Tất cả duration trong `media_metadata.json` dùng đơn vị giây.

Ví dụ:

```json
{
  "duration": 125.4
}
```

Không dùng milliseconds trong Data Contract.

### 15.2. Làm tròn số

Duration và fps có thể làm tròn ở mức hợp lý.

Gợi ý:

* `duration`: làm tròn 2 hoặc 3 chữ số thập phân.
* `fps`: giữ số nguyên nếu là `24`, `25`, `30`, `60`; giữ số thập phân nếu source là `29.97`.

### 15.3. Không sửa nội dung media ngoài phạm vi normalize

Stage 1 không được:

* Cắt bỏ đoạn đầu/cuối video.
* Cắt bỏ khoảng lặng audio.
* Thay đổi tốc độ audio.
* Thay đổi thứ tự video input.
* Tự loại video vì nội dung không liên quan.

Việc chọn đoạn nào dùng trong final video thuộc về Video Analyzer, Matching Engine và Timeline Planner.

### 15.4. Không hard-code đường dẫn máy cá nhân

Tất cả path trong JSON phải tương đối.

Nếu code cần dùng absolute path khi chạy FFmpeg/FFprobe, chỉ dùng nội bộ trong runtime, không ghi absolute path vào JSON output.

## 16. Re-run behavior

Input Processor cần có quy tắc rõ ràng khi chạy lại với cùng `project_id`.

### 16.1. Mục tiêu

Chạy lại module không được làm ID thay đổi bất ngờ hoặc tạo nhiều file khó kiểm soát.

Yêu cầu:

* Nếu thứ tự input không đổi, `video_id` và `audio_id` phải giữ ổn định.
* `media_metadata.json` mới phải phản ánh đúng output hiện tại.
* Không tạo nhiều bản normalized trùng nghĩa nếu không cần.
* Không ghi đè file quan trọng nếu người chạy chưa cho phép.

### 16.2. Quy tắc đề xuất

Nếu chạy lại với cùng `project_id`:

* Nếu có flag `--overwrite`, module được phép ghi đè normalized files, `media_metadata.json` và `input_processing_log.json`.
* Nếu không có `--overwrite`, module nên báo output đã tồn tại và dừng an toàn, hoặc yêu cầu người dùng chọn `project_id` khác.
* Nếu muốn hỗ trợ nhiều lần chạy trong cùng project, có thể tạo thư mục run riêng, nhưng phải thống nhất ở Integration pipeline trước.

Quy tắc ID:

* `video_id` dựa trên thứ tự input đã ổn định.
* `audio_id` vẫn là `audio_01` trong MVP.
* Không sinh ID theo timestamp, vì sẽ làm các file sau khó map lại.

### 16.3. Khi nào nên overwrite

Chỉ nên dùng overwrite khi:

* Người dùng đổi file input nhưng vẫn muốn giữ cùng `project_id`.
* Người dùng đổi cấu hình normalize.
* Output trước đó bị lỗi và cần chạy lại sạch.

Nếu đã có các stage sau chạy dựa trên `media_metadata.json` cũ, cần cân nhắc chạy lại toàn bộ pipeline từ Stage 1 để tránh lệch path, duration hoặc metadata.

## 17. Gợi ý cấu trúc code

Đây là gợi ý tổ chức module, không bắt buộc nếu nhóm đã có style code riêng.

```text
input_processor/
│
├── __init__.py
├── main.py
├── config.py
├── media_probe.py
├── normalizer.py
├── metadata_writer.py
└── validator.py
```

Vai trò từng file:

| File                 | Vai trò                                          |
| -------------------- | ----------------------------------------------- |
| `main.py`            | Entry point chạy module                         |
| `config.py`          | Đọc và validate cấu hình chạy module            |
| `media_probe.py`     | Lấy metadata bằng FFprobe hoặc thư viện tương đương |
| `normalizer.py`      | Chuẩn hóa video/audio                           |
| `metadata_writer.py` | Tạo và ghi `media_metadata.json`                |
| `validator.py`       | Kiểm tra input và output theo quy tắc hiện hành |

Nếu nhóm dùng ngôn ngữ hoặc framework khác, vẫn cần giữ nguyên trách nhiệm logic tương đương.

## 18. Gợi ý CLI

CLI tối thiểu:

```text
python -m input_processor.main \
  --project-id demo_01 \
  --videos data/raw/video_01.mp4 data/raw/video_02.mov \
  --audio data/raw/voiceover.mp3 \
  --output-dir data
```

Output mong đợi:

```text
data/normalized/video_01.mp4
data/normalized/video_02.mp4
data/normalized/voiceover.wav
data/intermediate/media_metadata.json
data/intermediate/input_processing_log.json
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

## 19. Test cases bắt buộc

### 19.1. Test một video và một audio hợp lệ

Input:

```text
video_01.mp4
voiceover.mp3
```

Kỳ vọng:

* Tạo được video normalized.
* Tạo được audio normalized.
* Tạo được `media_metadata.json`.
* Video có `status = ready`.
* Audio có `status = ready`.

### 19.2. Test nhiều video và một audio hợp lệ

Input:

```text
video_01.mp4
video_02.mov
voiceover.mp3
```

Kỳ vọng:

* Tạo đủ file normalized cho từng video.
* ID video lần lượt là `video_01`, `video_02`.
* `videos` trong metadata có đúng số lượng input.

### 19.3. Test video không có audio gốc

Kỳ vọng:

* `has_audio = false`.
* `status = ready` nếu visual stream hợp lệ.
* Pipeline không dừng chỉ vì video nguồn không có audio gốc.
* Chỉ dùng `warning` nếu cấu hình render/demo yêu cầu giữ audio gốc nhưng video không có audio gốc.

### 19.4. Test file audio không tồn tại

Kỳ vọng:

* Module báo lỗi rõ ràng.
* Pipeline dừng.
* Không tạo metadata giả với audio `ready`.

### 19.5. Test file video lỗi nhưng vẫn còn video hợp lệ

Input:

```text
valid_video.mp4
broken_video.mp4
voiceover.mp3
```

Kỳ vọng:

* Video hợp lệ vẫn được xử lý.
* Video lỗi được ghi nhận trong log.
* Nếu metadata vẫn ghi video lỗi, `status = error`.
* Integration pipeline có thể chạy tiếp nếu còn ít nhất một video `ready` hoặc `warning`.

### 19.6. Test path output

Kỳ vọng:

* `original_path` là relative path.
* `normalized_path` là relative path.
* Không có absolute path trong `media_metadata.json`.

### 19.7. Test schema required fields

Kỳ vọng:

* Top-level có đủ `schema_version`, `project_id`, `created_at`, `videos`, `audio`.
* Mỗi video có đủ required fields.
* Audio có đủ required fields.
* Không dùng mảng JSON trần ở top-level.

### 19.8. Test media `warning` vẫn được handoff

Kỳ vọng:

* Video hoặc audio có `status = warning` vẫn được xem là usable.
* Stage sau chỉ bỏ qua media có `status = error`.
* Integration pipeline không dừng nếu audio không lỗi và còn ít nhất một video usable.

### 19.9. Test giữ audio gốc trong normalized video

Input:

```text
video_has_audio.mp4
voiceover.mp3
```

Kỳ vọng:

* Nếu video nguồn có audio gốc, normalized video vẫn giữ audio stream đó theo mặc định.
* `has_audio = true`.
* Renderer vẫn có khả năng bật/tắt hoặc giảm âm lượng audio gốc ở stage sau.

### 19.10. Test chạy lại module

Kỳ vọng:

* Nếu chạy lại không có `--overwrite` và output đã tồn tại, module dừng an toàn hoặc yêu cầu chọn `project_id` khác.
* Nếu chạy lại có `--overwrite`, module được phép ghi đè output cũ.
* Nếu thứ tự input không đổi, ID vẫn giữ ổn định.

## 20. Tiêu chí nghiệm thu

Module Input Processor được xem là đạt yêu cầu MVP khi:

1. Chạy được với ít nhất một video và một audio hợp lệ.
2. Chạy được với nhiều video nguồn.
3. Tạo đúng file normalized cho video và audio.
4. Tạo `media_metadata.json` đúng schema hiện hành.
5. Tạo `input_processing_log.json` để hỗ trợ debug.
6. Tất cả thời gian trong JSON dùng giây.
7. Tất cả path trong JSON là relative path.
8. ID video/audio ổn định và không có khoảng trắng.
9. Có phân biệt được `ready`, `warning`, `error`.
10. Media `ready` và `warning` đều được xem là usable.
11. Chỉ media `error` mới bị loại khỏi pipeline.
12. Video không có audio gốc vẫn `ready` nếu visual stream hợp lệ.
13. Normalized video mặc định giữ audio gốc nếu video nguồn có audio.
14. Lỗi audio bắt buộc làm pipeline dừng.
15. Một video lỗi không làm pipeline dừng nếu vẫn còn video khác usable.
16. Có quy tắc rõ ràng khi chạy lại cùng `project_id`.
17. Audio Analyzer có thể đọc `audio.normalized_path` để chạy tiếp.
18. Video Analyzer có thể đọc `videos[*].normalized_path` để chạy tiếp.
19. Renderer có thể dùng metadata để tìm normalized media khi render.

## 21. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 1 cần tự kiểm tra:

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Nhận được một hoặc nhiều video input
[ ] Nhận được một audio voice-over input
[ ] Validate được file tồn tại và đọc được
[ ] Lấy được metadata video
[ ] Lấy được metadata audio
[ ] Normalize được video sang output thống nhất
[ ] Normalize được audio sang output thống nhất
[ ] Sinh đúng video_id và audio_id
[ ] Ghi đúng media_metadata.json
[ ] Ghi được input_processing_log.json
[ ] Không ghi absolute path vào JSON
[ ] Không dùng đơn vị milliseconds trong JSON
[ ] Status ready/warning/error được dùng đúng quy tắc
[ ] Media warning vẫn được xem là usable
[ ] Video không có audio gốc vẫn ready nếu hình ảnh hợp lệ
[ ] Normalized video giữ audio gốc nếu source có audio
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương khi chạy lại
[ ] Có xử lý lỗi input rõ ràng
[ ] Có test với dữ liệu mẫu nhỏ
[ ] Output có thể đưa cho Audio Analyzer và Video Analyzer chạy tiếp
```

## 22. Ghi chú triển khai MVP

Trong MVP, không cần làm Input Processor quá phức tạp. Ưu tiên quan trọng nhất là output ổn định và đúng contract.

Thứ tự ưu tiên nên là:

1. Validate input chắc chắn.
2. Lấy metadata đúng.
3. Ghi `media_metadata.json` đúng schema.
4. Normalize audio/video ở mức cơ bản.
5. Log lỗi dễ hiểu.
6. Tối ưu tốc độ xử lý sau.

Nếu có tranh luận giữa việc xử lý nhiều edge case và việc đảm bảo pipeline end-to-end chạy được, MVP nên ưu tiên pipeline chạy được trước, miễn là lỗi và giới hạn được ghi rõ trong `notes` hoặc log.
