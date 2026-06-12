# 10. Stage 8 - Renderer

## 1. Mục tiêu của stage

Stage 8 - Renderer có nhiệm vụ xuất video cuối cùng từ `timeline.json` đã được Timeline Planner tạo và Review UI chỉnh sửa.

Renderer là stage thực thi bản dựng. Renderer không chọn clip, không tính score và không quyết định clip nào phù hợp với audio. Renderer render theo timeline hợp lệ và media source đã chuẩn hóa, cắt clip, chỉnh speed, scale/crop, ghép các đoạn video, xử lý audio và xuất `final_video.mp4`.

Mục tiêu chính:

* Đọc `timeline.json`.
* Đọc `media_metadata.json` để resolve audio thuyết minh và media đã chuẩn hóa nếu cần.
* Đọc `render_config.json` nếu project tách config render khỏi timeline.
* Đọc `clip_metadata.json` nếu cần validate clip range.
* Validate timeline trước khi render.
* Cắt từng visual item theo `clip_start` và `clip_end`.
* Điều chỉnh `speed`.
* Scale/crop về resolution đầu ra.
* Áp dụng transition cơ bản.
* Ghép visual items theo `timeline_start` và `timeline_end`.
* Dùng voice-over làm audio chính.
* Tắt hoặc giảm âm lượng audio gốc của video theo setting.
* Xuất `final_video.mp4`.
* Xuất `render_log.json` để debug.

## 2. Vị trí trong pipeline

Stage này nằm sau Review UI và trước Evaluation:

```text
Review UI       -- timeline.json (đã cập nhật) --\
Input Processor -- media_metadata.json ---------\
Input Processor -- normalized video files ------\
Input Processor -- normalized audio file -------+--> Renderer
Video Analyzer  -- clip_metadata.json ----------/
User/System     -- render_config.json (optional)/
                                                   |
                                                   |-- final_video.mp4
                                                   |-- render_log.json
                                                   |
                                                   v
                                                Evaluation
```

Renderer là module cuối cùng tạo artifact video. Các module trước có thể tạo dữ liệu chưa hoàn hảo, nhưng Renderer chỉ nên render khi timeline đạt điều kiện kỹ thuật tối thiểu.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Renderer cần xử lý các phần sau:

1. Load `timeline.json`.
2. Load `media_metadata.json` hoặc resolve audio/video paths từ config.
3. Load `render_config.json` nếu có.
4. Load `clip_metadata.json` nếu dùng để validate range clip.
5. Validate `project_id`.
6. Validate `render_settings`.
7. Validate `timeline.items[]`.
8. Validate từng `visual_items[]`.
9. Kiểm tra media source tồn tại.
10. Tạo render plan nội bộ từ timeline.
11. Cắt video theo `clip_start` và `clip_end`.
12. Apply speed theo `visual_items[].speed`.
13. Resize/crop theo `crop_mode`.
14. Apply transition nếu được hỗ trợ.
15. Ghép visual items theo thứ tự timeline.
16. Ghép voice-over làm audio chính.
17. Mix audio gốc nếu được bật.
18. Xuất video cuối.
19. Ghi `render_log.json`.

### 3.2. Stage này không làm

Renderer không chịu trách nhiệm cho các phần sau:

* Không chạy ASR.
* Không detect scene hoặc shot.
* Không tạo embedding.
* Không tính semantic similarity.
* Không chọn top-k candidate.
* Không đổi clip khi confidence thấp.
* Không sửa `timeline.json` để chọn clip khác.
* Không sửa `matching_candidates.json`.
* Không sửa `clip_metadata.json`.
* Không sửa `audio_segments.json`.
* Không mở UI review.
* Không tự thay đổi transcript.

Nếu timeline có lỗi kỹ thuật, Renderer báo lỗi render. Renderer không tự suy luận clip thay thế.

## 4. Input

### 4.1. Input chính

Renderer đọc:

```text
data/intermediate/timeline.json
data/intermediate/media_metadata.json
data/intermediate/clip_metadata.json
data/intermediate/render_config.json (optional)
```

Media thực tế:

```text
timeline.items[].visual_items[].source_path   (video)
media_metadata.audio.normalized_path            (voice-over, hoặc render_config / CLI — xem Stage 8)
```

### 4.2. Input bắt buộc tối thiểu

MVP Renderer có thể chạy với tối thiểu:

```text
timeline.json
normalized video files referenced by timeline.items[].visual_items[].source_path
normalized voice-over audio file
```

Tuy nhiên, để validate tốt hơn, nên có:

```text
media_metadata.json
clip_metadata.json
```

Lý do:

