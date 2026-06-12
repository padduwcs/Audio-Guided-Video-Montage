# 08. Stage 6 — Timeline Planning

| | |
|---|---|
| **Module** | `timeline_planner/` |
| **Core docs** | [`00`](./00_project_scope.md) · [`01`](./01_system_architecture.md) · [`02`](./02_data_contract.md) |
| **Schema / Sample** | [`timeline.schema.md`](../schemas/timeline.schema.md) · [`timeline_sample.json`](../samples/timeline_sample.json) |
| **Stage spec** | File này |

---

## 1. Mục tiêu stage

Stage 6 — Timeline Planning tạo bản dựng video ban đầu `timeline.json` từ audio segments, clip metadata, matching candidates và media metadata.

Stage này là cầu nối giữa phân tích và dựng video. Output phải đủ rõ để Review UI hiển thị, người dùng chỉnh sửa và Renderer xuất video cuối **mà không gọi lại Matching Engine**.

**Mục tiêu cụ thể:**

* Đọc `audio_segments.json`, `clip_metadata.json`, `matching_candidates.json`, `media_metadata.json`.
* Validate mapping `segment_id` ↔ `clip_id` ↔ `video_id` ↔ source path.
* Tạo một timeline item cho mỗi audio segment.
* Chọn visual mặc định từ `selected_clip_id`; xử lý clip dài/ngắn hơn segment.
* Cho phép một segment có một hoặc nhiều visual items.
* Gán `timeline_start/end`, `clip_start/end`, `speed`, `transition`, `crop_mode`, `volume`.
* Đánh dấu `needs_review`, `fallback_used`, `confidence`.
* Xuất `timeline.json` đúng Data Contract; log phụ `timeline_planning_log.json` nếu cần.

**Không phải mục tiêu:** ASR, matching lại, render, UI (→ §3.2).

---

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  ① ──► ② ─┐
           ├──► ④ ──► ⑤ ──► ⑥ ──► ⑦ ──► ⑧
       ③ ─┘                    ▲
                          Stage này

  ── Chi tiết Stage ⑥ ─────────────────────────────────────

  ② audio_segments.json ─────────┐
  ③ clip_metadata.json ──────────┤
  ⑤ matching_candidates.json ─────┼──►
  ① media_metadata.json ─────────┘
                                ▼
                 ┌─────────────────────────────┐
                 │  ⑥ Timeline Planner          │  ◄── bạn ở đây
                 └─────────────┬───────────────┘
                               │ ghi
                               ├─ timeline.json
                               └─ timeline_planning_log.json
                               │
                               ▼
                    ⑦ Review UI → ⑧ Renderer
