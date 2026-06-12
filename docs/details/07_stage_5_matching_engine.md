# 07. Stage 5 — Matching Engine

| Module | `matching_engine/` |
| Core docs | [00](00_project_scope.md) · [01](01_system_architecture.md) · [02](02_data_contract.md) |
| Schema/Sample | [docs/schemas/matching_candidates.schema.md](../schemas/matching_candidates.schema.md) · [docs/samples/matching_candidates_sample.json](../samples/matching_candidates_sample.json) |

## 1. Mục tiêu stage

Stage 5 — Matching Engine tìm top-k clip phù hợp nhất cho từng audio segment, dựa trên `audio_segments.json`, `clip_metadata.json`, `embedding_metadata.json` và vector/index files từ Stage 4.

Stage này quyết định đoạn lời nói nào nên được gợi ý với những clip nào. Output chưa phải timeline dựng video cuối — là danh sách candidate clip có score, rank, confidence và lý do đề xuất để Timeline Planner và Review UI sử dụng.

Mục tiêu chính:

* Đọc `audio_segments.json`, `clip_metadata.json`, `embedding_metadata.json`.
* Load text embeddings và visual embeddings hoặc visual index.
* So khớp từng audio segment với clip candidate.
* Gộp score keyframe-level về clip-level nếu embedding theo keyframe.
* Tính `semantic_score` và các score phụ; áp dụng penalty.
* Trả về top-k clip cho từng audio segment.
* Chọn clip rank 1 làm `selected_clip_id` mặc định nếu đủ điều kiện.
* Gán `confidence`; đánh dấu fallback nếu không có clip khớp tốt.
* Xuất `matching_candidates.json` đúng Data Contract hiện hành.
* Xuất log phụ để debug scoring, ranking và fallback nếu cần.

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  ① ──► ② ─┐
           ├──► ④ ──► ⑤ ──► ⑥ ──► ⑦ ──► ⑧
       ③ ─┘              ▲
                    Stage này

  ── Chi tiết Stage ⑤ ─────────────────────────────────────

  ② audio_segments.json ────────┐
  ③ clip_metadata.json ─────────┼──►
  ④ embedding_metadata.json ────┤    embeddings/ + index/
                                ▼
                 ┌─────────────────────────────┐
                 │  ⑤ Matching Engine           │  ◄── bạn ở đây
                 └─────────────┬───────────────┘
                               │ ghi
                               ├─ matching_candidates.json
                               └─ matching_engine_log.json
                               │
                               ▼
                         ⑥ Timeline Planner