* `timeline.json` có `audio_id` nhưng không chứa voice-over path.
* `media_metadata.json` map `audio_id` sang `audio.normalized_path`.
* `clip_metadata.json` giúp kiểm tra `clip_start/clip_end` có nằm trong range clip không.

### 4.3. Điều kiện input hợp lệ

`timeline.json` phải có:

* `schema_version`.
* `project_id`.
* `audio_id`.
* `render_settings`.
* `items`.
* Mỗi item có `segment_id`, `audio_start`, `audio_end`, `duration`.
* Mỗi item cần render có ít nhất một visual item.

`media_metadata.json` nếu được dùng phải có:

* `project_id` khớp timeline.
* `audio.audio_id` khớp `timeline.audio_id`.
* `audio.normalized_path`.
* `audio.status != error`.
* Video source usable có `normalized_path`.

`clip_metadata.json` nếu được dùng phải có:

* `project_id` khớp timeline.
* Mỗi clip dùng trong timeline tồn tại.
* `clip_id` và `video_id` khớp visual item.
* `start`, `end`, `duration` hợp lệ.

`render_config.json` nếu được dùng phải có:

* `project_id` khớp timeline.
* Output config hợp lệ.
* Audio config hợp lệ.
* Video config hợp lệ.

Media files phải:

* Tồn tại.
* Đọc được.
* Có duration đủ cho requested clip range.
* Có video stream với visual source.
* Voice-over audio đọc được.

## 5. Output

### 5.1. Output chính

Renderer tạo:

```text
data/final/final_video.mp4
```

Output video phải:

* Đúng format `mp4`.
* Đúng resolution theo render settings.
* Đúng fps theo render settings.
* Có voice-over audio chính.
* Có duration gần bằng voice-over audio hoặc timeline duration.
* Không bị thiếu đoạn hình nếu timeline renderer-ready.

### 5.2. Output log

Renderer tạo:

```text
data/intermediate/render_log.json
```

`render_log.json` dùng để debug quá trình render.

**Mẫu chuẩn:** `docs/samples/render_log_sample.json`.

Ví dụ:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "started_at": "2026-06-11T10:40:00Z",
  "finished_at": "2026-06-11T10:42:30Z",
  "status": "success",
  "output_path": "data/final/final_video.mp4",
  "duration": 16.0,
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

Quy tắc:

* `success`: render hoàn tất, không có lỗi nghiêm trọng.
* `warning`: render hoàn tất nhưng có cảnh báo.
* `failed`: render không tạo được video cuối hợp lệ.

### 5.3. Output tạm

Renderer có thể tạo file tạm:

```text
data/temp/render_segments/*.mp4
data/temp/render_lists/*.txt
```

File tạm dùng nội bộ khi render.

Quy tắc:

* Có thể giữ file tạm khi debug.
* Nên có option cleanup sau render thành công.
* Không hard-code path cá nhân.

## 6. Render settings và render config

### 6.1. Nguồn cấu hình

Trong MVP, `timeline.render_settings` là nguồn chính.

**Mẫu chuẩn:** `docs/samples/render_config_sample.json` (optional).

Nếu có `render_config.json`, Renderer có thể dùng để override hoặc bổ sung:

```text
render_config.output.path
render_config.output.width
render_config.output.height
render_config.output.fps
render_config.output.format
render_config.audio.voiceover_path
render_config.audio.keep_original_audio
render_config.audio.original_audio_volume
render_config.video.crop_mode
render_config.video.default_transition
```

Thứ tự ưu tiên đề xuất:

1. CLI argument explicit.
2. `render_config.json`.
3. `timeline.render_settings`.
4. Default của Renderer.

Renderer phải ghi vào `render_log.json` nguồn config cuối cùng đã dùng.

### 6.2. Default MVP

Nếu thiếu config optional, dùng default:

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

### 6.3. Allowed values

Renderer chỉ chấp nhận:

```text
format: mp4
transition: cut, fade, crossfade
crop_mode: fit, fill, center_crop, blur_background
speed: 0.75 đến 1.25
effect: null, none
```

Nếu gặp giá trị ngoài allowed list:

* Dừng render nếu field ảnh hưởng trực tiếp output.
* Ghi lỗi rõ vào `render_log.json`.
* Không tự đoán giá trị thay thế trừ khi config cho phép fallback.

## 7. Validate timeline trước khi render

### 7.1. Validate top-level

Renderer cần kiểm tra:

* `schema_version` tồn tại.
* `project_id` đúng.
* `audio_id` tồn tại.
* `render_settings` có required fields.
* `items` không rỗng.
* `created_at` tồn tại.
* `updated_at` tồn tại nếu timeline đã qua Review UI.