```

| | |
|---|---|
| **Đọc (IN)** | `audio_segments.json`, `clip_metadata.json`, `matching_candidates.json`, `media_metadata.json` |
| **Ghi (OUT)** | `timeline.json`, `timeline_planning_log.json` |
| **Downstream** | Stage ⑦ chỉnh sửa và ghi đè `timeline.json`; Stage ⑧ render khi timeline đạt điều kiện |

Chi tiết: [`01` §4.6](./01_system_architecture.md). **Không** quyết định lại clip về mặt ngữ nghĩa — chỉ biến candidate đã chọn thành timeline có thể dựng được.

---

## 3. Trách nhiệm

### 3.1. Làm (in-scope)

| # | Hành vi |
|---|---------|
| 1 | Đọc 4 input JSON; validate `schema_version`, `project_id` |
| 2 | Validate audio chính trong `media_metadata.json` |
| 3 | Validate mỗi `segment_id` có candidate set (nếu Matching Engine chạy đầy đủ) |
| 4 | Validate `clip_id` tồn tại trong `clip_metadata.json`; map `video_id` → source path |
| 5 | Chọn clip mặc định; tạo `timeline.items[]` theo thứ tự audio segment |
| 6 | Tính vị trí timeline (`audio_start/end`); tính `clip_start/end`, `speed` |
| 7 | Tách segment thành nhiều visual items khi một clip không đủ dài |
| 8 | Gán transition, crop mode, volume; đánh dấu fallback và review flag |
| 9 | Xuất `timeline.json`; xuất `timeline_planning_log.json` để debug |

### 3.2. Không làm (out-of-scope)

| Hành vi | Thuộc |
|---------|-------|
| ASR, sửa transcript, detect scene, keyframe, embedding | Stage 2–4 |
| Tính lại semantic similarity; sửa `matching_candidates.json` / `clip_metadata.json` | Stage 5 / 3 |
| Render video; xử lý tương tác UI; lưu chỉnh sửa người dùng | Stage 7–8 |

Input thiếu/lỗi → báo lỗi hoặc đánh dấu `needs_review`; **không** tự chạy lại stage trước.

---

## 4. Input cần đọc

### 4.1. Files

| File | Path mặc định | Mục đích |
|------|---------------|----------|
| Audio segments | `data/intermediate/audio_segments.json` | Thứ tự segment, timestamp, transcript, `segment_id` |
| Clip metadata | `data/intermediate/clip_metadata.json` | Clip source, `video_id`, `start/end/duration`, `quality_score`, `status` |
| Matching candidates | `data/intermediate/matching_candidates.json` | Top-k, `selected_clip_id`, score, confidence, fallback |
| Media metadata | `data/intermediate/media_metadata.json` | Audio chính, video normalized, fps/resolution tham chiếu |

Contract đọc: [`02` §5–§8](./02_data_contract.md) · samples tương ứng trong `docs/samples/`.

### 4.2. Fail-fast

Bốn file phải: parse JSON; có `schema_version`, `project_id`; **`project_id` giống nhau**.

**`audio_segments.json`:** `items` không rỗng; mỗi segment có `segment_id`, `start`, `end`, `duration`; `duration ≈ end - start` (tolerance `0.01s`); sort tăng dần; không overlap bất thường.

**`clip_metadata.json`:** `items` không rỗng; mỗi clip có `clip_id`, `video_id`, `start/end/duration` (`duration > 0`); `source_path` hoặc suy ra từ `media_metadata.videos[].normalized_path`; nếu có `status`, không dùng `error`.

**`matching_candidates.json`:** candidate set cho mỗi segment (điều kiện bình thường); `audio_segment_id` tồn tại; `selected_clip_id` là `null` hoặc trong `candidates[]`; mỗi candidate có `clip_id`, `rank`, `final_score`; `confidence` ∈ `high|medium|low`.

**`media_metadata.json`:** `audio.audio_id`, `audio.normalized_path`, `audio.duration > 0`; ≥ 1 video `status = ready|warning` với `normalized_path` tồn tại.

Lỗi cấu trúc nghiêm trọng → **dừng**, không tạo timeline giả.

### 4.3. Config nội bộ module

> Không phải Data Contract giữa các module.

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

| Key | MVP default | Ghi chú |
|-----|-------------|---------|
| `render_settings.default_transition` | `cut` | Giảm rủi ro lệch duration khi render |
| `timing.min_speed` / `max_speed` | `0.75` / `1.25` | Khớp Renderer |
| `timing.time_tolerance` | `0.01` | Sai số duration visual trong segment |
| `keep_original_audio` | `false` | → `visual_items[].volume = 0.0` |

---

## 5. Output cần tạo

| Output | Path | Contract? |
|--------|------|-----------|
| Timeline | `data/intermediate/timeline.json` | **Có** — stage chính |
| Planning log | `data/intermediate/timeline_planning_log.json` | Không — debug only |

`timeline.json` là file trung tâm cho Review UI và Renderer. Tạo ngay cả khi một số segment cần review, miễn dữ liệu đủ để pipeline tiếp tục.

Lỗi nghiêm trọng khiến timeline không dùng được → dừng, **không** tạo timeline giả.

---

## 6. Contract fields stage trực tiếp dùng

Canonical: [`02` §9 `timeline.json`](./02_data_contract.md#9-timelinejson) · [`timeline.schema.md`](../schemas/timeline.schema.md) · [`timeline_sample.json`](../samples/timeline_sample.json).

Quy ước chung (giây, relative path, ID): [`02` §2](./02_data_contract.md#2-quy-ước-chung).

### 6.1. Đọc từ input

| Nguồn | Field đọc | Dùng cho |
|-------|-----------|----------|
| `audio_segments` | `segment_id`, `start`, `end`, `duration`, `text` | Timeline item timing + transcript |
| `clip_metadata` | `clip_id`, `video_id`, `source_path`, `start`, `end`, `duration`, `quality_score`, `status` | Visual item + validate |
| `matching_candidates` | `candidate_set_id`, `audio_segment_id`, `selected_clip_id`, `candidates[]`, `confidence`, `fallback_used` | Chọn clip + `candidates_ref` |
| `media_metadata` | `audio.audio_id`, `audio.normalized_path`, `videos[].normalized_path` | `audio_id`, resolve `source_path` |

### 6.2. Ghi `timeline.json`

**Top-level ghi:** `schema_version`, `project_id`, `audio_id`, `created_at`, `updated_at`, `render_settings`, `items`.

| Field / nhóm | Quy tắc stage |
|--------------|---------------|
| `audio_id` | Từ `media_metadata.audio.audio_id` |
| `created_at` / `updated_at` | ISO 8601 UTC; lần đầu có thể giống nhau |
| `render_settings` | Required: `width`, `height`, `fps`, `format` (`mp4`); optional: `default_transition`, `crop_mode`, `keep_original_audio`, `original_audio_volume` |
| `items[]` | **Một item cho mỗi** audio segment — không bỏ segment |

**Timeline item — quy tắc stage (ngoài schema):**

| Field | Quy tắc |
|-------|---------|
| `segment_id` | Từ `audio_segments`; không đổi |
| `audio_start` / `audio_end` / `duration` | Copy từ `audio_segments.items[].start/end/duration` |
| `text` | **Copy chính xác** từ `audio_segments.items[].text` (cùng `segment_id`) — không tóm tắt, không sửa |
| `confidence` | Từ candidate set; có thể **hạ** nếu fallback (không nâng `low` → `medium/high`) |
| `score` | `final_score` của candidate chọn; `null` nếu không có visual |
| `candidates_ref` | `candidate_set_id` (vd. `candidates_a001`); `null` nếu không có set |
| `user_edited` | Luôn `false` khi Planner tạo lần đầu |
| `visual_items` | Có thể `[]` khi không tìm clip — xem §8.2 |

**Visual item — quy tắc stage:**

| Field | Quy tắc |
|-------|---------|
| `timeline_item_id` | `t{segment_index_3d}_i{visual_index_2d}` — vd. `t001_i01`, `t003_i02`; ổn định khi input + thứ tự segment không đổi; không UUID |
| `source_path` | Video normalized — **không** keyframe image (§8.4) |
| `clip_start` / `clip_end` | Trong range clip gốc; timestamp video normalized |
| `timeline_start` / `timeline_end` | Trong `[audio_start, audio_end]`; item đầu = `segment.start`, item cuối = `segment.end` |
| `speed` | `0.75`–`1.25` (§7.6) |
| `transition` | `cut` \| `fade` \| `crossfade`; MVP default `cut` |
| `volume` | `0.0` nếu `keep_original_audio = false`; else `original_audio_volume` |
| `source_candidate_rank` | Rank trong top-k hoặc `null` (fallback) |
| `locked` | `false` khi Planner tạo lần đầu |

**Ràng buộc timing bắt buộc khi tạo timeline:**

```text
sum(timeline_end - timeline_start) per segment ≈ segment.duration  (tolerance 0.01s)
(clip_end - clip_start) / speed = timeline_end - timeline_start   (per visual item)
```

Mẫu multi-visual: segment `a003` trong [`timeline_sample.json`](../samples/timeline_sample.json).

---

## 7. Quy trình xử lý riêng

### 7.1. Luồng chính

```text
1. Load media_metadata → audio_segments → clip_metadata → matching_candidates
2. Validate project_id, required fields
3. Build lookup: segments_by_id, clips_by_id, videos_by_id, candidate_sets_by_segment_id
4. Chuẩn bị render_settings (§7.2)
5. Với mỗi audio segment (sort theo start):
   a. Tạo timeline item (timing + text copy)
   b. Chọn clip mặc định (§7.4)
   c. Tạo visual items + fit duration (§7.5–7.6)
   d. Gán score, confidence, needs_review (§7.7)
