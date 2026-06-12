# 05. Stage 3 — Video Analysis

| Module | `video_analyzer/` |
| Core docs | [00](00_project_scope.md) · [01](01_system_architecture.md) · [02](02_data_contract.md) |
| Schema/Sample | [docs/schemas/clip_metadata.schema.md](../schemas/clip_metadata.schema.md) · [docs/samples/clip_metadata_sample.json](../samples/clip_metadata_sample.json) |

## 1. Mục tiêu stage

Stage 3 — Video Analysis phân tích các video nguồn đã chuẩn hóa từ Stage 1, tách video thành clip candidate, trích keyframe đại diện, tính quality score cơ bản và tạo `clip_metadata.json` cho các stage phía sau.

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

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  ① Input ──► ② Audio ─┐
                        ├──► ④ → ⑤ → ⑥ → ⑦ → ⑧
            ③ Video ───┘
                 ▲
            Stage này (song song ②)

  ── Chi tiết Stage ③ ─────────────────────────────────────

        ┌── media_metadata.json
        │   videos[*].normalized_path
        ▼
┌─────────────────────────────┐
│  ③ Video Analyzer           │  ◄── bạn ở đây
└─────────────┬───────────────┘
              │ ghi
              ├─ clip_metadata.json
              ├─ keyframes/*.jpg
              └─ video_analysis_log.json
              │
              ▼
    ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧
```

| | |
|---|---|
| **Đọc (IN)** | `media_metadata.json`, file video đã chuẩn hóa (`videos[*].normalized_path`) |
| **Ghi (OUT)** | `clip_metadata.json`, keyframe images, `video_analysis_log.json` |
| **Downstream** | Stage ④ (embedding visual), ⑤, ⑥, ⑦, ⑧ đọc `clip_metadata.json` |

Không đọc audio thuyết minh — chỉ phụ thuộc output Stage ①. Chi tiết: [01 §4.3](01_system_architecture.md#43-video-analyzer).

## 3. Trách nhiệm

### 3.1. Làm

1. Đọc `media_metadata.json`.
2. Lọc video usable (`status = ready` hoặc `warning`).
3. Lấy `videos[*].normalized_path`.
4. Kiểm tra file video normalized tồn tại và đọc được.
5. Chạy scene detection hoặc shot detection.
6. Tạo clip candidate từ ranh giới scene/shot.
7. Chia nhỏ clip quá dài nếu cần.
8. Đánh dấu clip quá ngắn nếu không đủ dùng.
9. Trích keyframe đại diện cho mỗi clip.
10. Tính quality score cơ bản cho keyframe và clip.
11. Sinh `clip_id` và `keyframe_id` theo quy tắc ổn định.
12. Lưu keyframe image files.
13. Xuất `clip_metadata.json`.
14. Xuất `video_analysis_log.json` để debug nếu cần.

### 3.2. Không làm

* Không chuẩn hóa video, không render video cuối.
* Không chạy ASR, không đọc transcript, không tạo text query.
* Không tạo embedding, không matching clip với audio segment.
* Không chọn clip mặc định cho timeline, không tạo `timeline.json`.
* Không quyết định transition, speed hoặc crop mode của video cuối.

Stage này chỉ tạo danh sách clip candidate và metadata đi kèm. Việc clip nào khớp với đoạn audio nào thuộc Matching Engine và Timeline Planner.

## 4. Input cần đọc

### 4.1. Files

| File | Nguồn | Mục đích |
| ---- | ----- | -------- |
| `data/intermediate/media_metadata.json` | Stage 1 | Danh sách video + `normalized_path` |
| Video normalized | `media_metadata.json → videos[*].normalized_path` | Scene detection, keyframe (ví dụ: `data/normalized/video_01.mp4`) |

Không hard-code đường dẫn video trong module. Quy ước path: [02 §2.6](02_data_contract.md#26-path).

### 4.2. Fail-fast

`media_metadata.json` phải thỏa:

* Parse được JSON; có `schema_version`, `project_id`, array `videos`.
* `videos` có ít nhất một video.
* Mỗi video có `video_id`, `normalized_path`, `duration > 0`, `fps > 0`, `width > 0`, `height > 0`.

**Xử lý theo status:**

* `ready` / `warning` → xử lý.
* `error` → bỏ qua video đó.

**Dừng pipeline** nếu không còn video usable nào sau khi lọc.

### 4.3. Config nội bộ

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

| Tham số | Giá trị đề xuất MVP |
| ------- | ------------------- |
| `scene_detection.method` | `content` hoặc thư viện tương đương |
| `min_clip_duration` | `1.5` giây |
| `max_clip_duration` | `8.0` giây |
| `split_long_clips` | `true` |
| `keep_low_quality_clips` | `true` |
| `keyframes.positions` | `start`, `middle`, `end` |
| `keyframes.image_format` | `jpg` |

Ghi chú: không bắt buộc PySceneDetect/OpenCV/FFmpeg cụ thể; clip chất lượng thấp giữ với `status = low_quality` thay vì xóa; score chưa tính được → `null`; caption/content_tags optional, có thể bỏ qua MVP.

## 5. Output cần tạo

| Output | Path | Contract? |
| ------ | ---- | --------- |
| Clip metadata | `data/intermediate/clip_metadata.json` | **Có** — stage chính |
| Keyframe images | `data/keyframes/{clip_id}_k{NN}.jpg` | Dữ liệu trực quan — path ghi trong metadata |
| Analysis log | `data/intermediate/video_analysis_log.json` | Không — debug only |

Ví dụ keyframe: `data/keyframes/v01_c001_k01.jpg`, `v01_c001_k02.jpg`, `v01_c001_k03.jpg`.

Các module sau chỉ nên phụ thuộc vào `clip_metadata.json` và keyframe paths trong file này. Nếu mâu thuẫn với log, ưu tiên `clip_metadata.json`.

## 6. Contract fields stage trực tiếp dùng

### 6.1. Đọc từ `media_metadata.json`

→ [02 §4](02_data_contract.md#4-media_metadatajson) · schema: [media_metadata.schema.md](../schemas/media_metadata.schema.md) · sample: [media_metadata_sample.json](../samples/media_metadata_sample.json)

| Field đọc | Quy tắc stage |
| --------- | ------------- |
| `project_id` | Copy sang `clip_metadata.json` |
| `videos[*].video_id` | Map vào mỗi clip |
| `videos[*].normalized_path` | Input phân tích; ghi `source_path` trên clip |
| `videos[*].duration`, `fps`, `width`, `height` | Validate + log |
| `videos[*].status` | Chỉ xử lý `ready`/`warning`; bỏ qua `error` |

### 6.2. Ghi `clip_metadata.json`

→ [02 §6](02_data_contract.md#6-clip_metadatajson) · schema: [clip_metadata.schema.md](../schemas/clip_metadata.schema.md) · sample: [clip_metadata_sample.json](../samples/clip_metadata_sample.json)

**Top-level ghi:** `schema_version`, `project_id`, `created_at`, `items`.

**Clip item — quy tắc stage (ngoài schema chung):**

| Field | Quy tắc stage |
| ----- | ------------- |
| `clip_id` | `v01_c001`, `v01_c002`, … — prefix từ `video_id`; padding 3 chữ số |
| `video_id` | Phải tồn tại trong `media_metadata.json` |
| `source_path` | **MVP bắt buộc ghi** — relative path video normalized tương ứng |
| `start`, `end`, `duration` | Giây trong video nguồn; xem [02 §2.2](02_data_contract.md#22-đơn-vị-thời-gian) |
| `keyframes` | ≥ 1 keyframe với clip usable; path relative, file phải tồn tại |
| `keyframe_id` | `v01_c001_k01`, … — padding 2 chữ số |
| `keyframe.timestamp` | Trong `[clip.start, clip.end]` |
| `keyframe.position` | `start`, `middle`, `end`, `extra` |
| `quality_score` | `0.0`–`1.0` hoặc `null` — không bịa |
| `quality.*` | Chi tiết blur/brightness/motion/stability — optional, cùng quy ước score |
| `status` | **MVP bắt buộc ghi** mọi clip: `usable`, `low_quality`, `too_short`, `error` |
| `scene_index`, `content_tags`, `caption`, `notes` | Optional |

**MVP:** `items` phải có ít nhất một clip usable nếu phân tích thành công; không tạo clip `duration <= 0`.

## 7. Quy trình xử lý riêng

### 7.1. Bước 1 — Đọc metadata

Đọc `project_id`, `videos[*].video_id`, `normalized_path`, `duration`, `fps`, `width`, `height`, `status`.

Video `warning` → vẫn xử lý; ghi warning trong log.

### 7.2. Bước 2 — Lọc video usable

Chỉ xử lý `status = ready` hoặc `warning`. Bỏ qua `error`. Không còn video usable → dừng, báo lỗi.

### 7.3. Bước 3 — Validate video file

Với từng video usable: file tồn tại, đọc được, stream hình hợp lệ, FPS/width/height đọc được, duration gần metadata:

```text
Lệch <= 0.1s: chấp nhận
Lệch > 0.1s và <= 1.0s: warning
Lệch > 1.0s: cần xem lại, có thể bỏ qua video
```

### 7.4. Bước 4 — Scene/shot detection

Detect ranh giới cảnh. Output nội bộ: scene/shot index, start, end, duration.

Yêu cầu:

* Timestamp map về video normalized; không cắt/thay đổi video.
* Không detect được boundary → **fallback fixed-window** (chia clip ~4–6 giây); ghi rõ trong log.

MVP không yêu cầu scene detection hoàn hảo — ưu tiên: không lỗi timestamp, không bỏ sót toàn bộ video, đủ clip cho matching, có log debug.

### 7.5. Bước 5 — Tạo clip candidate

Từ ranh giới scene/shot, tạo clip:

* Duration đủ dùng timeline; không quá dài so với audio segment thông thường.
* Có hình ảnh đọc được; ≥ 1 keyframe đại diện.

```text
min_clip_duration: 1.5s
max_clip_duration: 8.0s
```

Quy tắc:

* Clip < `1.5s` → đánh dấu `too_short` hoặc gộp clip lân cận nếu hợp lý.
* Clip > `8.0s` → chia nhỏ nếu `split_long_clips = true`.
* Không tự loại clip vì "không liên quan audio" — độ liên quan ngữ nghĩa thuộc Embedding/Matching.
* Không cắt clip theo audio duration ở Stage 3 — căn duration với audio thuộc Timeline Planner.

### 7.6. Bước 6 — Xử lý clip quá ngắn

Clip quá ngắn gây cắt cảnh quá nhanh.

* Nằm giữa hai clip cùng cảnh → có thể gộp trước/sau.
* Không gộp được → ghi `status = too_short`; Matching/Timeline có thể bỏ qua hoặc penalty.
* Không xóa im lặng — giữ để debug scene detection.

### 7.7. Bước 7 — Chia clip quá dài

Scene/shot > `max_clip_duration` → chia clip con, mỗi con ~4–8s nếu có thể.

* Giữ `video_id` gốc; `scene_index` giữ scene gốc hoặc index mới — nhất quán.
* `start`, `end`, `duration` là timestamp trong video nguồn.

Ví dụ scene 24.0s–42.0s:

```text
v01_c003: 24.0s -> 30.0s
v01_c010: 30.0s -> 36.0s
v01_c011: 36.0s -> 42.0s
```

(Timestamp thật: [clip_metadata_sample.json](../samples/clip_metadata_sample.json).)

### 7.8. Bước 8 — Trích keyframe

MVP: 3 keyframe (`start`, `middle`, `end`) khi clip đủ dài; clip ngắn → 1 keyframe giữa.

Timestamp:

* `start`: gần đầu clip, tránh transition/blur — ví dụ `start + 0.2s`.
* `middle`: gần giữa clip.
* `end`: gần cuối — ví dụ `end - 0.2s`.
* Phải nằm trong `[clip.start, clip.end]`.

Output path (relative):

```text
data/keyframes/v01_c003_k01.jpg
data/keyframes/v01_c003_k02.jpg
```

Path dựa trên `keyframe_id`; không dùng timestamp dài trong tên file.

**Clip lỗi keyframe:** không đánh dấu `usable`; `status = error`; không tạo path giả; không đưa keyframe item nếu file không tồn tại. Frame mờ/lỗi → lấy frame lân cận nếu có thể.

### 7.9. Bước 9 — Tính quality score

| Score | Ý nghĩa |
| ----- | ------- |
| `blur_score` | Độ nét (ví dụ variance of Laplacian, normalize 0–1) |
| `brightness_score` | Độ sáng vừa phải; quá tối/cháy → thấp |
| `motion_score` | Chuyển động vừa phải = cao; rung mạnh = thấp |
| `stability_score` | Ít rung = cao |
| `quality_score` | Trung bình có trọng số các score trên |

Quy ước: score ∈ `[0.0, 1.0]`; cao = tốt; chưa tính → `null` (không dùng `0` thay "chưa tính"). MVP không cần công thức phức tạp — quan trọng nhất quán và giải thích được.

`quality_score` cấp clip nên khớp `quality.quality_score` nếu cả hai tồn tại.

### 7.10. Bước 10 — Gán status clip

| `status` | Khi dùng |
| -------- | -------- |
| `usable` | Dùng được cho matching/timeline |
| `low_quality` | Đọc được nhưng hình thấp — vẫn dùng được với penalty |
| `too_short` | Quá ngắn — không chọn mặc định MVP |
| `error` | Lỗi timestamp hoặc không trích keyframe |

Consumer được phép dùng `usable` và `low_quality`. `too_short` và `error` không chọn mặc định; giữ trong metadata để debug.

### 7.11. Bước 11 — Ghi output

Trước khi ghi: validate top-level; `items` không rỗng nếu có video usable; `clip_id` không trùng; `video_id` hợp lệ; `source_path` mọi clip; timestamp hợp lệ; keyframe path relative và file tồn tại; `quality_score` ∈ `[0.0, 1.0]` hoặc `null`; `status` mọi clip thuộc allowed values.

**Log phụ:** video xử lý/bỏ qua, scene method/threshold, số scene/clip theo status, clip bị split, clip lỗi keyframe, quality summary, thời gian chạy. Cấu trúc đề xuất — không phải inter-module schema.

### 7.12. Quy tắc scene/clip bổ sung

* **Không cắt theo audio:** ví dụ sai — "audio segment 5.2s nên cắt mọi clip 5.2s".
* **Không tự loại clip "không liên quan":** Stage 3 chỉ đánh giá tồn tại, vị trí, keyframe, chất lượng hình cơ bản.
* **Ưu tiên giữ dữ liệu có status rõ:** clip có vấn đề nhưng đọc được → giữ với `too_short`/`low_quality`/`error` thay vì xóa im lặng.

## 8. Error / fallback / re-run behavior

### 8.1. Lỗi chặn pipeline

| Tình huống | Hành vi |
| ---------- | ------- |
| Không còn video usable | Dừng; báo lỗi rõ |
| Không tạo được clip usable nào | Báo lỗi; pipeline matching không chạy bình thường; có thể giữ clip lỗi để debug |
| Video file không tồn tại/không đọc được | Bỏ qua hoặc dừng tùy mức; nếu hết usable → dừng |

### 8.2. Fallback không chặn

| Tình huống | Hành vi |
| ---------- | ------- |
| Scene detection không tìm boundary | Fixed-window ~4–6s; ghi fallback trong log |
| Video `status = warning` | Xử lý tiếp; ghi warning |
| Một số clip `low_quality` | Pipeline chạy tiếp — penalty ở Matching/Timeline |
| Duration metadata lệch nhẹ (≤ 1.0s) | Warning; tiếp tục nếu timestamp hợp lý |

### 8.3. Ràng buộc stage

* Không thay đổi file video normalized (không cắt ghi đè, đổi speed, dịch timestamp).
* Không bịa `quality_score` — chưa tính → `null`.
* Không tạo keyframe path giả — clip usable phải có file ảnh thật.
* Các module sau không phụ thuộc `video_analysis_log.json`.

Quy ước thời gian, score, ID, path chung: [02 §2](02_data_contract.md#2-quy-ước-chung).

### 8.4. Re-run

* Cùng `project_id` + input/rule detection không đổi → `clip_id`, `keyframe_id` ổn định.
* Đổi threshold hoặc rule split → boundary có thể thay đổi; ghi trong log.
* Không `--overwrite` → báo output đã tồn tại, dừng an toàn.
* Có `--overwrite` → ghi đè `clip_metadata.json`, keyframe files, log.
* Nếu đã có `embedding_metadata.json`, `matching_candidates.json` hoặc `timeline.json` từ output cũ → chạy lại stage sau.

## 9. Handoff condition

Stage 3 bàn giao `clip_metadata.json` + keyframe files cho Embedding Indexer khi:

```text
clip_metadata.json parse được
có đủ top-level required fields
items không rỗng
mỗi clip có đủ required fields
clip_id không trùng
timestamp hợp lệ
keyframe path của clip usable tồn tại
quality_score ∈ [0.0, 1.0] hoặc null
status có ở mọi clip và thuộc allowed values
source_path mỗi clip trỏ đúng video normalized
```

Consumer: Embedding Indexer (`clip_id`, `keyframes[*].path`); Matching Engine (`clip_id`, `duration`, `quality_score`, `status`); Timeline Planner (`video_id`, `source_path`, `start`, `end`, `duration`, `status`); Review UI (keyframes, `quality_score`, `status`); Renderer (timestamp qua timeline hoặc metadata). Chi tiết: [01 §4.3](01_system_architecture.md#43-video-analyzer) và [02 §13](02_data_contract.md#13-quy-tắc-mapping-giữa-các-file).

Clip `low_quality` → pipeline tiếp (cảnh báo/penalty). Không có clip usable → lỗi chặn integration.

## 10. Test cases

| # | Test | Input / điều kiện | Kỳ vọng |
| - | ---- | ----------------- | ------- |
| 1 | Một video hợp lệ | `media_metadata.json` + `video_01.mp4` | `clip_metadata.json`; ≥ 1 clip usable; keyframe files; top-level đúng `project_id`; clip usable đủ required fields |
| 2 | Nhiều video hợp lệ | Nhiều video usable | Clip mỗi video; `video_id` map đúng; `clip_id` không trùng |
| 3 | Video `status = warning` | Video warning | Vẫn xử lý; warning trong log; tạo clip nếu OK |
| 4 | Video `status = error` | Video error | Bỏ qua; không clip usable từ video lỗi; hết usable → dừng |
| 5 | Timestamp hợp lệ | Output clips | `start >= 0`; `end > start`; `duration = end - start`; không vượt duration video; keyframe timestamp trong clip |
| 6 | Scene detection không boundary | Video không có cảnh rõ | Fallback fixed-window; clip hợp lệ; ghi fallback trong log |
| 7 | Clip quá ngắn | Clip < 1.5s | Gộp nếu hợp lý hoặc `status = too_short` |
| 8 | Clip quá dài | Scene dài | Chia nhỏ nếu `split_long_clips = true`; timestamp hợp lệ; `clip_id` theo thời gian |
| 9 | Keyframe path | Clip usable | `keyframe_id`, `timestamp`, `path`; file tồn tại; relative path; không path giả |
| 10 | Quality score | Output clips | ∈ `[0.0, 1.0]` hoặc `null`; không dùng `0` thay "chưa tính" |
| 11 | Status clip | Mọi clip | Có `status`; thuộc allowed values; không sinh `ready`, `warning`, `bad`, `normal` |
| 12 | source_path | Mọi clip MVP | Relative path; trỏ đúng video normalized; file tồn tại |
| 13 | Chạy lại module | Output đã tồn tại | Không `--overwrite` → dừng an toàn; có `--overwrite` → ghi đè; input/rule không đổi → ID ổn định |

CLI tối thiểu (nếu cần smoke test): `python -m video_analyzer.main --media-metadata data/intermediate/media_metadata.json --output-dir data/intermediate --keyframe-dir data/keyframes`.

## 11. Acceptance criteria

Module Video Analyzer đạt yêu cầu MVP khi:

1. Đọc được `media_metadata.json`; lấy đúng `videos[*].normalized_path`.
2. Chạy với video `ready`/`warning`; bỏ qua đúng video `error`.
3. Tạo clip candidate từ video nguồn; `clip_metadata.json` đúng schema.
4. Mỗi clip có `clip_id`, `video_id`, `start`, `end`, `duration`, `keyframes`, `quality_score`.
5. Thời gian dùng giây; clip và keyframe timestamp hợp lệ.
6. `clip_id` ổn định nếu input và rule detection không đổi.
7. Clip usable có ≥ 1 keyframe thật; path relative, file tồn tại.
8. `quality_score` ∈ `[0.0, 1.0]` hoặc `null`.
9. Mọi clip có `status` thuộc allowed values (MVP bắt buộc ghi dù contract tổng optional).
10. MVP ghi `source_path` mọi clip.
11. Clip `usable`/`low_quality` đưa sang Matching Engine; `too_short`/`error` không chọn mặc định.
12. Tạo `video_analysis_log.json` hỗ trợ debug.
13. Embedding Indexer dùng keyframe; Matching Engine xếp hạng; Review UI hiển thị keyframe.
14. Timeline Planner / Renderer dùng timestamp cắt video.
15. Có quy tắc rõ khi chạy lại cùng `project_id`.

## 12. Checklist

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
[ ] Output có thể đưa cho Embedding Indexer; Matching Engine, Timeline Planner, Review UI dùng ở các bước sau
```