### 7.2. Validate timeline item

Mỗi item phải thỏa:

* `segment_id` không rỗng.
* `audio_start >= 0`.
* `audio_end > audio_start`.
* `duration = audio_end - audio_start` trong sai số cho phép.
* `confidence` thuộc `high`, `medium`, `low`.
* `visual_items` là array.

Nếu `visual_items = []`:

* Renderer nên fail trong MVP.
* Có thể hỗ trợ placeholder sau nếu được cấu hình rõ.
* Ghi lỗi segment thiếu visual.

### 7.3. Validate visual item

Mỗi visual item phải thỏa:

* `timeline_item_id` không rỗng.
* `clip_id` không rỗng.
* `video_id` không rỗng.
* `source_path` không rỗng.
* `source_path` tồn tại.
* `clip_start >= 0`.
* `clip_end > clip_start`.
* `timeline_start >= 0`.
* `timeline_end > timeline_start`.
* `speed` trong `[0.75, 1.25]`.
* `transition` thuộc allowed list.
* `effect` là `null` hoặc `none`.
* `crop_mode` là `null` hoặc thuộc allowed list.

Nếu có `clip_metadata.json`, kiểm tra thêm:

* `clip_id` tồn tại trong `clip_metadata.items`.
* `video_id` khớp clip.
* `clip_start >= clip_metadata.start`.
* `clip_end <= clip_metadata.end`.

### 7.4. Validate continuity

Renderer cần kiểm tra timeline visual:

* Visual items trong từng segment không overlap sai.
* Visual items trong từng segment không có gap lớn nếu không có placeholder.
* `timeline_start` và `timeline_end` nằm trong `[audio_start, audio_end]`.
* Tổng duration visual của segment gần bằng `duration`.
* Tổng duration output gần bằng audio voice-over.

Sai số đề xuất:

```text
0.01s cho item-level
0.10s cho toàn video
```

### 7.5. Mức lỗi

Renderer nên phân loại:

| Mức | Ý nghĩa | Hành động |
| --- | ------- | --------- |
| `error` | Không thể render đúng | Dừng |
| `warning` | Render được nhưng có rủi ro | Render tiếp nếu config cho phép |
| `info` | Thông tin debug | Render tiếp |

Ví dụ `error`:

* Source file không tồn tại.
* Voice-over audio không tồn tại.
* `speed` ngoài range.
* `clip_end <= clip_start`.
* `visual_items = []`.
* `format` không phải `mp4`.

Ví dụ `warning`:

* `needs_review = true`.
* `confidence = low`.
* `fallback_used = true`.
* Video source có audio nhưng `keep_original_audio = false`.
* Transition không được hỗ trợ đầy đủ và bị fallback về `cut`.

## 8. Render plan nội bộ

### 8.1. Mục tiêu của render plan

Trước khi gọi FFmpeg hoặc thư viện render, Renderer nên chuyển `timeline.json` thành render plan nội bộ.

Render plan giúp:

* Flatten visual items theo thứ tự timeline.
* Resolve source path.
* Tính duration source/output.
* Validate transition.
* Tách logic parse JSON khỏi logic render.
* Dễ test không cần render thật.

### 8.2. Render plan item

Ví dụ render plan item nội bộ:

```json
{
  "timeline_item_id": "t001_i01",
  "segment_id": "a001",
  "source_path": "data/normalized/video_01.mp4",
  "clip_start": 24.5,
  "clip_end": 29.7,
  "timeline_start": 0.0,
  "timeline_end": 5.2,
  "speed": 1.0,
  "crop_mode": "center_crop",
  "transition": "cut",
  "volume": 0.0
}
```

Render plan không phải Data Contract public. Không cần lưu nếu không debug.

### 8.3. Sort order

Renderer phải sort visual items theo:

```text
timeline_start ASC
timeline_end ASC
```

Không sort theo:

* `clip_id`.
* `video_id`.
* Candidate rank.
* Score.
* Segment ID string nếu thứ tự string khác thứ tự thời gian.

## 9. Xử lý video

### 9.1. Cắt clip

Với mỗi visual item:

```text
source_path
clip_start
clip_end
```

Renderer cắt đoạn:

```text
source_duration = clip_end - clip_start
```

Nếu cắt bằng FFmpeg:

* Có thể dùng seek input nhanh cho MVP.
* Nếu cần chính xác frame, dùng seek sau input hoặc filter trim.
* Phải ưu tiên đúng duration hơn tốc độ khi render final.

### 9.2. Điều chỉnh speed

Timeline định nghĩa:

```text
timeline_duration = timeline_end - timeline_start
speed = source_duration / timeline_duration
```