6. Ghi timeline.json + timeline_planning_log.json
```

Lỗi cấu trúc ở bước 1–2 → dừng. Segment thiếu `segment_id`/`start`/`end`/`duration` → lỗi nghiêm trọng, yêu cầu sửa Stage 2.

### 7.2. Render settings

Thứ tự ưu tiên: config người dùng → default module → suy ra từ video usable đầu tiên trong `media_metadata`.

MVP nên dùng default ổn định (1920×1080, 30fps, mp4, `cut`, `center_crop`, `keep_original_audio=false`). Nếu suy ra từ video nguồn: chỉ video `ready|warning`; nhiều resolution khác nhau → vẫn normalize output theo config cố định.

### 7.3. Timeline item per audio segment

* Duyệt `audio_segments.items[]` sau sort `start`.
* Copy `audio_start`, `audio_end`, `duration`, **`text`** — không gộp/tách audio segment ở Stage 6.
* Segment lỗi nhẹ vẫn tạo item + `needs_review=true` + `notes`.

### 7.4. Chọn clip mặc định

Thứ tự:

1. `selected_clip_id` từ candidate set nếu hợp lệ.
2. `selected_clip_id = null` → candidate rank 1, rồi rank tiếp theo.
3. Hết candidate hợp lệ → fallback clip từ `clip_metadata` nếu bật (§8.1).
4. Vẫn không có → `visual_items = []`, `needs_review = true`.

**Candidate hợp lệ:** `clip_id` tồn tại; `status ≠ error`; `duration > 0`; map được video source; source path ghi đúng contract.

| Clip status | MVP |
|-------------|-----|
| `usable` | Chọn bình thường |
| `low_quality` | Chỉ khi không có lựa chọn tốt hơn hoặc Matching đã chọn |
| `too_short` | Không ưu tiên đầu; có thể lấp khoảng ngắn |
| `error` | **Không** dùng |

Chọn khác `selected_clip_id` → log + `needs_review = true`; giữ `candidates_ref` cho UI.

### 7.5. Tạo visual items (single và multi)

Mục tiêu: `sum(visual timeline duration) ≈ segment.duration` (tolerance `0.01s`).

* Visual đầu: `timeline_start = segment.start`.
* Visual cuối: `timeline_end = segment.end`.
* Nhiều visual trong segment: liên tục, không overlap, không gap > `time_tolerance`, sort `timeline_start` ASC.

```text
segment a001: 0.0 → 5.2s
  visual 1: timeline 0.0 → 5.2

