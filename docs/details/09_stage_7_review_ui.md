# 09. Stage 7 — Review UI

| | |
|---|---|
| **Module** | `review_ui/` |
| **Core docs** | [`00`](./00_project_scope.md) · [`01`](./01_system_architecture.md) · [`02`](./02_data_contract.md) |
| **Schema / Sample** | [`timeline.schema.md`](../schemas/timeline.schema.md) · [`timeline_sample.json`](../samples/timeline_sample.json) |
| **Stage spec** | File này |

---

## 1. Mục tiêu stage

Stage 7 — Review UI cung cấp giao diện để người dùng kiểm tra và chỉnh sửa bản dựng ban đầu do Timeline Planner tạo.

UI **không** phải editor phim đầy đủ. MVP: xem từng audio segment, clip đang chọn, top-k thay thế; đổi clip; chỉnh tham số cơ bản; lưu `timeline.json` để Renderer dùng.

**Mục tiêu cụ thể:**

* Load `timeline.json`, `matching_candidates.json`, `clip_metadata.json`, `audio_segments.json`, `media_metadata.json`.
* Hiển thị segments theo thứ tự timeline; highlight `needs_review`, `confidence`, fallback.
* Hiển thị visual hiện tại và top-k theo `candidates_ref`.
* Cho đổi clip; chỉnh `clip_start/end`, `speed`, `transition`, `crop_mode`, `volume`, `locked`.
* Validate trước khi lưu; cập nhật `user_edited`, `updated_at`.
* **Ghi đè** `data/intermediate/timeline.json` (cùng path Timeline Planner tạo).

**Không phải mục tiêu:** ASR, matching lại, render `final_video.mp4`, sửa `matching_candidates.json`, **sửa transcript** (MVP: correction ngoài UI — xem [`04_stage_2_audio_analysis.md`](04_stage_2_audio_analysis.md) §7.13, [`00_project_scope.md`](00_project_scope.md) §6.2) (→ §3.2).

---

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  ① ──► ② ─┐
           ├──► ④ ──► ⑤ ──► ⑥ ──► ⑦ ──► ⑧
       ③ ─┘                          ▲
                                Stage này

  ── Chi tiết Stage ⑦ ─────────────────────────────────────

  ⑥ timeline.json ─────────────────┐
  ⑤ matching_candidates.json ──────┤  top-k theo candidates_ref
  ③ clip_metadata.json ────────────┤
  ② audio_segments.json ───────────┤  đồng bộ segment / phụ đề
  ① media_metadata.json ───────────┤
     normalized media ─────────────┘  preview clip
                                   ▼
                 ┌─────────────────────────────┐
                 │  ⑦ Review UI                 │  ◄── bạn ở đây
                 └─────────────┬───────────────┘
                               │ ghi đè (cùng path)
                               ├─ timeline.json
                               └─ review_ui_log.json (optional)
                               │
                               ▼
                         ⑧ Renderer