```

| | |
|---|---|
| **Đọc (IN)** | `audio_segments.json`, `clip_metadata.json`, `embedding_metadata.json`, vector/index |
| **Ghi (OUT)** | `matching_candidates.json`, `matching_engine_log.json` |
| **Downstream** | Stage ⑥ (chọn clip mặc định), ⑦ (hiển thị top-k theo `candidates_ref`) |

Không render video, không tạo timeline — chỉ xếp hạng candidate clip theo segment. Chi tiết: [01 §4.5](01_system_architecture.md#45-matching-engine).

## 3. Trách nhiệm

### 3.1. Làm

1. Đọc ba file metadata chính; validate `project_id` khớp.
2. Load text embedding theo `segment_id`; load visual embedding hoặc visual index.
3. Map visual embedding/index result về `clip_id`.
4. Lọc clip candidate theo `status`.
5. Tính semantic similarity; gộp keyframe score về clip nếu cần.
6. Tính `visual_quality_score`, `duration_fit_score`, `continuity_score`, `diversity_score` nếu có dữ liệu.
7. Áp dụng penalty; tính `final_score`; sắp xếp và lấy top-k.
8. Gán `selected_clip_id`, `confidence`, `reason`, `fallback_used`.
9. Xuất `matching_candidates.json` và log phụ nếu cần.

### 3.2. Không làm

* Không chạy ASR, không sửa transcript/query, không detect scene, không trích keyframe.
* Không tạo embedding mới nếu embedding thiếu; không sửa `clip_metadata.json`.
* Không tạo `timeline.json`; không xử lý speed, transition, crop; không render video cuối.
* Không quyết định người dùng có chấp nhận clip hay không.

Embedding thiếu hoặc metadata lỗi → báo lỗi, fallback hoặc bỏ qua candidate theo rule — không tự chạy lại stage trước.

## 4. Input cần đọc

### 4.1. Files

| File | Nguồn | Mục đích |
| ---- | ----- | -------- |
| `data/intermediate/audio_segments.json` | Stage 2 | Segment, duration, query, `segment_id` |
| `data/intermediate/clip_metadata.json` | Stage 3 | Clip candidate, duration, quality, `status` |
| `data/intermediate/embedding_metadata.json` | Stage 4 | Mapping segment/clip/keyframe ↔ vector/index |
| Vector files | `embedding_metadata.json → vector_path` | Text/visual embeddings |
| Visual index | `embedding_metadata.json → index.path` | Search nhanh (optional) |

Vector/index load theo path ghi trong `embedding_metadata.json`. Quy ước path: [02 §2.6](02_data_contract.md#26-path).

### 4.2. Fail-fast

Ba file chính: parse được; có `schema_version`, `project_id` — **ba file phải cùng `project_id`**.

**`audio_segments.json`:** `items` không rỗng; mỗi segment có `segment_id`, `start`, `end`, `duration`, `query` không rỗng.

**`clip_metadata.json`:** `items` không rỗng; mỗi clip có `clip_id`, `duration`; `quality_score` ∈ `[0.0, 1.0]` hoặc `null`; MVP nên có `status`.

**`embedding_metadata.json`:** `model.name`, `model.type`, `model.dimension`; `text_embeddings` và `visual_embeddings` không rỗng; `embedding_id` không trùng; text map được `segment_id`; visual map được `clip_id`/`keyframe_id`; `vector_path` load được nếu khác `null`; `index.path` load được nếu dùng index.

Nếu Stage 4 dùng quy tắc index row `i` ↔ `visual_embeddings[i]`, Matching Engine phải giữ đúng rule khi đọc kết quả search.

### 4.3. Clip được matching

Trong MVP, xét clip có:

```text
status = usable
status = low_quality
```

Không chọn mặc định:

```text
status = too_short
status = error
```

| `status` | Quy tắc |
| -------- | ------- |
| `usable` | Xếp hạng bình thường |
| `low_quality` | Vẫn xếp hạng; áp dụng `bad_clip_penalty` |
| `too_short` | Bỏ qua MVP hoặc fallback đặc biệt |
| `error` | Luôn bỏ qua |

Thiếu `status`: clip có keyframe/embedding hợp lệ → xử lý như usable tạm; warning trong log.

Clip không có visual embedding hợp lệ → không đưa vào candidate chính.

### 4.4. Config nội bộ

```json
{
  "project_id": "demo_01",
  "audio_segments_path": "data/intermediate/audio_segments.json",
  "clip_metadata_path": "data/intermediate/clip_metadata.json",
  "embedding_metadata_path": "data/intermediate/embedding_metadata.json",
  "output_dir": "data/intermediate",
  "top_k": 5,
  "similarity": {
    "metric": "cosine",
    "normalize_vectors": true
  },
  "score_weights": {
    "semantic": 0.60,
    "visual_quality": 0.15,
    "duration_fit": 0.15,
    "continuity": 0.05,
    "diversity": 0.05
  },
  "penalties": {
    "low_quality": 0.10,
    "recent_repetition": 0.15
  },
  "confidence_thresholds": {
    "high": 0.75,
    "medium": 0.50
  },
  "fallback": {
    "enabled": true,
    "allow_low_quality": true
  }
}
```

| Tham số | Giá trị đề xuất MVP |
| ------- | ------------------- |
| `top_k` | `5` |
| `similarity.metric` | `cosine` |
| `similarity.normalize_vectors` | `true` |
| `score_weights.semantic` | `0.60` |
| `score_weights.visual_quality` | `0.15` |
| `score_weights.duration_fit` | `0.15` |
| `score_weights.continuity` | `0.05` |
| `score_weights.diversity` | `0.05` |
| `penalties.low_quality` | `0.10` |
| `penalties.recent_repetition` | `0.15` |
| `confidence_thresholds.high` | `0.75` |
| `confidence_thresholds.medium` | `0.50` |

Ghi chú: `final_score` clamp về `[0.0, 1.0]`. Chưa làm continuity/diversity → score `null` hoặc weight `0`. Semantic score là lõi MVP.

## 5. Output cần tạo

| Output | Path | Contract? |
| ------ | ---- | --------- |
| Matching candidates | `data/intermediate/matching_candidates.json` | **Có** — stage chính |
| Matching log | `data/intermediate/matching_engine_log.json` | Không — debug only |

Các module sau chỉ phụ thuộc `matching_candidates.json`. Nếu mâu thuẫn với log, ưu tiên `matching_candidates.json`.

## 6. Contract fields stage trực tiếp dùng

### 6.1. Đọc từ input upstream

→ Audio: [02 §5](02_data_contract.md#5-audio_segmentsjson) · [audio_segments.schema.md](../schemas/audio_segments.schema.md) · [audio_segments_sample.json](../samples/audio_segments_sample.json)

→ Clip: [02 §6](02_data_contract.md#6-clip_metadatajson) · [clip_metadata.schema.md](../schemas/clip_metadata.schema.md) · [clip_metadata_sample.json](../samples/clip_metadata_sample.json)

→ Embedding: [02 §7](02_data_contract.md#7-embedding_metadatajson) · [embedding_metadata.schema.md](../schemas/embedding_metadata.schema.md) · [embedding_metadata_sample.json](../samples/embedding_metadata_sample.json)

| Nguồn | Field đọc | Quy tắc stage |
| ----- | --------- | ------------- |
| `audio_segments` | `segment_id`, `duration`, `query`, `segment_type`, `needs_review` | Một candidate set / segment |
| `clip_metadata` | `clip_id`, `duration`, `quality_score`, `status` | Lọc status; quality cho score |
| `embedding_metadata` | `text_embeddings`, `visual_embeddings`, `index`, `model` | Load vector; map index result |

### 6.2. Ghi `matching_candidates.json`

→ [02 §8](02_data_contract.md#8-matching_candidatesjson) · schema: [matching_candidates.schema.md](../schemas/matching_candidates.schema.md) · sample: [matching_candidates_sample.json](../samples/matching_candidates_sample.json)

**Top-level ghi:** `schema_version`, `project_id`, `top_k`, `created_at`, `items`.

**Candidate set item — quy tắc stage:**

| Field | Quy tắc |
| ----- | ------- |
| `candidate_set_id` | `candidates_{segment_id}` — ví dụ `candidates_a001` |
| `audio_segment_id` | Phải tồn tại trong `audio_segments.json` |
| `selected_clip_id` | Clip rank 1 nếu có candidate; `null` nếu không |
| `confidence` | `high` / `medium` / `low` — xem §7.8 |
| `candidates` | Tối đa `top_k` item; sort theo `final_score` giảm dần |
| `fallback_used` | `true` khi dùng fallback |
| `reason`, `notes` | Optional; nên ghi khi fallback hoặc confidence thấp |

**Candidate item — quy tắc stage:**

| Field | Quy tắc |
| ----- | ------- |
| `rank` | Bắt đầu `1`; tăng dần; không trùng `clip_id` trong cùng set |
| `clip_id` | Phải tồn tại trong `clip_metadata.json` — **clip-level, không keyframe_id** |
| `final_score` | ∈ `[0.0, 1.0]` |
| `semantic_score`, `visual_quality_score`, `duration_fit_score`, `continuity_score`, `diversity_score` | ∈ `[0.0, 1.0]` hoặc `null` — không ghi score giả |
| `repetition_penalty`, `bad_clip_penalty` | ∈ `[0.0, 1.0]` hoặc `null` |
| `reason` | Optional; giải thích penalty hoặc đề xuất |

**MVP:** Một candidate set cho mỗi audio segment; `top_k = 5`; không tạo candidate giả để đủ số lượng.

## 7. Quy trình xử lý riêng

### 7.1. Bước 1 — Load embeddings

* Map `segment_id → text_vector`; validate dimension = `model.dimension`.
* Map visual embedding → `clip_id`, `keyframe_id`; load index nếu có.
* Thiếu text embedding cho segment → warning/error trong log.

### 7.2. Bước 2 — Lọc clip candidate

Danh sách clip matching: `usable`, `low_quality`. Loại `too_short`, `error`. Clip không có visual embedding → loại khỏi candidate chính.

### 7.3. Bước 3 — Tính semantic score

Với mỗi audio segment:

1. Lấy text vector theo `segment_id`.
2. So sánh với visual vectors (toàn bộ hoặc qua index search).
3. Tính similarity (cosine nếu config).

Nếu cosine với vector đã normalize:

```text
cosine_similarity ∈ [-1.0, 1.0]
semantic_score = (cosine_similarity + 1.0) / 2.0
```

Model/index trả score sẵn trong `[0.0, 1.0]` → dùng trực tiếp; ghi rõ trong log.

**Gộp keyframe → clip:** contract trả `clip_id`, không `keyframe_id`.

```text
semantic_score_clip = max(semantic_score_keyframes_of_clip)
```

MVP dùng `max` — một keyframe khớp tốt đủ đại diện clip. Có thể thử average/weighted sau.

### 7.4. Bước 4 — Tính score phụ

**`duration_fit_score`:** đo clip có đủ thời lượng so với audio segment.

```text
if clip.duration >= audio_segment.duration:
    duration_fit_score = 1.0
