# 10. Stage 8 — Renderer

| | |
|---|---|
| **Module** | `renderer/` |
| **Core docs** | [`00`](./00_project_scope.md) · [`01`](./01_system_architecture.md) · [`02`](./02_data_contract.md) |
| **Schema / Sample** | [`timeline.schema.md`](../schemas/timeline.schema.md) · [`render_config.schema.md`](../schemas/render_config.schema.md) · [`render_log.schema.md`](../schemas/render_log.schema.md) · [`timeline_sample.json`](../samples/timeline_sample.json) · [`render_config_sample.json`](../samples/render_config_sample.json) · [`render_log_sample.json`](../samples/render_log_sample.json) |
| **Stage spec** | File này |

---

## 1. Mục tiêu stage

Stage 8 — Renderer xuất video cuối từ `timeline.json` (Timeline Planner tạo, Review UI cập nhật).

Renderer **thực thi** bản dựng — không chọn clip, không tính score, không sửa matching. Cắt clip, chỉnh speed, scale/crop, ghép đoạn, mix audio, xuất `final_video.mp4`.

**Mục tiêu cụ thể:**

* Đọc `timeline.json`, `media_metadata.json`; optional `clip_metadata.json`, `render_config.json`.
* Validate timeline trước render.
* Render từng visual item; ghép theo `timeline_start/end`.
* Voice-over làm audio chính; mute/mix audio gốc video theo setting.
* Xuất `data/final/final_video.mp4` và `data/intermediate/render_log.json`.

**Không phải mục tiêu:** ASR, matching, sửa `timeline.json`, UI review (→ §3.2).

---

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  ① ──► ② ─┐
           ├──► ④ ──► ⑤ ──► ⑥ ──► ⑦ ──► ⑧
       ③ ─┘                              ▲
                                    Stage này (cuối pipeline)

  ── Chi tiết Stage ⑧ ─────────────────────────────────────

  ⑦ timeline.json (đã chỉnh) ────┐
  ① media_metadata.json ──────────┤
     normalized video + voice-over ┤
  ③ clip_metadata.json (optional) ┤
     render_config.json (optional) ┘
                                   ▼
                 ┌─────────────────────────────┐
                 │  ⑧ Renderer                  │  ◄── bạn ở đây
                 └─────────────┬───────────────┘
                               │ ghi
                               ├─ final_video.mp4
                               └─ render_log.json