segment a002: 5.2 → 12.0s
  visual 1: 5.2 → 8.5
  visual 2: 8.5 → 12.0
```

**Ưu tiên nhiều visual items** hơn speed < `0.75`. Không loop cùng đoạn clip trong segment (trừ fallback đã đánh dấu). Reuse clip → ghi `notes`.

Một segment dài với clip dài: MVP chỉ cắt **một** subrange — không tự chia clip dài thành nhiều visual nếu không có lý do (tránh logic khó debug).

### 7.6. Duration và speed (`0.75`–`1.25`)

**Công thức cơ bản** (mỗi visual item):

```text
source_duration = clip_end - clip_start
timeline_duration = timeline_end - timeline_start
speed = source_duration / timeline_duration
```

| `speed` | Ý nghĩa |
|---------|---------|
| `1.0` | Phát bình thường |
| `< 1.0` | Chậm — kéo dài clip |
| `> 1.0` | Nhanh — rút ngắn clip |

**MVP:** `0.75 <= speed <= 1.25`. Speed gần ngưỡng → có thể `needs_review = true`.

#### Clip dài hơn segment (`clip.duration >= segment.duration`)

* `speed = 1.0`.
* `clip_start = clip.start` (mặc định).
* `clip_end = clip_start + segment.duration`.

```text
segment.duration = 5.2, clip.start = 24.5
→ clip_start = 24.5, clip_end = 29.7, speed = 1.0
```

#### Clip ngắn hơn segment — fit bằng speed

```text
speed = clip.duration / segment.duration
```

Nếu `speed >= 0.75`: một visual item duy nhất.

```text
segment 5.0s, clip 4.0s → speed = 0.8
clip_start = clip.start, clip_end = clip.end
timeline_start = segment.start, timeline_end = segment.end
```

#### Clip quá ngắn (`clip.duration / segment.duration < 0.75`)

Không kéo giãn quá mức. Thứ tự:

1. Dùng clip chọn cho phần đầu segment.
2. Candidate rank tiếp theo cho phần còn lại.
3. Hết candidate → fallback clip (§8.1).
4. Vẫn thiếu → gap thiếu visual hoặc clip tốt nhất + `needs_review = true`.

#### Transition và duration

MVP: `transition = cut` mặc định. Planner **không** trừ duration cho transition — `timeline_start/end` là vị trí tuyệt đối; Renderer áp dụng transition không đổi tổng duration. `crossfade` overlap cần rule đồng bộ Planner + Renderer — **không** bật MVP nếu Renderer chưa hỗ trợ.

### 7.7. Score, confidence, `needs_review`

| Field | Nguồn |
|-------|-------|
| `score` | `final_score` candidate chọn; `null` nếu không visual |
| `confidence` | Candidate set; hạ `high→medium` (cảnh báo nhỏ), `medium→low` (fallback/path không chắc) |
| `fallback_used` | Candidate set hoặc Planner gán khi fallback thêm |
| `user_edited` | `false` |

`needs_review = true` khi:

* `confidence = low` hoặc `fallback_used = true`
* `visual_items = []`
* `selected_clip_id` không hợp lệ, phải chọn candidate khác
* Clip `low_quality`; duration không fit sạch trong speed range
* Reuse clip quá gần; source path không tồn tại tại thời điểm tạo

`needs_review = false` khi: confidence `high|medium`, không fallback, visual hợp lệ, duration fit, source path OK.

### 7.8. Source path và volume

**Source path** (thứ tự):

1. `clip_metadata.items[].source_path`
2. `media_metadata.videos[].normalized_path` theo `video_id`

Không dùng `original_path` nếu đã có `normalized_path`; không path tuyệt đối máy cá nhân; không path keyframe.

Path đúng contract nhưng file chưa mount → vẫn ghi path + `needs_review=true` + warning log. Path không xác định → không tạo visual đó; thử fallback.

**Volume:** voice-over là audio chính (Renderer dùng `media_metadata.audio.normalized_path`). Video gốc chỉ khi `keep_original_audio = true`.

```text
keep_original_audio = false  → volume = 0.0
keep_original_audio = true   → volume = original_audio_volume
```

Video không có audio gốc → visual vẫn hợp lệ; `volume` có thể `0.0` hoặc `null`.

### 7.9. Output phụ — `timeline_planning_log.json`

Khuyến nghị khi tích hợp. Ghi: segment dùng selected clip / rank khác / fallback ngoài set / không visual / hạ confidence / multi visual / source path missing / lý do `needs_review`. Không đưa embedding, transcript dài.

Cấu trúc đề xuất: `summary` (counts) + `items[]` per segment (`decision`, `warnings`). Không phải inter-module contract.

---

## 8. Error / fallback / re-run behavior

### 8.1. Fallback

**Khi cần fallback:** không candidate set; `selected_clip_id = null`; clip chọn không tồn tại / `status=error` / không map path; clip quá ngắn thiếu candidate khác; Matching đã `fallback_used = true`.

**Thứ tự:**

1. Candidate rank tiếp theo trong cùng set.
2. Clip `usable`, `quality_score` cao — cùng video với candidate tốt nhất.
3. Clip `usable`, `quality_score` cao — toàn `clip_metadata`.
4. Clip `low_quality` nếu `allow_low_quality = true`.
5. Không chọn → `visual_items = []`.

Mỗi lần fallback → `notes` hoặc log entry.

### 8.2. `visual_items = []` và renderer-readiness

Vẫn **tạo timeline item** khi không có clip:

```text
confidence = low, score = null, needs_review = true, fallback_used = true
visual_items = [], candidates_ref = null hoặc giữ ref cho UI
```

Lý do: UI hiển thị segment cần xử lý; người dùng chọn clip thủ công; Evaluation biết segment thiếu hình.

| Consumer | Hành vi |
|----------|---------|
| Review UI | Mở được; highlight `missing visual` |
| Renderer (MVP) | **Fail** — không render bản cuối cho đến khi mọi segment cần render có visual |
| Handoff Renderer | Cần mỗi item **ít nhất một** visual item hợp lệ |

### 8.3. Re-run

| Tình huống | Hành vi |
|------------|---------|
| Output tồn tại, không `--overwrite` | Dừng an toàn hoặc yêu cầu path khác |
| `--overwrite` | Ghi đè `timeline.json` do Planner tạo |
| Timeline có `user_edited = true` | **Không** ghi đè im lặng — cần xác nhận hoặc path mới |
| Input + config không đổi | `timeline_item_id` và thứ tự `items` ổn định |

Planner chỉ tạo draft ban đầu; sau Review UI chỉnh → không merge timeline cũ/mới trong MVP.

### 8.4. Ràng buộc kỹ thuật

* Không thêm required field mới vào `timeline.json` — dùng `notes` hoặc log phụ.
* Path trong timeline: **relative** (vd. `data/normalized/video_01.mp4`).
* Visual item trỏ **video clip**, không keyframe (`data/intermediate/keyframes/...jpg` = sai).
* Không bỏ audio segment — luôn một timeline item.
* Thời gian: giây; tolerance `0.01s`; round 2–3 chữ số thập phân.

---

## 9. Handoff condition

### 9.1. Review UI

| # | Điều kiện |
|---|-----------|
| 1 | `timeline.json` parse được; `project_id`, `audio_id` đúng |
| 2 | `render_settings` đủ required fields |
| 3 | Một timeline item cho **mỗi** audio segment |
| 4 | Mỗi item có `segment_id`, `audio_start/end`, `duration`, `text` (copy từ audio segments) |
| 5 | `needs_review` gán rõ; `candidates_ref` map được `matching_candidates` nếu có |

### 9.2. Renderer (renderer-ready)

Tất cả điều kiện Review UI **và**:

| # | Điều kiện |
|---|-----------|
| 6 | Mỗi item cần render có ≥ 1 visual item |
| 7 | Visual đủ required fields; `source_path` resolve được |
| 8 | `clip_start/end`, `timeline_start/end` hợp lệ, liên tục |
| 9 | `speed` ∈ `[0.75, 1.25]`; `transition` allowed |
| 10 | Tổng timeline ≈ duration audio chính |

Còn `visual_items = []` → UI mở được; Renderer **chưa** render được — thể hiện qua `needs_review = true`.

Chi tiết consumer: [`01` §4.6](./01_system_architecture.md) · [`02` §14.5](./02_data_contract.md#145-kiểm-tra-timelinejson).

---

## 10. Test cases

| ID | Mô tả | Kỳ vọng chính |
|----|-------|----------------|
| T01 | 1 segment 5s, clip dài hơn 5s | 1 visual; `speed=1.0`; `clip_end-clip_start=5.0` |
| T02 | Segment 5s, clip 4s | 1 visual; `speed=0.8`; trong `[0.75, 1.25]` |
| T03 | Segment 8s; rank1=3s, rank2=5s | 2 visual liên tục; tổng 8s; `source_candidate_rank` 1, 2 |
| T04 | `selected_clip_id` không tồn tại; rank1 OK | Chọn rank1; `needs_review=true`; log |
| T05 | Không candidate hợp lệ; fallback tắt | Item với `visual_items=[]`; `confidence=low`; `score=null` |
| T06 | Candidate set rỗng; fallback bật | Dùng fallback clip; `fallback_used=true`; `source_candidate_rank=null` |
| T07 | Selected clip `status=error` | Bỏ clip; thử khác hoặc `visual_items=[]` |
| T08 | Clip thiếu `source_path`; metadata có `normalized_path` | Visual dùng `normalized_path` |
| T09 | `project_id` không khớp | Dừng; không timeline giả |
| T10 | `format=mov` hoặc `transition=dissolve` | Dừng hoặc fallback default rõ ràng |
| T11 | Nhiều segments liên tiếp | Timing khớp audio; visual không overlap sai |
| T12 | Re-run | Không overwrite → dừng; `--overwrite` → ghi đè; `user_edited` → không im lặng |
| T13 | `text` copy | Khớp chính xác `audio_segments` cùng `segment_id` |

```bash
python -m timeline_planner.cli \
  --project-id demo_01 \
  --media-metadata data/intermediate/media_metadata.json \
  --audio-segments data/intermediate/audio_segments.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --matching-candidates data/intermediate/matching_candidates.json \
  --output data/intermediate/timeline.json