Renderer cần tạo output segment có duration:

```text
timeline_duration
```

Nếu dùng FFmpeg, video speed có thể xử lý bằng `setpts`.

Ý nghĩa:

* `speed = 1.0`: giữ nguyên.
* `speed < 1.0`: làm chậm clip.
* `speed > 1.0`: làm nhanh clip.

Renderer không tự tính lại speed nếu timeline đã có speed hợp lệ, trừ khi chỉ dùng để validate sai số.

### 9.3. Scale và crop

Renderer phải đưa mọi visual item về:

```text
width = render_settings.width
height = render_settings.height
fps = render_settings.fps
```

Supported `crop_mode`:

```text
fit
fill
center_crop
blur_background
```

Quy tắc:

* Visual item `crop_mode` override `render_settings.crop_mode`.
* Nếu visual item `crop_mode = null`, dùng default từ render settings.
* Nếu vẫn thiếu, dùng `center_crop`.

Định nghĩa MVP:

* `fit`: giữ aspect ratio, thêm padding nếu cần.
* `fill`: scale để phủ toàn frame, có thể crop.
* `center_crop`: crop từ giữa sau khi scale.
* `blur_background`: nền là video blur fill, foreground fit ở giữa.

### 9.4. FPS

Renderer output phải có fps theo setting.

Nếu source fps khác output fps:

* Renderer convert fps.
* Ghi warning nếu source fps quá thấp hoặc bất thường.

Không để nhiều fps khác nhau trong output final.

### 9.5. Effect

Trong MVP, chỉ hỗ trợ:

```text
null
none
```

Nếu gặp effect khác:

* Dừng render hoặc warning rồi bỏ qua tùy config.
* Khuyến nghị MVP: dừng để tránh output khác timeline.

## 10. Transition

### 10.1. Supported transition

Allowed transition theo Data Contract:

```text
cut
fade
crossfade
```

Trong MVP, ưu tiên hỗ trợ chắc:

```text
cut
```

Nếu chưa hỗ trợ `fade` hoặc `crossfade`:

* Renderer phải báo rõ.
* Có thể fallback về `cut` nếu config `allow_transition_fallback = true`.
* Nếu fallback, ghi warning vào `render_log.json`.

### 10.2. Rule duration

Timeline Planner và Review UI đang giả định transition không làm thay đổi tổng duration output.

Do đó Renderer phải đảm bảo:

* Tổng output duration không bị ngắn đi vì transition.
* `timeline_start/timeline_end` vẫn là source of truth.

Với `cut`:

* Không overlap.
* Không thay đổi duration.

Với `fade`:

* Có thể fade in/out trong duration của item.
* Không kéo dài item.

Với `crossfade`:

* Nếu chưa có rule overlap rõ, không nên bật trong MVP.
* Nếu hỗ trợ, phải giữ tổng duration theo timeline.

## 11. Xử lý audio

### 11.1. Voice-over là audio chính

Renderer phải dùng voice-over làm audio chính.

Nguồn voice-over lấy theo thứ tự:

1. CLI argument explicit.
2. `render_config.audio.voiceover_path`.
3. `media_metadata.audio.normalized_path` theo `timeline.audio_id`.

Nếu không tìm được voice-over:

* Renderer dừng.
* Ghi lỗi vào `render_log.json`.

### 11.2. Cắt audio voice-over

MVP nên dùng toàn bộ voice-over.

Output duration nên gần bằng:

```text
media_metadata.audio.duration
```

hoặc duration thực tế của audio file nếu đọc được bằng FFprobe/thư viện tương đương.

Nếu timeline ngắn hơn audio:

* Renderer có thể fail hoặc render video đen/last frame cho phần thiếu nếu config cho phép.
* MVP khuyến nghị fail để buộc sửa timeline.

Nếu timeline dài hơn audio:

* Renderer có thể cắt video theo audio hoặc thêm silence nếu config cho phép.
* MVP khuyến nghị fail nếu lệch lớn hơn tolerance.

### 11.3. Audio gốc của video

Voice-over là audio chính. Audio gốc của video chỉ dùng nếu:

```text
keep_original_audio = true
```

Volume lấy theo:

1. `visual_items[].volume` nếu khác `null`.
2. `effective_render_settings.original_audio_volume` sau khi merge CLI, `render_config.json` và `timeline.render_settings`.
3. Default `0.0`.

Nếu:

```text
keep_original_audio = false
```

Renderer phải mute audio gốc của video.

Nếu video không có audio gốc:

* Visual item vẫn render bình thường.
* Không coi là lỗi.
* Ghi info hoặc bỏ qua.

### 11.4. Audio mix