else:
    duration_fit_score = clip.duration / audio_segment.duration
clamp về [0.0, 1.0]
```

Timeline Planner xử lý cắt/speed cụ thể — Matching Engine chỉ đánh giá tương đối.

**`visual_quality_score`:** lấy từ `clip_metadata.quality_score`.

* Có number → dùng trực tiếp.
* `null` → output `null`; scoring nội bộ có thể dùng `0.5` trung tính nhưng **không ghi `0.5` vào output** nếu chỉ là giá trị nội bộ.

**`continuity_score` (optional MVP):** clip nối hợp với segment trước — tránh cùng clip liên tiếp, ưu tiên clip gần nhau trong cùng video nếu semantic tương đương. Chưa triển khai → `null`, weight `0`.

**`diversity_score` (optional MVP):** top-k không toàn clip giống nhau / cùng video timestamp gần. Chưa triển khai → `null`, weight `0`.

### 7.5. Bước 5 — Áp dụng penalty

Penalty là điểm trừ ∈ `[0.0, 1.0]` — cao hơn = phạt nhiều hơn.

| Penalty | Khi dùng | Giá trị đề xuất |
| ------- | -------- | --------------- |
| `bad_clip_penalty` | `status = low_quality` hoặc quality thấp | `0.10` |
| `repetition_penalty` | Clip trùng segment liền trước hoặc quá giống candidate khác | `0.15` |

Nếu clip bị tụt rank vì penalty → ghi `reason` hoặc log giải thích.

### 7.6. Bước 6 — Tính `final_score`

Công thức MVP:

```text
base_score =
    0.60 * semantic_score
  + 0.15 * visual_quality_score_effective
  + 0.15 * duration_fit_score
  + 0.05 * continuity_score_effective
  + 0.05 * diversity_score_effective