```

---

## 11. Acceptance criteria

Module Timeline Planner đạt MVP khi:

1. Đọc và validate 4 input; `project_id` khớp.
2. Một timeline item cho mỗi audio segment; `text` copy chính xác từ audio segments.
3. Ưu tiên `selected_clip_id`; fallback candidate/fallback clip khi lỗi; không dùng `status=error`.
4. Map `clip_id` → `video_id` → source path normalized.
5. Visual item đủ required fields; `timeline_item_id` ổn định.
6. Tính đúng `clip_start/end`, `timeline_start/end`, `speed` ∈ `[0.75, 1.25]`.
7. Clip dài → cắt `speed=1.0`; clip ngắn → speed fit; quá ngắn → multi visual hoặc fallback.
8. `transition`, `crop_mode`, `volume` theo render settings.
9. `score`, `confidence`, `needs_review`, `fallback_used`, `candidates_ref` đúng rule.
10. `user_edited=false`, `locked=false` khi tạo lần đầu.
11. `visual_items=[]` vẫn tạo item + `needs_review` — Renderer fail cho đến khi có visual.
12. `timeline.json` đúng contract; log phụ hỗ trợ debug.
13. Review UI mở và highlight review; Renderer đọc được khi renderer-ready.
14. Re-run có `--overwrite`; không ghi đè timeline `user_edited` im lặng.

---

## 12. Checklist

```text
[ ] Đã đọc 00, 01, 02 và stage spec này
[ ] Đọc audio_segments, clip_metadata, matching_candidates, media_metadata
[ ] project_id khớp; lookup maps theo segment_id, clip_id, video_id, candidate set
[ ] Một timeline item cho mỗi audio segment — không bỏ segment
[ ] text copy chính xác từ audio_segments (cùng segment_id)
[ ] Dùng selected_clip_id nếu hợp lệ; fallback đúng §8.1
[ ] Không dùng clip status error
[ ] Clip dài: speed=1.0, cắt đúng duration
[ ] Clip ngắn: speed fit trong [0.75, 1.25]
[ ] Clip quá ngắn: multi visual items ưu tiên hơn speed < 0.75
[ ] timeline_start/end liên tục trong segment; tổng duration ≈ segment.duration
[ ] (clip_end - clip_start) / speed = timeline_end - timeline_start
[ ] source_path = video normalized, không keyframe, relative path
[ ] volume theo keep_original_audio
[ ] needs_review, fallback_used, confidence, score, candidates_ref đúng rule
[ ] visual_items=[] → needs_review=true; Renderer chưa ready
[ ] Ghi timeline.json + timeline_planning_log.json
[ ] --overwrite / không ghi đè user_edited im lặng
[ ] Test T01–T13 §10
[ ] Handoff §9 — Review UI và Renderer (khi renderer-ready)
```