```

| | |
|---|---|
| **Đọc (IN)** | `timeline.json`, `media_metadata.json`, normalized media; optional `clip_metadata.json`, `render_config.json` |
| **Ghi (OUT)** | `final_video.mp4`, `render_log.json` |
| **Downstream** | Evaluation đọc output render; không có stage pipeline tiếp theo |

Không chạy lại Stage ②–⑦ — chỉ dựng video từ timeline đã duyệt. Chi tiết: [`01` §4.8](./01_system_architecture.md).

---

## 3. Trách nhiệm

### 3.1. Làm (in-scope)

| # | Hành vi |
|---|---------|
| 1 | Load `timeline.json`, `media_metadata.json`; optional `render_config.json`, `clip_metadata.json` |
| 2 | Validate `project_id`, `render_settings`, `items[]`, `visual_items[]` |
| 3 | Kiểm tra media source + voice-over tồn tại |
| 4 | Build render plan nội bộ từ timeline |
| 5 | Cắt video `clip_start/end`; apply `speed`; scale/crop; transition |
| 6 | Ghép visual items theo timeline order; mix voice-over (+ audio gốc nếu bật) |
| 7 | Xuất `final_video.mp4`; ghi `render_log.json` |

### 3.2. Không làm (out-of-scope)

| Hành vi | Thuộc |
|---------|-------|
| ASR, embedding, matching, đổi clip khi confidence thấp | Stage 2–5 |
| Sửa `timeline.json`, `matching_candidates.json`, `clip_metadata.json`, `audio_segments.json` | Upstream / Review UI |
| Mở UI review; tự suy luận clip thay thế | Stage 7 |

Timeline lỗi kỹ thuật → báo lỗi render; **không** tự sửa logic matching.

---

## 4. Input cần đọc

### 4.1. Files

| File | Path | Bắt buộc MVP |
|------|------|--------------|
| Timeline | `data/intermediate/timeline.json` | **Có** |
| Media metadata | `data/intermediate/media_metadata.json` | Khuyến nghị (resolve voice-over) |
| Clip metadata | `data/intermediate/clip_metadata.json` | Optional (validate clip range) |
| Render config | `data/intermediate/render_config.json` | Optional (override settings) |

**Media thực tế:**

```text
timeline.items[].visual_items[].source_path     (video)
media_metadata.audio.normalized_path              (voice-over — xem §7.3)
```

Tối thiểu chạy được: `timeline.json` + normalized video paths trong timeline + voice-over file. `media_metadata` giúp map `audio_id` → path vì timeline không chứa voice-over path.

### 4.2. Fail-fast

**`timeline.json`:** `schema_version`, `project_id`, `audio_id`, `render_settings`, `items`; mỗi item có `segment_id`, `audio_start/end`, `duration`; item cần render có ≥ 1 visual item.

**`media_metadata.json` (nếu dùng):** `project_id` khớp; `audio.audio_id` khớp `timeline.audio_id`; `audio.normalized_path`; `audio.status ≠ error`; video usable có `normalized_path`.

**`clip_metadata.json` (nếu dùng):** `project_id` khớp; clip trong timeline tồn tại; `clip_id`/`video_id` khớp visual item.

**Media files:** tồn tại, đọc được; duration đủ cho clip range; video stream hợp lệ; voice-over đọc được.

---

## 5. Output cần tạo

| Output | Path | Contract? |
|--------|------|-----------|
| Final video | `data/final/final_video.mp4` | **Có** (artifact) |
| Render log | `data/intermediate/render_log.json` | **Có** |
| Temp segments | `data/temp/render_segments/*.mp4` | Không — nội bộ |

**`final_video.mp4`:** mp4; resolution/fps theo `render_settings`; voice-over audio chính; duration ≈ voice-over/timeline; không thiếu đoạn nếu renderer-ready.

**`render_log.json`:** canonical [`02` §11](./02_data_contract.md#11-render_logjson) · [`render_log.schema.md`](../schemas/render_log.schema.md) · [`render_log_sample.json`](../samples/render_log_sample.json).

| `status` | Ý nghĩa |
|----------|---------|
| `success` | Hoàn tất, không lỗi nghiêm trọng |
| `warning` | Hoàn tất có cảnh báo |
| `failed` | Không tạo video cuối hợp lệ |

Validate fail → **không** tạo `final_video.mp4` mới; vẫn ghi/cập nhật `render_log.json` với `status=failed`.

Temp files: cleanup sau success nếu `--cleanup-temp`; giữ nếu debug (`--keep-temp`).

---

## 6. Contract fields stage trực tiếp dùng

### 6.1. Đọc từ `timeline.json`

→ [`02` §9](./02_data_contract.md#9-timelinejson) · [`timeline.schema.md`](../schemas/timeline.schema.md)

| Field đọc | Dùng cho |
|-----------|----------|
| `audio_id` | Resolve voice-over qua `media_metadata` |
| `render_settings` | width, height, fps, format, crop_mode, transition default, keep_original_audio, original_audio_volume |
| `items[].segment_id` | Log, validate |
| `items[].visual_items[]` | Toàn bộ render plan |

**Visual item đọc:** `timeline_item_id`, `clip_id`, `video_id`, `source_path`, `clip_start/end`, `timeline_start/end`, `speed`, `transition`, `crop_mode`, `volume`, `effect`.

Renderer **không** dùng: `candidates_ref`, `score`, `confidence`, `source_candidate_rank` để quyết định clip.

### 6.2. Ghi `render_log.json`

→ [`02` §11](./02_data_contract.md#11-render_logjson)

Required: `schema_version`, `project_id`, `started_at`, `finished_at`, `status`, `output_path`, `duration`, `render_time`, `warnings`, `errors`.

Nên thêm (optional): `settings` (config cuối), `summary` (counts), `items[]` per visual (`timeline_item_id`, `segment_id`, `clip_id`, `status`, `temp_path`, `duration`).

Ghi: render settings cuối, voice-over path, số items/visual, segment lỗi, FFmpeg error rút gọn, render time. Không ghi binary, log FFmpeg quá dài, absolute path cá nhân.

### 6.3. Config merge — `render_config.json` (optional)

→ [`render_config.schema.md`](../schemas/render_config.schema.md) · [`render_config_sample.json`](../samples/render_config_sample.json)

MVP: `timeline.render_settings` là nguồn chính. `render_config.json` có thể override output/audio/video paths và settings.

**Thứ tự ưu tiên (config render):**

1. CLI argument explicit
2. `render_config.json`
3. `timeline.render_settings`
4. Default Renderer

Ghi nguồn config cuối vào `render_log.json`.

**Allowed values:**

```text
format: mp4
transition: cut, fade, crossfade
crop_mode: fit, fill, center_crop, blur_background
speed: 0.75 – 1.25
effect: null, none
```

Giá trị ngoài allowed list → dừng render (field ảnh hưởng output) + ghi lỗi `render_log`; không tự đoán thay thế trừ khi config cho phép (vd. transition fallback).

---

## 7. Quy trình xử lý riêng

### 7.1. Luồng chính

```text
1. Load timeline + metadata (+ optional clip_metadata, render_config)
2. Merge effective render settings (§6.3)
3. Validate timeline (§7.2) — fail → render_log failed, exit
4. Resolve voice-over path (§7.3)
5. Build render plan — flatten visual items, sort timeline_start ASC
6. Với mỗi visual item: render temp segment (cut, speed, scale/crop, transition)
7. Concat video stream theo timeline order
8. Ghép/mix voice-over (+ audio gốc nếu bật)
9. Xuất final_video.mp4
10. Ghi render_log.json (status, paths, warnings, errors, per-item status)
```

Render plan là cấu trúc nội bộ — không phải public contract. Sort **chỉ** theo `timeline_start`, `timeline_end` — không theo `clip_id`, rank, score.

### 7.2. Validate timeline trước render

**Top-level:** `schema_version`, `project_id`, `audio_id`, `render_settings` (required fields), `items` không rỗng, `created_at`; `updated_at` nếu đã qua Review UI.

**Timeline item:** `segment_id` không rỗng; `audio_start >= 0`; `audio_end > audio_start`; `duration ≈ audio_end - audio_start`; `confidence` ∈ `high|medium|low`; `visual_items` là array.

**`visual_items = []` → FAIL (MVP):** không render segment thiếu hình; ghi lỗi segment trong `render_log.errors`. Placeholder chỉ khi được cấu hình rõ — **không** mặc định MVP.

**Visual item:** `timeline_item_id`, `clip_id`, `video_id`, `source_path` không rỗng; **`source_path` tồn tại**; `clip_start >= 0`; `clip_end > clip_start`; `timeline_start >= 0`; `timeline_end > timeline_start`; `speed` ∈ `[0.75, 1.25]`; `transition` allowed; `effect` null/none; `crop_mode` null hoặc allowed.

**Với `clip_metadata.json`:** `clip_id` tồn tại; `video_id` khớp; `clip_start >= clip.start`; `clip_end <= clip.end`.

**Continuity:** visual trong segment không overlap sai; không gap lớn; `timeline_start/end` trong `[audio_start, audio_end]`; tổng visual duration ≈ `duration`; tổng output ≈ voice-over duration. Tolerance: `0.01s` item-level; `0.10s` toàn video.

**Phân loại:**

| Mức | Ví dụ | Hành động |
|-----|-------|-----------|
| `error` | Source/voice-over missing; `speed` ngoài range; `visual_items=[]`; `format≠mp4` | **Dừng** |
| `warning` | `needs_review=true`; `confidence=low`; transition fallback về `cut` | Render tiếp nếu config cho phép |
| `info` | Video không có audio gốc | Render tiếp |

### 7.3. Voice-over path resolution

Voice-over là **audio chính**. Thứ tự resolve:

1. CLI `--voiceover` (explicit)
2. `render_config.audio.voiceover_path`
3. `media_metadata.audio.normalized_path` theo `timeline.audio_id`

Không tìm được → **dừng**; ghi lỗi `render_log`.

**Output duration:** gần bằng `media_metadata.audio.duration` hoặc duration thực tế file (FFprobe). Timeline ngắn/dài hơn audio nhiều → MVP **khuyến nghị fail** (không render video đen/silence im lặng).

### 7.4. Xử lý video per visual item

**Cắt:**

```text
source_duration = clip_end - clip_start
```

Ưu tiên đúng duration hơn tốc độ seek. FFmpeg: seek input nhanh cho MVP; trim chính xác khi cần frame-accurate final.

**Speed** (timeline là source of truth):

```text
timeline_duration = timeline_end - timeline_start
speed = source_duration / timeline_duration   (đã có trong timeline — dùng để validate, không tự tính lại trừ sai số)
```

Output segment duration = `timeline_duration`. FFmpeg: `setpts` cho video speed.

**Scale/crop** về `render_settings.width/height/fps`:

| `crop_mode` | MVP |
|-------------|-----|
| `fit` | Giữ aspect ratio + padding |
| `fill` | Scale phủ frame, có thể crop |
| `center_crop` | Scale + crop giữa (default) |
| `blur_background` | Nền blur fill + foreground fit giữa |

Visual `crop_mode` override `render_settings.crop_mode`; `null` → dùng render default.

**FPS:** convert nếu source khác output; ghi warning nếu source fps thấp/bất thường.

**Effect:** chỉ `null`/`none` — khác → dừng hoặc bỏ qua theo config (MVP: dừng).

### 7.5. Transition

Allowed: `cut`, `fade`, `crossfade`. MVP hỗ trợ chắc: **`cut`**.

Timeline Planner + Review UI giả định transition **không** đổi tổng duration output. Renderer phải giữ `timeline_start/end` là source of truth.

| Transition | MVP rule |
|------------|----------|
| `cut` | Không overlap; không đổi duration |
| `fade` | Fade in/out trong item duration; không kéo dài item |
| `crossfade` | Không bật MVP nếu chưa có rule overlap rõ |

Chưa hỗ trợ `fade`/`crossfade` → báo rõ; fallback `cut` nếu `allow_transition_fallback=true` + warning trong log.

### 7.6. Audio mix

Voice-over: full file làm bed chính (MVP không cắt theo segment).

**Audio gốc video** chỉ khi `keep_original_audio = true`.

Volume:

1. `visual_items[].volume` nếu ≠ `null`
2. Effective `original_audio_volume` (sau merge config)
3. Default `0.0`

`keep_original_audio = false` → **mute** audio gốc video. Video không có audio gốc → không lỗi.

Mix: audio gốc nhỏ hơn voice-over; `original_audio_volume` ∈ `[0.0, 1.0]`.

### 7.7. Chiến lược FFmpeg (MVP)

Dùng FFmpeg hoặc wrapper ổn định — không xử lý frame thủ công trong MVP.

**Khuyến nghị: Hướng A — render từng visual item tạm rồi concat**

```text
Ưu: dễ debug, biết segment lỗi, retry từng đoạn, lệnh đơn giản
Nhược: chậm hơn, nhiều file tạm
```

**Không khuyến nghị MVP:** Hướng B — một `filter_complex` cho toàn timeline.

**Từng visual item:**

1. Render temp `.mp4` thống nhất: width, height, fps, pixel format, codec (h264), audio format nếu có audio gốc.
2. Sort temp files theo `timeline_start`.
3. Concat list → video stream hoàn chỉnh.
4. Ghép voice-over (+ mix audio gốc).
5. Xuất mp4.

**Codec output:**

```text
video: h264, pixel yuv420p
audio: aac
container: mp4
```

Gap timeline: MVP **không** cho gap kỹ thuật — fail validate thay vì black frame placeholder.

**Lỗi giữa chừng:** một visual item fail → **dừng** pipeline MVP; ghi `timeline_item_id`, `segment_id`, `clip_id`, `source_path`, FFmpeg stderr rút gọn. Không bỏ segment lỗi rồi render video thiếu đoạn.

---

## 8. Error / fallback / re-run behavior

### 8.1. Validate fail

Không tạo `final_video.mp4` mới; ghi `render_log.json` với `status=failed`, `errors` đầy đủ.

### 8.2. Fail trên `visual_items = []`

MVP Renderer **fail** khi bất kỳ timeline item cần render có `visual_items = []`. Error message ghi rõ `segment_id`. UI nên sửa timeline trước khi render lại.

### 8.3. Concat / audio mix fail

Giữ temp nếu debug; ghi concat list path; `status=failed`. Voice-over bắt buộc mà mix fail → không xuất final im lặng.

### 8.4. Re-run

| Tình huống | Hành vi |
|------------|---------|
| `final_video.mp4` tồn tại, không `--overwrite` | Dừng an toàn |
| `--overwrite` | Ghi đè output |
| `render_log.json` | Ghi đè hoặc timestamped theo config |
| Temp từ lần trước | Cleanup nếu không debug |
| `timeline.json` | **Không sửa** |

Default output: `data/final/final_video.mp4`; `--output` cho version khác; ghi path trong log.

### 8.5. Ràng buộc

* Không đọc `matching_candidates.json` để chọn clip.
* `confidence=low` → có thể warning, vẫn render nếu timeline kỹ thuật OK.
* Không dùng keyframe để render final.
* Không hard-code absolute path.

---

## 9. Handoff condition

Stage 8 bàn giao Evaluation khi:

| # | Điều kiện |
|---|-----------|
| 1 | `data/final/final_video.mp4` tồn tại, đọc được |
| 2 | `data/intermediate/render_log.json` tồn tại |
| 3 | `render_log.status` = `success` hoặc `warning` |
| 4 | Duration ≈ voice-over/timeline; resolution/fps đúng settings |
| 5 | Output có voice-over audio |
| 6 | `render_log.errors` không có lỗi nghiêm trọng |

`status=failed` → không bàn giao như output final; Evaluation vẫn có thể đọc log báo lỗi pipeline.

Chi tiết Evaluation input: [`02` §12](./02_data_contract.md#12-evaluation_reportjson) · [`01` §4.8](./01_system_architecture.md).

---

## 10. Test cases

| ID | Mô tả | Kỳ vọng |
|----|-------|---------|
| T01 | 1 visual, `speed=1.0`, `cut` | `final_video.mp4`; duration ≈ segment; voice-over có; `status=success` |
| T02 | Nhiều segment liên tiếp | Đúng thứ tự; không gap/overlap bất thường |
| T03 | `speed=0.8` | Output duration = `timeline_end - timeline_start` |
| T04 | `speed=1.2` | Tương tự T03 |
| T05 | Crop modes `fit`, `fill`, `center_crop` | Resolution đúng; không méo |
| T06 | `source_path` không tồn tại | Không final mới; `status=failed`; error ghi path |
| T07 | Voice-over missing | Fail; error audio chính |
| T08 | `visual_items=[]` | **MVP fail**; error ghi segment |
| T09 | `crossfade` chưa hỗ trợ | Fail hoặc fallback `cut` + warning |
| T10 | `keep_original_audio=false` | Chỉ voice-over rõ; audio gốc mute |
| T11 | `keep_original_audio=true`, volume `0.2` | Mix; gốc nhỏ hơn voice-over |
| T12 | Output tồn tại, không `--overwrite` | Dừng; không ghi đè |
| T13 | `project_id` không khớp | Fail trước render |
| T14 | Timeline lỗi kỹ thuật | `render_log` tạo; `status=failed`; `errors` không rỗng |

```bash
python -m renderer.cli \
  --project-id demo_01 \
  --timeline data/intermediate/timeline.json \
  --media-metadata data/intermediate/media_metadata.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --output data/final/final_video.mp4 \
  --log-output data/intermediate/render_log.json
```

---

## 11. Acceptance criteria

Module Renderer đạt MVP khi:

1. Đọc `timeline.json`, `media_metadata.json`; optional `clip_metadata`, `render_config`.
2. Validate `project_id`, `render_settings`, items, visual items.
3. Resolve voice-over theo thứ tự §7.3; resolve video `source_path`.
4. **Fail rõ** khi `visual_items=[]`, source/voice-over thiếu, `speed` ngoài range.
5. Render 1 visual đơn giản và nhiều visual theo timeline order.
6. Cắt `clip_start/end`; apply speed; scale/crop đúng resolution/fps.
7. Hỗ trợ `transition=cut`; rule rõ cho fade/crossfade chưa hỗ trợ.
8. Voice-over audio chính; mute/mix audio gốc theo setting.
9. Xuất `final_video.mp4` (h264/aac/yuv420p) mở được player phổ biến.
10. Tạo `render_log.json` với `status`, `output_path`, `duration`, `render_time`, `errors` khi fail.
11. **Không** sửa `timeline.json`; **không** đọc Matching Engine chọn clip.
12. `--overwrite`; temp cleanup/keep rõ ràng.
13. Output + log đưa được cho Evaluation.

---

## 12. Checklist

```text
[ ] Đã đọc 00, 01, 02 và stage spec này
[ ] Đọc timeline.json, media_metadata.json
[ ] Validate project_id; merge render settings §6.3
[ ] Validate timeline §7.2 trước render
[ ] Fail nếu visual_items=[] §8.2
[ ] Resolve voice-over: CLI → render_config → media_metadata §7.3
[ ] Kiểm tra mọi source_path + voice-over tồn tại
[ ] speed trong [0.75, 1.25]; clip_start/end hợp lệ
[ ] Build render plan; sort timeline_start ASC
[ ] FFmpeg Hướng A: temp per visual → concat §7.7
[ ] Codec h264/aac/yuv420p
[ ] transition cut; rule fade/crossfade nếu chưa hỗ trợ
[ ] Voice-over audio chính; mute/mix gốc theo keep_original_audio
[ ] Xuất data/final/final_video.mp4
[ ] Ghi data/intermediate/render_log.json — status, errors khi fail
[ ] Không sửa timeline.json; không tự chọn clip
[ ] --overwrite; cleanup/keep temp
[ ] Test T01–T14 §10
[ ] Handoff §9 — Evaluation
```