final_score = base_score - repetition_penalty - bad_clip_penalty
final_score = clamp(final_score, 0.0, 1.0)
```

Trong đó `*_effective` là giá trị dùng nội bộ khi optional score `null` (weight `0` hoặc trung tính nội bộ). **Output field optional chưa có dữ liệu thật → `null`** — không ghi score giả chỉ để đủ công thức.

Nguyên tắc scoring:

* Semantic score là thành phần quan trọng nhất — clip đẹp nhưng không liên quan không nên thắng chỉ vì quality cao.
* Quality hỗ trợ ranking, không chi phối hoàn toàn.
* Duration fit hỗ trợ timeline — không xử lý speed/cut ở Stage 5.

### 7.7. Bước 7 — Top-k và `selected_clip_id`

Với mỗi audio segment:

1. Tính score mọi clip hợp lệ; gộp theo `clip_id`.
2. Sort `final_score` giảm dần; loại trùng `clip_id`.
3. Lấy tối đa `top_k` clip; gán `rank` từ `1`.
4. `selected_clip_id` = clip rank 1 nếu có candidate đủ điều kiện.

Quy tắc top-k:

| Quy tắc | Chi tiết |
| ------- | -------- |
| Clip-level | Output theo `clip_id`, không `keyframe_id` |
| Không trùng clip | Một set không có cùng `clip_id` hai lần |
| Không đủ top-k | Trả ít hơn `top_k` — không candidate giả |
| Nhiều keyframe cùng clip | Dùng keyframe tốt nhất cho clip-level score |

Ví dụ **sai:** rank 1 `v01_c003_k01`, rank 2 `v01_c003_k02`. **Đúng:** rank 1 `v01_c003`.

### 7.8. Bước 8 — Confidence mapping

Ba mức: `high`, `medium`, `low`.

Rule đề xuất:

```text
if fallback_used:
    confidence = low
else if selected final_score >= 0.75:
    confidence = high
else if selected final_score >= 0.50:
    confidence = medium
else:
    confidence = low