Nếu giữ audio gốc:

* Mix audio gốc với voice-over.
* Audio gốc nên nhỏ hơn voice-over.
* `original_audio_volume` nên trong `[0.0, 1.0]`.

Trong MVP:

* Default `keep_original_audio = false`.
* Default `original_audio_volume = 0.0`.

## 12. Chiến lược render bằng FFmpeg

### 12.1. Khuyến nghị thư viện

Renderer nên dùng FFmpeg hoặc wrapper ổn định quanh FFmpeg.

Lý do:

* Cắt clip.
* Chỉnh speed.
* Scale/crop.
* Ghép clip.
* Mix audio.
* Xuất mp4.

Không nên tự xử lý frame bằng code thủ công trong MVP nếu không cần.

### 12.2. Hai hướng triển khai

Có hai hướng triển khai hợp lý:

```text
Hướng A: Render từng segment tạm rồi concat
Hướng B: Dùng filter_complex lớn cho toàn timeline
```

Khuyến nghị MVP:

```text
Hướng A: Render từng visual item/segment tạm rồi concat
```

Lý do:

* Dễ debug.
* Dễ biết segment nào lỗi.
* Dễ retry từng đoạn.
* Lệnh FFmpeg đơn giản hơn.

Nhược điểm:

* Chậm hơn.
* Tạo file tạm.

### 12.3. Render từng visual item

Mỗi visual item được render thành file tạm cùng resolution/fps/codec.

Output tạm phải thống nhất:

* Width.
* Height.
* FPS.
* Pixel format.
* Codec.
* Audio format nếu có audio gốc.

Sau đó concat các file tạm.

### 12.4. Concat final video stream

Sau khi tạo các segment tạm:

* Sort đúng timeline order.
* Tạo concat list.
* Concat thành video stream hoàn chỉnh.
* Ghép voice-over audio.
* Xuất mp4.

Nếu timeline có gap và Renderer hỗ trợ placeholder:

* Tạo black frame hoặc blurred placeholder cho gap.
* Ghi warning.

MVP khuyến nghị không cho gap kỹ thuật.

### 12.5. Codec output

Output mp4 nên dùng:

```text
video codec: h264
audio codec: aac
pixel format: yuv420p
container: mp4
```

Lý do:

* Dễ mở trên nhiều máy.
* Phù hợp demo.
* Tránh lỗi player không hỗ trợ codec.

## 13. Error handling

### 13.1. Khi validate fail

Nếu validate fail trước render:

* Không tạo `final_video.mp4` mới.
* Tạo hoặc cập nhật `render_log.json`.
* `status = failed`.
* Ghi đầy đủ `errors`.

### 13.2. Khi render một segment fail

Nếu một visual item render fail:

* Dừng pipeline render trong MVP.
* Ghi `timeline_item_id`, `segment_id`, `clip_id`, `source_path`.
* Ghi stderr hoặc error summary từ FFmpeg nếu có.

Không nên bỏ qua segment lỗi và tiếp tục render video thiếu đoạn trong MVP.

### 13.3. Khi concat fail

Nếu concat fail:

* Giữ file tạm nếu debug enabled.
* Ghi concat list path nếu có.
* Ghi lỗi vào log.
* `status = failed`.

### 13.4. Khi audio mix fail

Nếu audio mix fail:

* Không xuất final video im lặng nếu voice-over bắt buộc.
* `status = failed`.
* Ghi lỗi voice-over/audio mix.

## 14. `render_log.json`

### 14.1. Cấu trúc đề xuất

Data Contract chỉ chốt các field cơ bản. Renderer có thể thêm field phụ nếu không phá contract.