```

| | |
|---|---|
| **Đọc (IN)** | `timeline.json`, `matching_candidates.json`, `clip_metadata.json`, `audio_segments.json`, `media_metadata.json`, media preview |
| **Ghi (OUT)** | `timeline.json` (ghi đè), `review_ui_log.json` (optional) |
| **Downstream** | Stage ⑧ chỉ đọc `timeline.json` đã cập nhật — không chạy lại pipeline phân tích |

Chi tiết: [`01` §4.7](./01_system_architecture.md) · [`02` §9](./02_data_contract.md#9-timelinejson).

---

## 3. Trách nhiệm

### 3.1. Làm (in-scope)

| # | Hành vi |
|---|---------|
| 1 | Load 5 file JSON + media preview nếu cần |
| 2 | Validate `project_id`; hiển thị toàn bộ timeline items |
| 3 | Highlight `needs_review`, `confidence=low`, `fallback_used`, `visual_items=[]` |
| 4 | Hiển thị clip hiện tại + top-k theo `candidates_ref` |
| 5 | Cho đổi clip từ candidate; chỉnh tham số visual được phép (§6) |
| 6 | Validate chỉnh sửa trước khi lưu (§8.1) |
| 7 | Cập nhật `user_edited`, `locked`, `updated_at`; lưu `timeline.json` |
| 8 | Ghi `review_ui_log.json` nếu cần |

### 3.2. Không làm (out-of-scope)

| Hành vi | Thuộc |
|---------|-------|
| ASR, scene detection, embedding, tính lại matching score | Stage 2–5 |
| Sửa `matching_candidates.json`, `clip_metadata.json`, `audio_segments.json` | Contract upstream |
| Render `final_video.mp4`; tự chọn clip bằng model | Stage 8 |
| Đổi schema; chỉnh `audio_start/end` (MVP); chỉnh file media nguồn | Ngoài phạm vi MVP |

Đổi clip → chỉ cập nhật `timeline.json`; giữ `matching_candidates.json` để truy vết top-k ban đầu.

---

## 4. Input cần đọc

### 4.1. Files

| File | Path mặc định | Mục đích |
|------|---------------|----------|
| Timeline | `data/intermediate/timeline.json` | Bản dựng hiện tại |
| Matching candidates | `data/intermediate/matching_candidates.json` | Top-k thay thế |
| Clip metadata | `data/intermediate/clip_metadata.json` | Preview + validate clip |
| Audio segments | `data/intermediate/audio_segments.json` | Đối chiếu transcript/timing gốc |
| Media metadata | `data/intermediate/media_metadata.json` | Path voice-over + video normalized |

### 4.2. Media preview (optional)

```text
data/normalized/*.mp4
data/normalized/*.wav
```

UI chỉ preview — không xuất video cuối. Resolve path: `visual_items[].source_path` hoặc `clip_metadata` → `media_metadata.videos[].normalized_path`.

### 4.3. Fail-fast / degraded load

JSON phải: parse được; `schema_version`, `project_id`; **`project_id` giống nhau**.

**`timeline.json`:** `audio_id`, `render_settings`, `items` không rỗng; mỗi item có `segment_id`, `audio_start/end`, `duration`, `visual_items` (array, có thể rỗng).

**`matching_candidates.json`:** `items`; mỗi set có `candidate_set_id`, `audio_segment_id`; candidate có `rank`, `clip_id`, `final_score`.

**`clip_metadata.json`:** mỗi clip có `clip_id`, `video_id`, `start`, `end`, `duration`.

**`audio_segments.json`:** segment khớp `timeline.items[].segment_id`; timing khớp trong tolerance nhỏ.

| Mức lỗi | Hành vi UI |
|---------|------------|
| Nhẹ | Mở read-only nếu có thể; hiển thị lỗi theo segment/file; không cho lưu nếu phá contract |
| Nghiêm trọng | Dừng load; không tạo timeline mới |

---

## 5. Output cần tạo

| Output | Path | Contract? |
|--------|------|-----------|
| Timeline (cập nhật) | `data/intermediate/timeline.json` | **Có** — **ghi đè** file Planner tạo |
| Review log | `data/intermediate/review_ui_log.json` | Không — debug only |
| Backup (optional) | `data/intermediate/timeline.before_review.json` | Không — lần save đầu phiên |

**Quy tắc path:** MVP mặc định ghi đè `data/intermediate/timeline.json`. Renderer đọc **cùng path** — integration phải truyền đúng. Có thể backup trước save đầu; backup không thay contract.

Mẫu: [`timeline_sample.json`](../samples/timeline_sample.json). Renderer **không** đọc `review_ui_log.json`.

---

## 6. Contract fields stage trực tiếp dùng

Canonical: [`02` §9](./02_data_contract.md#9-timelinejson) · [`timeline.schema.md`](../schemas/timeline.schema.md).

### 6.1. Field UI **được** chỉnh

**Timeline item:**

| Field | Ghi chú |
|-------|---------|
| `visual_items` | Đổi clip / tạo visual khi `[]` |
| `user_edited` | `true` khi người dùng chỉnh |
| `needs_review` | Tắt sau xác nhận; bật nếu chỉnh còn vấn đề |
| `notes` | Ghi chú người dùng |

**Visual item:**

| Field | Ghi chú |
|-------|---------|
| `clip_id`, `video_id`, `source_path` | Khi đổi clip |
| `clip_start`, `clip_end`, `speed` | Trong range hợp lệ; speed `0.75`–`1.25` |
| `transition`, `effect` (`null`/`none`), `crop_mode`, `volume` | Allowed values only |
| `source_candidate_rank` | Rank nếu từ top-k; `null` nếu ngoài top-k |
| `locked`, `notes` | Khóa lựa chọn người dùng |

**Top-level:**

| Field | Ghi chú |
|-------|---------|
| `updated_at` | Cập nhật mỗi lần Save |
| `render_settings` | Chỉ setting cơ bản nếu UI có panel — values trong contract |

### 6.2. Field UI **không** chỉnh

| Field | Lý do |
|-------|-------|
| `segment_id`, `audio_start`, `audio_end`, `duration`, `text` | Thuộc audio segment gốc (MVP không sửa transcript) |
| `candidates_ref`, `score`, `confidence` | Truy vết hệ thống — hiển thị OK, không tự nâng confidence |
| `timeline_item_id`, `timeline_start`, `timeline_end` | ID/timing ổn định — MVP giữ `timeline_start=audio_start`, `timeline_end=audio_end` khi đổi clip 1 visual |
| `schema_version`, `project_id`, `audio_id`, `created_at` | Metadata contract |

Người dùng xác nhận segment `confidence=low` → có thể `needs_review=false`, **không** đổi `confidence` thành `high`.

### 6.3. Công thức timing khi chỉnh

```text
source_duration = clip_end - clip_start
timeline_duration = timeline_end - timeline_start
speed = source_duration / timeline_duration
```

Chỉnh `clip_start/end` → validate `speed` ∈ `[0.75, 1.25]`. Chỉnh `speed` → cập nhật `clip_end = clip_start + (timeline_duration * speed)`; validate `clip_end <= clip_metadata.end`.

Đổi clip (1 visual item): giữ `timeline_item_id`, `timeline_start`, `timeline_end`; tính lại `clip_start/end`, `speed`, `video_id`, `source_path`, `source_candidate_rank`.

---

## 7. Quy trình xử lý riêng

### 7.1. Bố cục UI (MVP)

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

**Segment list:** `segment_id`, transcript rút gọn, time range, confidence, score, badge `needs_review` / `fallback_used` / `edited` / `missing visual`. Sort: timeline order. Filter: All, Needs review, Low confidence, Edited, Missing visual.

**Current preview:** video từ `source_path`, đoạn `clip_start`→`clip_end`, transcript/audio segment, clip/video ID, timeline range, warning path lỗi. MVP: HTML video/audio hoặc player local — không cần preview transition chính xác hay composite multi-visual.

**Candidate list:** map `candidates_ref` → `matching_candidates.items[].candidate_set_id`. Hiển thị rank, clip ID, scores, reason, thumbnail/keyframe nếu có. Clip đang dùng → `selected`. Candidate invalid → disable + lý do.

**Inspector:** chỉnh + validation inline (speed range, clip end vượt range, source missing, visual duration ≠ segment).

**Render settings panel (optional):** width, height, fps, format, crop mode default, keep original audio, original audio volume — validate allowed values trước save.

### 7.2. Mở project

1. Load `timeline.json` + file phụ.
2. Validate mapping cơ bản.
3. Chọn segment đầu tiên có `needs_review=true` (hoặc `confidence=low`, `fallback_used=true`, `visual_items=[]`); không có → segment đầu tiên.

### 7.3. Review segment

Hiển thị: transcript, audio start/end/duration, confidence, score, fallback, clip hiện tại, preview, top-k, controls, validation warnings.

### 7.4. Đổi clip từ top-k

1. Validate `clip_id` trong `clip_metadata`.
2. Lấy `video_id`, `source_path`, `start`, `end`, `duration`.
3. Tính `clip_start/end`, `speed` fit segment.
4. Cập nhật visual hiện tại hoặc **tạo mới** nếu `visual_items=[]` (`timeline_item_id` vd. `t003_i01`).
5. `source_candidate_rank = candidate.rank`; `user_edited=true`; `locked` theo lựa chọn.
6. **Giữ** `candidates_ref`; **không** sửa `matching_candidates.json`.

**Segment nhiều visual (MVP tối thiểu):** hiển thị từng item; chọn item đang chỉnh; đổi clip từng item; không đổi ranh giới `timeline_start/end` trừ khi gộp về 1 visual (clip mới fit toàn segment + validate).

**Clip ngoài top-k (optional):** phải có trong `clip_metadata`; `source_candidate_rank=null`; `notes`: `Selected outside top-k`.

### 7.5. Mark as reviewed

Action đơn giản: `needs_review=false`, `user_edited=true`. **Không** đổi `confidence`, `score`, `candidates_ref`.

### 7.6. Preview rules

| Loại | Nguồn |
|------|-------|
| Audio segment | `media_metadata.audio.normalized_path`; seek `audio_start`→`audio_end` |
| Visual item | `source_path`, `clip_start/end`, `speed` (preview speed có thể không chính xác 100%) |
| Candidate | Metadata clip — **không** cập nhật timeline cho đến khi Choose/Apply |

### 7.7. Transition / crop / volume

```text
transition: cut | fade | crossfade  (disable nếu Renderer chưa hỗ trợ)
crop_mode: fit | fill | center_crop | blur_background
volume: 0.0–1.0
```

`keep_original_audio=false` → volume nên `0.0`. `effect` chỉ `null` hoặc `none`.

---

## 8. Error / fallback / re-run behavior

### 8.1. Validation trước khi lưu

**Top-level:** `schema_version`, `project_id`, `audio_id`, `created_at` không đổi/xóa; `updated_at` hợp lệ; `render_settings` hợp lệ; `items` không rỗng.

**Timeline item:** `segment_id` ∈ `audio_segments`; `duration ≈ audio_end - audio_start`; `confidence` ∈ `high|medium|low`; `visual_items` là array; `candidates_ref` string hoặc `null`.

**Visual item:** `timeline_item_id` không rỗng; `clip_id` tồn tại; `video_id` khớp; `source_path` không rỗng; `clip_start/end` trong clip range; `timeline_start/end` trong `[audio_start, audio_end]`; `speed` ∈ `[0.75, 1.25]`; `transition` allowed; `effect` null/none; `crop_mode` null hoặc allowed.

**Continuity:** visual không overlap; không gap lớn nếu renderer-ready; tổng visual duration ≈ `duration`; không duplicate `segment_id`; đủ segment.

### 8.2. Mức lỗi validation

| Mức | Ý nghĩa | Cho lưu? |
|-----|---------|----------|
| `error` | Sai contract hoặc Renderer chắc chắn lỗi | **Không** |
| `warning` | Hợp lệ nhưng cần xem lại | Có |
| `info` | Thông tin phụ | Có |

Ví dụ `error`: `clip_id` không tồn tại; `speed=1.6`; `clip_end <= clip_start`; `transition=dissolve`.

Ví dụ `warning`: `confidence=low`; `fallback_used=true`; source chưa kiểm tra được; clip `low_quality`.

### 8.3. Save behavior

MVP: **explicit Save** — không auto-save mỗi phím.

```text
1. Người dùng chỉnh → state in-memory
2. Bấm Save → validate toàn bộ timeline
3. Có error → không lưu
4. Chỉ warning → cho lưu
5. Cập nhật updated_at
6. Ghi data/intermediate/timeline.json (ghi đè)
7. Ghi review_ui_log.json nếu có
8. Hiển thị save status
```

**Dirty state** khi: đổi clip, timing, speed, transition, crop, volume, locked, needs_review, notes, render settings. Rời trang khi dirty → cảnh báo chưa lưu.

**Preserve:** không xóa optional field UI không hiểu; không xóa `notes` cũ nếu user không sửa.

**Read-only mode** (`--readonly`): load + preview OK; controls save/chỉnh disabled.

### 8.4. State management (gợi ý)

```text
project, timeline, candidate_sets, clips_by_id, segments_by_id, videos_by_id
selected_segment_id, selected_visual_item_id
dirty, validation_errors, save_status
```

Mỗi thao tác chỉnh = transaction nhỏ (vd. `replaceClip` cập nhật đồng thời clip_id, video_id, source_path, clip_start/end, speed, rank, locked, user_edited, validation).

### 8.5. API nội bộ (nếu có backend)

```text
GET  /api/project
GET  /api/media/video?path=...
GET  /api/media/audio?path=...
POST /api/timeline/validate
POST /api/timeline/save
```

`POST /api/timeline/save` phải validate trước khi ghi `data/intermediate/timeline.json`.

---

## 9. Handoff condition

Review UI bàn giao sang Renderer khi:

| # | Điều kiện |
|---|-----------|
| 1 | `timeline.json` đã save; parse được; `project_id` đúng |
| 2 | `render_settings` hợp lệ; `updated_at` phản ánh lần save cuối |
| 3 | Mỗi segment cần render có ≥ 1 visual item |
| 4 | Không còn validation **error** |
| 5 | `source_path` resolve được; `clip_start/end`, `timeline_start/end`, `speed`, `transition` hợp lệ |

| Tình huống | UI |
|------------|-----|
| Còn `needs_review=true` | Cảnh báo; vẫn render nếu không có error kỹ thuật |
| Còn `visual_items=[]` | Cảnh báo rõ; **không** nên cho Render nếu Renderer MVP fail |

Renderer chỉ tin `timeline.json` trên disk — không đọc UI state. Chi tiết: [`02` §14.5](./02_data_contract.md#145-kiểm-tra-timelinejson).

---

## 10. Test cases

| ID | Mô tả | Kỳ vọng |
|----|-------|---------|
| T01 | Load 5 file hợp lệ | Segment list đúng; segment đầu chọn; không error |
| T02 | `project_id` không khớp | Báo lỗi; không save; không sửa project_id |
| T03 | Segment `needs_review=true` | Highlight; filter Needs review |
| T04 | `candidates_ref` → top-k | Sort rank; score/reason hiển thị |
| T05 | Đổi clip rank 2 | `clip_id`, `video_id`, `source_path`, `source_candidate_rank=2`, `user_edited=true` |
| T06 | `visual_items=[]` + candidate OK | Tạo visual mới; `timeline_item_id` hợp lệ |
| T07 | Chỉnh `clip_start/end` | Validate speed; error nếu range sai |
| T08 | Chỉnh `speed=1.1` | Cập nhật `clip_end`; error nếu vượt clip range hoặc speed ngoài range |
| T09 | Save sau đổi clip | `updated_at` đổi; file ghi đè `data/intermediate/timeline.json`; reload giữ chỉnh sửa |
| T10 | Đổi clip | `candidates_ref` giữ nguyên |
| T11 | `--readonly` | Preview OK; save disabled |
| T12 | `speed=1.5` | Validation error; không save / không handoff Renderer |

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

---

## 11. Acceptance criteria

Module Review UI đạt MVP khi:

1. Load 5 JSON; validate `project_id`.
2. Hiển thị segment list, transcript, timing, confidence, score, needs_review, fallback.
3. Highlight segment cần review; filter hoạt động.
4. Hiển thị visual hiện tại; preview clip MVP.
5. Hiển thị top-k theo `candidates_ref`; disable candidate invalid.
6. Đổi clip từ top-k — cập nhật đúng visual fields + `user_edited`.
7. Chỉnh `clip_start/end`, `speed`, `transition`, `crop_mode`, `volume`, `locked` trong phạm vi §6.
8. **Không** sửa `matching_candidates`, `clip_metadata`, `audio_segments`.
9. **Không** đổi `segment_id`, `audio_start/end`, `text`, `confidence`, `score`, `candidates_ref`.
10. Validate trước save; phân loại error/warning.
11. Save ghi đè `data/intermediate/timeline.json`; cập nhật `updated_at`.
12. Dirty state + cảnh báo rời trang; read-only mode.
13. Cảnh báo `visual_items=[]`; Renderer dùng timeline sau save.

---

## 12. Checklist

```text
[ ] Đã đọc 00, 01, 02 và stage spec này
[ ] Load timeline, matching_candidates, clip_metadata, audio_segments, media_metadata
[ ] project_id khớp
[ ] UI layout §7.1 — segment list, preview, candidates, inspector
[ ] Highlight needs_review, low confidence, fallback, missing visual
[ ] Map candidates_ref → candidate_set_id; top-k đúng rank
[ ] Đổi clip: cập nhật clip_id, video_id, source_path, clip_start/end, speed, rank
[ ] visual_items=[] → cho tạo visual từ candidate
[ ] Giữ candidates_ref sau đổi clip
[ ] Chỉ sửa field §6.1; không sửa field §6.2
[ ] speed trong [0.75, 1.25]; transition/crop allowed
[ ] Mark reviewed không đổi confidence/score
[ ] Validate §8.1 trước save; error → không lưu
[ ] Save explicit → ghi đè data/intermediate/timeline.json
[ ] Cập nhật updated_at; preserve schema_version, project_id, audio_id, created_at
[ ] Dirty state + cảnh báo chưa lưu
[ ] --readonly hoạt động
[ ] Test T01–T12 §10
[ ] Handoff §9 — Renderer đọc timeline sau save
```