```

Có thể kết hợp thêm: chênh lệch rank 1 vs rank 2; `semantic_score` riêng; `needs_review` của segment; `status` clip được chọn.

Segment `needs_review = true` → có thể giảm confidence một mức hoặc ghi `notes`. Segment `abstract` → chấp nhận clip bối cảnh chung; có thể confidence thấp hơn.

Fallback luôn → `confidence = low`.

### 7.9. Bước 9 — Fallback

Fallback khi không có clip khớp đủ tốt:

* Semantic score quá thấp cho mọi clip.
* Segment trừu tượng / query mơ hồ.
* Thiếu embedding cho segment.
* Footage không có cảnh liên quan.

Hành vi fallback (`fallback.enabled = true`):

* Chọn clip `usable` quality cao; ưu tiên chưa dùng gần đây; duration đủ dài.
* `fallback_used = true`; `confidence = low`; ghi `reason` rõ.
* `fallback.allow_low_quality = true` → có thể chọn clip low_quality nếu không còn usable tốt.

Không có clip usable nào:

```text
selected_clip_id = null
candidates = []
confidence = low
fallback_used = true
```

Candidate set **vẫn tồn tại** cho segment — Timeline Planner xử lý tiếp hoặc báo cần người dùng can thiệp.

Fallback không phải lỗi — quan trọng là không giả confidence cao và ghi reason đủ rõ cho UI.

### 7.10. Bước 10 — Ghi output

Validate trước khi ghi: top-level fields; `top_k` integer dương; candidate set mỗi segment; `candidate_set_id` không trùng; `selected_clip_id` null hoặc khớp `candidates[]`; `confidence` allowed; rank hợp lệ; `final_score` ∈ `[0.0, 1.0]`.

**Log phụ:** config top-k/weights, số segment matched, fallback count, segment thiếu embedding, score stats, warnings/errors. Cấu trúc đề xuất — không phải inter-module schema.

## 8. Error / fallback / re-run behavior

### 8.1. Lỗi chặn pipeline

| Tình huống | Hành vi |
| ---------- | ------- |
| `project_id` không khớp | Dừng; không metadata giả |
| `embedding_metadata` không load được | Dừng hoặc báo lỗi chặn |
| Không load được vector/index bắt buộc | Dừng; báo lỗi rõ |

### 8.2. Cảnh báo không chặn

| Tình huống | Hành vi |
| ---------- | ------- |
| Segment thiếu text embedding | Warning; fallback hoặc candidate rỗng |
| Một số segment `confidence = low` | Pipeline chạy tiếp — UI highlight |
| Clip `low_quality` trong top-k | Hợp lệ với penalty/reason |

### 8.3. Ràng buộc stage

* Không ghi `timeline.json`; candidate chỉ có `clip_id`.
* Không chọn clip `error`; không chọn `too_short` mặc định MVP.
* Không bịa score — chưa tính → `null`.
* Không phụ thuộc `matching_engine_log.json`.

Quy ước score, confidence, ID: [02 §2](02_data_contract.md#2-quy-ước-chung).

### 8.4. Re-run

* Cùng `project_id` + input/config không đổi → `candidate_set_id` ổn định.
* Rank có thể thay nếu score formula hoặc embedding thay đổi.
* Không `--overwrite` → dừng an toàn.
* Có `--overwrite` → ghi đè output và log.
* Nếu đã có `timeline.json` từ matching cũ → chạy lại Timeline Planner.

## 9. Handoff condition

Stage 5 bàn giao `matching_candidates.json` cho Timeline Planner khi:

```text
matching_candidates.json parse được
có đủ top-level required fields
top_k là integer dương
items không rỗng
candidate set cho mỗi audio segment
candidate_set_id không trùng
audio_segment_id map đúng segment
confidence ∈ high/medium/low
selected_clip_id null hoặc khớp candidates[].clip_id
candidate rank hợp lệ; clip_id không trùng trong cùng set
clip_id map đúng clip_metadata
final_score ∈ [0.0, 1.0]
```

Consumer: Timeline Planner (`selected_clip_id`, `confidence`, `candidates`); Review UI (top-k thay thế); Evaluation (semantic avg, fallback rate). Chi tiết: [01 §4.5](01_system_architecture.md#45-matching-engine) và [02 §13](02_data_contract.md#13-quy-tắc-mapping-giữa-các-file).

Segment `confidence = low` → pipeline vẫn chạy; Timeline Planner đánh dấu `needs_review`. Segment không có candidate → set vẫn tồn tại với `selected_clip_id = null`, `fallback_used = true`.

## 10. Test cases

| # | Test | Input / điều kiện | Kỳ vọng |
| - | ---- | ----------------- | ------- |
| 1 | Input hợp lệ | Ba metadata + vector/index | `matching_candidates.json`; set mỗi segment; `top_k` đúng config |
| 2 | `project_id` không khớp | Ba file khác ID | Dừng; không metadata giả |
| 3 | Gộp keyframe → clip | Nhiều keyframe cùng clip | Một candidate `clip_id`; không trùng trong set |
| 4 | Rank và score | Output candidates | Sort `final_score` giảm; rank từ 1; scores ∈ `[0.0, 1.0]` hoặc `null` |
| 5 | `final_score` formula | Clip có đủ score phụ | Weights 0.60/0.15/0.15/0.05/0.05; penalty trừ đúng; clamp `[0.0, 1.0]` |
| 6 | Clip `low_quality` | Status low_quality | Có thể trong candidates; `bad_clip_penalty` hoặc reason |
| 7 | Clip `too_short` / `error` | Status không matching | Không trong candidates mặc định |
| 8 | Fallback | Semantic score rất thấp | `fallback_used = true`; `confidence = low`; reason rõ |
| 9 | Không candidate | Không clip usable | Set tồn tại; `selected_clip_id = null`; `candidates = []` |
| 10 | `selected_clip_id` | Có/không candidate | Rank 1 nếu có; `null` nếu không; khớp `candidates[]` |
| 11 | Confidence | Mọi set | `high`/`medium`/`low`; fallback → `low` |
| 12 | Top-k | Ít hơn `top_k` clip hợp lệ | Trả đúng số có; không candidate giả |
| 13 | Chạy lại module | Output đã tồn tại | Không `--overwrite` → dừng; có → ghi đè; ID ổn định |

CLI tối thiểu: `python -m matching_engine.main --audio-segments data/intermediate/audio_segments.json --clip-metadata data/intermediate/clip_metadata.json --embedding-metadata data/intermediate/embedding_metadata.json --output-dir data/intermediate --top-k 5`.

## 11. Acceptance criteria

Module Matching Engine đạt yêu cầu MVP khi:

1. Đọc được ba file input; validate `project_id` khớp.
2. Load text/visual embedding hoặc index; map về `clip_id`.
3. Tạo candidate set cho mỗi audio segment.
4. Gộp keyframe score về clip-level (`max`); không trùng `clip_id` trong set.
5. Tính `semantic_score` và `final_score` theo công thức §7.6 trong `[0.0, 1.0]`.
6. Top-k đúng rule; sort rank đúng; không candidate giả.
7. `selected_clip_id` đúng rule; `confidence` mapping đúng §7.8.
8. Penalty cho `low_quality` và repetition hoạt động.
9. Fallback đánh dấu rõ `fallback_used`; không giả confidence cao.
10. Clip `error` không trong candidates; `too_short` không mặc định MVP.
11. `matching_candidates.json` đúng schema; log phụ hỗ trợ debug.
12. Timeline Planner dùng `selected_clip_id`; Review UI hiển thị top-k.
13. Có quy tắc rõ khi chạy lại cùng `project_id`.

## 12. Checklist

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc schema/sample matching_candidates
[ ] Đọc được audio_segments, clip_metadata, embedding_metadata
[ ] Kiểm tra project_id các file khớp nhau
[ ] Load được text embeddings và visual embeddings hoặc index
[ ] Map index result về visual_embeddings nếu dùng index
[ ] Map visual embedding về clip_id
[ ] Lọc clip theo status usable/low_quality
[ ] Không xuất keyframe_id làm candidate
[ ] Gộp keyframe score về clip-level (max)
[ ] Tính semantic_score và final_score theo công thức MVP
[ ] Weights: 0.60 semantic + 0.15 quality + 0.15 duration + 0.05 continuity + 0.05 diversity
[ ] Áp dụng bad_clip_penalty và repetition_penalty
[ ] Sort candidate theo final_score; rank từ 1
[ ] Không trùng clip_id trong cùng candidate set
[ ] Top-k đúng rule; không candidate giả
[ ] Sinh candidate_set_id dạng candidates_a001
[ ] Gán selected_clip_id và confidence đúng rule
[ ] Đánh dấu fallback_used khi fallback
[ ] Ghi reason đủ hiểu
[ ] Ghi đúng matching_candidates.json
[ ] Ghi được matching_engine_log.json
[ ] Không hard-code path cá nhân
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương
[ ] Có test với dữ liệu mẫu nhỏ
[ ] Output có thể đưa cho Timeline Planner chạy tiếp
```