Ví dụ mở rộng:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "started_at": "2026-06-11T10:40:00Z",
  "finished_at": "2026-06-11T10:42:30Z",
  "status": "success",
  "output_path": "data/final/final_video.mp4",
  "duration": 16.0,
  "render_time": 150.0,
  "settings": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "format": "mp4",
    "crop_mode": "center_crop",
    "keep_original_audio": false
  },
  "summary": {
    "timeline_items": 3,
    "visual_items": 4,
    "warnings_count": 1,
    "errors_count": 0
  },
  "warnings": [],
  "errors": [],
  "items": [
    {
      "timeline_item_id": "t001_i01",
      "segment_id": "a001",
      "clip_id": "v01_c003",
      "status": "success",
      "temp_path": "data/temp/render_segments/t001_i01.mp4",
      "duration": 5.2,
      "warnings": []
    }
  ]
}
```

### 14.2. Nội dung nên log

Log nên ghi:

* Render settings cuối cùng.
* Output path.
* Voice-over path.
* Số timeline items.
* Số visual items.
* Segment nào render thành công.
* Segment nào lỗi.
* Warnings về confidence/fallback nếu muốn.
* Lỗi FFmpeg rút gọn.
* Tổng render time.

Không nên ghi:

* Nội dung binary.
* Log FFmpeg quá dài nếu không cần.
* Đường dẫn tuyệt đối của máy cá nhân nếu có thể tránh.

## 15. Re-run behavior

Nếu chạy lại Renderer với cùng `project_id`:

* Nếu output đã tồn tại và không có `--overwrite`, module nên dừng an toàn.
* Nếu có `--overwrite`, module được phép ghi đè `final_video.mp4`.
* `render_log.json` có thể được ghi đè hoặc lưu bản mới theo timestamp tùy config.
* File tạm từ lần render trước nên được cleanup nếu không dùng debug mode.
* Không sửa `timeline.json`.

Khuyến nghị:

* Dùng output mặc định `data/final/final_video.mp4`.
* Cho phép truyền `--output` để render nhiều version.
* Ghi rõ output path trong `render_log.json`.

## 16. Cấu trúc code đề xuất

Module nên đặt trong:

```text
renderer/
```

Cấu trúc tham khảo:

```text
renderer/
  __init__.py
  cli.py
  renderer.py
  render_plan.py
  validators.py
  ffmpeg_runner.py
  audio.py
  video_filters.py
  io.py
  tests/
```

Gợi ý trách nhiệm:

* `io.py`: đọc/ghi JSON, resolve path.
* `validators.py`: validate timeline, media, config.
* `render_plan.py`: chuyển timeline thành render plan.
* `video_filters.py`: build scale/crop/speed/transition filters.
* `audio.py`: xử lý voice-over và audio mix.
* `ffmpeg_runner.py`: chạy FFmpeg và gom lỗi.
* `renderer.py`: orchestration render.
* `cli.py`: entrypoint.
* `tests/`: unit tests và integration tests nhỏ.

## 17. CLI đề xuất

CLI tối thiểu:

```bash
python -m renderer.cli \
  --project-id demo_01 \
  --timeline data/intermediate/timeline.json \
  --media-metadata data/intermediate/media_metadata.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --output data/final/final_video.mp4 \
  --log-output data/intermediate/render_log.json
```

CLI đầy đủ hơn:

```bash
python -m renderer.cli \
  --project-id demo_01 \
  --timeline data/intermediate/timeline.json \
  --media-metadata data/intermediate/media_metadata.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --render-config data/intermediate/render_config.json \
  --output data/final/final_video.mp4 \
  --log-output data/intermediate/render_log.json \
  --overwrite \
  --cleanup-temp
```

Tham số nên có:

| Tham số | Ý nghĩa |
| ------- | ------- |
| `--project-id` | Project ID cần render |
| `--timeline` | Path tới `timeline.json` |
| `--media-metadata` | Path tới `media_metadata.json` |
| `--clip-metadata` | Path tới `clip_metadata.json` |
| `--render-config` | Path tới `render_config.json` nếu có |
| `--voiceover` | Override voice-over path |
| `--output` | Path output video |
| `--log-output` | Path output `render_log.json` |
| `--temp-dir` | Thư mục file tạm |
| `--overwrite` | Cho phép ghi đè output |
| `--cleanup-temp` | Xóa file tạm sau khi render thành công |
| `--keep-temp` | Giữ file tạm để debug |
| `--allow-transition-fallback` | Fallback transition chưa hỗ trợ về cut |

CLI phải fail rõ ràng nếu:

* File input không tồn tại.
* JSON lỗi format.
* `project_id` không khớp.
* Output đã tồn tại nhưng không có `--overwrite`.
* FFmpeg không khả dụng.
* Timeline có lỗi kỹ thuật.

## 18. Quan hệ với các module khác

### 18.1. Với Review UI

Review UI lưu `timeline.json` đã chỉnh.

Renderer đọc file đó và render đúng theo dữ liệu.

Renderer không đọc state trong UI và không cần biết người dùng chỉnh bằng thao tác nào.

### 18.2. Với Timeline Planner

Timeline Planner tạo timeline ban đầu.

Nếu chưa qua Review UI, Renderer vẫn có thể render timeline ban đầu nếu timeline hợp lệ.

Renderer không phân biệt timeline do Timeline Planner hay Review UI tạo, miễn là đúng contract.

### 18.3. Với Input Processor

Renderer dùng output của Input Processor:

* Normalized video files.
* Normalized voice-over audio.
* `media_metadata.json`.

Renderer không dùng raw media nếu normalized path đã có.

### 18.4. Với Video Analyzer

Renderer có thể dùng `clip_metadata.json` để validate clip range.

Renderer không dùng keyframe để render final video.

### 18.5. Với Matching Engine

Renderer không phụ thuộc vào `matching_candidates.json`.

Renderer không dùng:

* Candidate rank.
* Semantic score.
* Confidence để đổi clip.
* Reason.

Nếu timeline có `confidence = low`, Renderer có thể ghi warning nhưng vẫn render nếu timeline kỹ thuật hợp lệ.

### 18.6. Với Evaluation

Evaluation dùng:

* `final_video.mp4`.
* `render_log.json`.
* `timeline.json`.

Renderer nên ghi log đủ để Evaluation biết render thành công, duration output và warning/error.

## 19. Điều kiện handoff sang Evaluation

Stage 8 được phép bàn giao sang Evaluation khi:

* `final_video.mp4` tồn tại.
* File output đọc được.
* `render_log.json` tồn tại.
* `render_log.status = success` hoặc `warning`.
* Output duration gần với voice-over/timeline duration.
* Output resolution đúng render settings.
* Output fps đúng render settings.
* Output có audio voice-over.
* Không có lỗi nghiêm trọng trong `render_log.errors`.

Nếu `render_log.status = failed`:

* Không bàn giao Evaluation như output final.
* Evaluation vẫn có thể đọc log để báo lỗi pipeline nếu cần.

## 20. Test cases bắt buộc

### 20.1. Test render một segment đơn giản

Input:

* Timeline có một visual item.
* `speed = 1.0`.
* `transition = cut`.

Kỳ vọng:

* Tạo được `final_video.mp4`.
* Duration gần bằng segment duration.
* Có audio voice-over.
* `render_log.status = success`.

### 20.2. Test nhiều segment

Input:

* Timeline có nhiều segment liên tiếp.

Kỳ vọng:

* Video output ghép đúng thứ tự timeline.
* Không có gap/overlap bất thường.
* Duration tổng đúng tolerance.

### 20.3. Test speed nhỏ hơn 1

Input:

* Visual item có `speed = 0.8`.

Kỳ vọng:

* Output visual item dài hơn source duration.
* Duration output khớp `timeline_end - timeline_start`.

### 20.4. Test speed lớn hơn 1

Input:

* Visual item có `speed = 1.2`.

Kỳ vọng:

* Output visual item ngắn hơn source duration.
* Duration output khớp timeline.

### 20.5. Test crop mode

Input:

* Source video khác aspect ratio output.
* Test `fit`, `fill`, `center_crop`.

Kỳ vọng:

* Output resolution đúng.
* Không méo hình.
* Crop/padding đúng mode.

### 20.6. Test missing source path

Input:

* Visual item có `source_path` không tồn tại.

Kỳ vọng:

* Renderer không tạo final video mới.
* `render_log.status = failed`.
* Error ghi rõ source path.

### 20.7. Test missing voice-over

Input:

* Không có voice-over path hợp lệ.

Kỳ vọng:

* Renderer fail.
* Error ghi rõ audio chính thiếu.

### 20.8. Test visual_items rỗng

Input:

* Một timeline item có `visual_items = []`.

Kỳ vọng:

* MVP Renderer fail.
* Error ghi rõ segment thiếu visual.

### 20.9. Test transition unsupported

Input:

* Visual item có `transition = crossfade`.
* Renderer chưa hỗ trợ crossfade.

Kỳ vọng:

* Nếu không bật fallback, render fail.
* Nếu bật fallback, render dùng cut và log warning.

### 20.10. Test keep_original_audio false

Input:

* Source video có audio gốc.
* `keep_original_audio = false`.

Kỳ vọng:

* Output chỉ có voice-over hoặc audio gốc bị mute.
* Không nghe audio gốc rõ trong final.

### 20.11. Test keep_original_audio true

Input:

* Source video có audio gốc.
* `keep_original_audio = true`.
* `original_audio_volume = 0.2`.

Kỳ vọng:

* Output có voice-over.
* Audio gốc được mix nhỏ hơn voice-over.

### 20.12. Test output tồn tại

Input:

* `final_video.mp4` đã tồn tại.
* Không có `--overwrite`.

Kỳ vọng:

* Renderer dừng an toàn.
* Không ghi đè output cũ.

### 20.13. Test project_id không khớp

Input:

* `timeline.json` và `media_metadata.json` khác `project_id`.

Kỳ vọng:

* Renderer fail trước khi render.
* Không tạo output mới.

### 20.14. Test render_log failed

Input:

* Timeline có lỗi kỹ thuật.

Kỳ vọng:

* `render_log.json` được tạo.
* `status = failed`.
* `errors` không rỗng.

## 21. Tiêu chí nghiệm thu

Module Renderer được xem là đạt yêu cầu MVP khi:

1. Đọc được `timeline.json`.
2. Đọc được `media_metadata.json`.
3. Đọc được `clip_metadata.json` nếu dùng validate.
4. Đọc được `render_config.json` nếu có.
5. Validate được `project_id` giữa các file.
6. Resolve được voice-over audio path.
7. Resolve được video source paths.
8. Validate được `render_settings`.
9. Validate được timeline items.
10. Validate được visual items.
11. Fail rõ khi segment thiếu visual.
12. Fail rõ khi source path thiếu.
13. Fail rõ khi voice-over thiếu.
14. Render được một visual item đơn giản.
15. Render được nhiều visual items theo thứ tự timeline.
16. Cắt clip đúng `clip_start/clip_end`.
17. Apply speed đúng trong `[0.75, 1.25]`.
18. Scale/crop đúng output resolution.
19. Xuất fps đúng setting.
20. Hỗ trợ `transition = cut`.
21. Có rule rõ cho `fade/crossfade` nếu chưa hỗ trợ.
22. Dùng voice-over làm audio chính.
23. Mute audio gốc khi `keep_original_audio = false`.
24. Mix audio gốc khi `keep_original_audio = true`.
25. Xuất được `final_video.mp4`.
26. Output mp4 mở được bằng player phổ biến.
27. Tạo `render_log.json`.
28. `render_log.status` đúng trạng thái.
29. `render_log.errors` ghi rõ lỗi khi fail.
30. Không sửa `timeline.json`.
31. Không đọc Matching Engine để chọn clip.
32. Có cơ chế `--overwrite`.
33. Có test với dữ liệu mẫu nhỏ.
34. Output có thể đưa sang Evaluation.

## 22. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 8 cần tự kiểm tra:

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc được timeline.json
[ ] Đọc được media_metadata.json
[ ] Đọc được clip_metadata.json nếu dùng validate
[ ] Đọc được render_config.json nếu có
[ ] Validate project_id các file khớp nhau
[ ] Resolve được voice-over path
[ ] Resolve được source_path của mọi visual item
[ ] Kiểm tra source files tồn tại
[ ] Kiểm tra voice-over tồn tại
[ ] Validate render_settings
[ ] Validate timeline item required fields
[ ] Validate visual item required fields
[ ] Không render nếu visual_items rỗng
[ ] Không render nếu speed ngoài [0.75, 1.25]
[ ] Không render nếu clip_start/clip_end sai
[ ] Không render nếu transition ngoài allowed list
[ ] Build được render plan
[ ] Sort visual items theo timeline_start
[ ] Cắt clip đúng clip_start/clip_end
[ ] Apply speed đúng
[ ] Scale/crop đúng crop_mode
[ ] Xuất đúng width/height/fps
[ ] Hỗ trợ transition cut
[ ] Có rule rõ nếu fade/crossfade chưa hỗ trợ
[ ] Dùng voice-over làm audio chính
[ ] Mute audio gốc khi keep_original_audio false
[ ] Mix audio gốc khi keep_original_audio true
[ ] Xuất final_video.mp4
[ ] Ghi render_log.json
[ ] render_log có status/output_path/duration/render_time
[ ] render_log ghi errors khi fail
[ ] Không sửa timeline.json
[ ] Không sửa matching_candidates.json
[ ] Không tự chọn clip thay thế
[ ] Không hard-code path cá nhân
[ ] Có --overwrite hoặc cơ chế tương đương
[ ] Có cleanup/keep temp rõ ràng
[ ] Có test render mẫu ngắn
[ ] Output có thể đưa cho Evaluation
```

## 23. Ghi chú triển khai MVP

MVP Renderer nên ưu tiên đúng timeline, ổn định và dễ debug hơn là hiệu ứng đẹp.

Thứ tự ưu tiên nên là:

1. Validate timeline chặt.
2. Resolve media source ổn định.
3. Render `transition = cut`.
4. Scale/crop đúng resolution.
5. Ghép voice-over đúng.
6. Xuất mp4 mở được.
7. Ghi log rõ.
8. Hỗ trợ speed.
9. Hỗ trợ audio gốc ở volume nhỏ.
10. Hỗ trợ fade/crossfade sau.

Nếu có tranh luận giữa filter FFmpeg phức tạp và luồng render tạm dễ debug, MVP nên chọn luồng render tạm. Khi pipeline end-to-end ổn định, có thể tối ưu sang `filter_complex` để render nhanh hơn và hỗ trợ transition nâng cao.
