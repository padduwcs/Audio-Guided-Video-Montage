# 07. Stage 5 - Matching Engine

## 1. Mục tiêu của stage

Stage 5 - Matching Engine có nhiệm vụ tìm top-k clip phù hợp nhất cho từng audio segment, dựa trên `audio_segments.json`, `clip_metadata.json`, `embedding_metadata.json` và vector/index files từ Stage 4.

Stage này là nơi hệ thống quyết định đoạn lời nói nào nên được gợi ý với những clip nào. Output của stage này chưa phải timeline dựng video cuối, mà là danh sách candidate clip có score, rank, confidence và lý do đề xuất để Timeline Planner và Review UI sử dụng.

Mục tiêu chính:

* Đọc `audio_segments.json`.
* Đọc `clip_metadata.json`.
* Đọc `embedding_metadata.json`.
* Load text embeddings và visual embeddings hoặc visual index.
* So khớp từng audio segment với các clip candidate.
* Gộp score từ keyframe-level về clip-level nếu embedding theo keyframe.
* Tính `semantic_score`.
* Kết hợp thêm `visual_quality_score`, `duration_fit_score`, `continuity_score`, `diversity_score` nếu có.
* Áp dụng penalty cho clip chất lượng thấp hoặc clip bị lặp quá gần.
* Trả về top-k clip cho từng audio segment.
* Chọn clip rank 1 làm `selected_clip_id` mặc định nếu đủ điều kiện.
* Gán `confidence` cho candidate set.
* Đánh dấu fallback nếu không có clip khớp tốt.
* Xuất `matching_candidates.json` đúng Data Contract đã chốt.
* Xuất log phụ để debug scoring, ranking và fallback nếu cần.

## 2. Vị trí trong pipeline

Stage này nằm sau Embedding Indexer và trước Timeline Planner:

```text
Audio Analyzer
        |
        |-- audio_segments.json
        |
Video Analyzer
        |
        |-- clip_metadata.json
        |
Embedding Indexer
        |
        |-- embedding_metadata.json
        |-- vector/index files
        |
        v
Matching Engine
        |
        |-- matching_candidates.json
        |-- matching_engine_log.json
        |
        |--> Timeline Planner
        |--> Review UI
        |--> Evaluation
```

Matching Engine không render video và không tạo timeline. Stage này chỉ tạo danh sách candidate clip cho từng audio segment.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Matching Engine cần xử lý các phần sau:

1. Đọc `audio_segments.json`.
2. Đọc `clip_metadata.json`.
3. Đọc `embedding_metadata.json`.
4. Validate `project_id` giữa các file.
5. Load text embedding cho từng audio segment.
6. Load visual embedding hoặc visual index.
7. Map visual embedding về `clip_id`.
8. Tính semantic similarity giữa text và visual embeddings.
9. Gộp score keyframe về clip nếu cần.
10. Tính các score phụ nếu có dữ liệu.
11. Áp dụng penalty cho clip xấu hoặc clip bị lặp quá gần.
12. Sắp xếp candidate theo `final_score`.
13. Lấy top-k clip cho từng audio segment.
14. Gán `selected_clip_id`.
15. Gán `confidence`.
16. Ghi reason giải thích ngắn gọn.
17. Xuất `matching_candidates.json`.
18. Xuất `matching_engine_log.json` để debug nếu cần.

### 3.2. Stage này không làm

Matching Engine không chịu trách nhiệm cho các phần sau:

* Không chạy ASR.
* Không sửa transcript hoặc query.
* Không detect scene/shot.
* Không trích keyframe.
* Không tạo embedding mới nếu embedding thiếu.
* Không chỉnh sửa `clip_metadata.json`.
* Không tạo `timeline.json`.
* Không xử lý speed, transition hoặc crop mode.
* Không render video cuối.
* Không quyết định người dùng có chấp nhận clip hay không.

Nếu embedding thiếu hoặc clip metadata lỗi, Stage 5 chỉ báo lỗi, fallback hoặc bỏ qua candidate theo rule rõ ràng. Không tự chạy lại stage trước.

## 4. Input

### 4.1. Input chính

Matching Engine đọc:

```text
data/intermediate/audio_segments.json
data/intermediate/clip_metadata.json
data/intermediate/embedding_metadata.json
data/intermediate/embeddings/*.npy
data/intermediate/index/visual.index
```

Trong đó:

* `audio_segments.json` cung cấp audio segment, duration, query và `segment_id`.
* `clip_metadata.json` cung cấp clip candidate, duration, quality score và status.
* `embedding_metadata.json` cung cấp mapping segment/clip/keyframe với vector hoặc index.
* Vector/index files được load theo path ghi trong `embedding_metadata.json`.

### 4.2. Điều kiện input hợp lệ

Ba file chính phải thỏa:

* Parse được JSON.
* Có `schema_version`.
* Có `project_id`.
* `project_id` giữa ba file phải giống nhau.

`audio_segments.json` phải có:

* `items` không rỗng.
* Mỗi segment có `segment_id`.
* Mỗi segment có `start`, `end`, `duration`.
* Mỗi segment có `query` không rỗng.

`clip_metadata.json` phải có:

* `items` không rỗng.
* Mỗi clip có `clip_id`.
* Mỗi clip có `duration`.
* Mỗi clip có `quality_score` là number trong `[0.0, 1.0]` hoặc `null`.
* MVP nên có `status` cho mọi clip.

`embedding_metadata.json` phải có:

* `model.name`.
* `model.type`.
* `model.dimension`.
* `text_embeddings` không rỗng.
* `visual_embeddings` không rỗng.
* `embedding_id` không trùng.
* Text embedding map được về `segment_id`.
* Visual embedding map được về `clip_id` và `keyframe_id` nếu có.
* `vector_path` load được nếu khác `null`.
* Nếu dùng index, `index.path` phải load được.

### 4.3. Clip nào được matching

Trong MVP, Matching Engine nên xét clip có:

```text
status = usable
status = low_quality
```

Không nên chọn mặc định clip có:

```text
status = too_short
status = error
```

Quy tắc:

* Clip `usable`: được xếp hạng bình thường.
* Clip `low_quality`: vẫn được xếp hạng nhưng có penalty.
* Clip `too_short`: bỏ qua trong MVP hoặc chỉ dùng nếu bật fallback đặc biệt.
* Clip `error`: luôn bỏ qua.

Nếu clip thiếu `status` do dữ liệu cũ:

* Nếu clip có keyframe/embedding hợp lệ, có thể xử lý như usable tạm thời.
* Ghi warning vào `matching_engine_log.json`.
* Nên yêu cầu Stage 3 cập nhật lại để có `status` rõ ràng.

### 4.4. Cấu hình chạy module

Cấu hình dưới đây là cấu hình nội bộ của Matching Engine, không phải Data Contract bắt buộc giữa các module.

Ví dụ cấu hình:

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

Trong MVP, các giá trị đề xuất:

| Tham số | Giá trị đề xuất |
| ------- | --------------- |
| `top_k` | `5` |
| `similarity.metric` | `cosine` |
| `similarity.normalize_vectors` | `true` |
| `score_weights.semantic` | `0.60` |
| `score_weights.visual_quality` | `0.15` |
| `score_weights.duration_fit` | `0.15` |
| `score_weights.continuity` | `0.05` |
| `score_weights.diversity` | `0.05` |
| `confidence_thresholds.high` | `0.75` |
| `confidence_thresholds.medium` | `0.50` |

Ghi chú:

* Trọng số có thể điều chỉnh, nhưng tổng các weight chính nên dễ giải thích.
* `final_score` phải được clamp về `[0.0, 1.0]`.
* Nếu chưa làm được continuity hoặc diversity, có thể để các score đó `null` hoặc dùng weight `0`.
* Semantic score là lõi của MVP, không nên bỏ qua nếu đã có embedding.

## 5. Output

Stage này tạo output chính:

```text
data/intermediate/matching_candidates.json
```

Stage này có thể tạo output phụ:

```text
data/intermediate/matching_engine_log.json
```

Trong đó:

* `matching_candidates.json` là Data Contract chính cho Timeline Planner, Review UI và Evaluation.
* `matching_engine_log.json` là log phụ để debug similarity, score, rank và fallback.

Các module sau chỉ nên phụ thuộc vào `matching_candidates.json`. Log phụ không phải contract bắt buộc.

## 6. Data Contract: `matching_candidates.json`

### 6.1. Vai trò

`matching_candidates.json` lưu top-k clip phù hợp cho từng audio segment.

File này giúp các module sau biết:

* Mỗi audio segment có những clip nào được đề xuất.
* Clip nào được chọn mặc định.
* Mỗi candidate có rank và score bao nhiêu.
* Hệ thống tự tin ở mức nào.
* Có dùng fallback không.
* Vì sao clip được đề xuất.

### 6.2. Cấu trúc top-level

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "top_k": 5,
  "created_at": "2026-06-11T10:20:00Z",
  "items": []
}
```

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `schema_version` | string | Phiên bản schema |
| `project_id` | string | ID dự án đang xử lý |
| `top_k` | integer | Số candidate tối đa cho mỗi segment |
| `created_at` | string | Thời điểm tạo file |
| `items` | array[object] | Danh sách candidate set |

Quy ước:

* `schema_version` dùng `"1.0"` trong MVP.
* `project_id` phải khớp với input.
* `top_k` nên là `5` trong MVP.
* Nên có một candidate set cho mỗi audio segment.

### 6.3. Candidate set item

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `candidate_set_id` | string | ID nhóm candidate |
| `audio_segment_id` | string | Segment được matching |
| `selected_clip_id` | string/null | Clip mặc định được chọn |
| `confidence` | string | Độ tin cậy tổng quát |
| `candidates` | array[object] | Danh sách top-k clip |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `reason` | string | Lý do tổng quát |
| `fallback_used` | boolean | Có dùng fallback không |
| `notes` | string | Ghi chú |

Allowed `confidence`:

```text
high
medium
low
```

Quy tắc:

* `audio_segment_id` phải tồn tại trong `audio_segments.json`.
* `candidate_set_id` nên có dạng `candidates_a001`.
* `selected_clip_id` nên là clip rank 1 nếu có candidate đủ điều kiện.
* `selected_clip_id = null` nếu không có candidate nào dùng được.
* `candidates` có tối đa `top_k` item.

### 6.4. Candidate item

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `rank` | integer | Thứ hạng |
| `clip_id` | string | Clip candidate |
| `final_score` | number | Điểm tổng hợp |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `semantic_score` | number/null | Điểm khớp nghĩa |
| `visual_quality_score` | number/null | Điểm chất lượng hình |
| `duration_fit_score` | number/null | Điểm khớp thời lượng |
| `continuity_score` | number/null | Điểm nối cảnh |
| `diversity_score` | number/null | Điểm đa dạng |
| `repetition_penalty` | number/null | Điểm phạt lặp |
| `bad_clip_penalty` | number/null | Điểm phạt clip xấu |
| `reason` | string | Lý do đề xuất |

Quy tắc:

* `rank` bắt đầu từ `1`.
* Candidate phải được sắp xếp theo `final_score` giảm dần.
* `clip_id` phải tồn tại trong `clip_metadata.json`.
* Không nên có hai candidate cùng `clip_id` trong một candidate set.
* `final_score` phải nằm trong `[0.0, 1.0]`.
* Các score phụ nếu có cũng phải nằm trong `[0.0, 1.0]` hoặc `null`.

## 7. Quy tắc đặt ID

ID cần ngắn gọn, ổn định và dễ map giữa các file.

Với MVP, quy tắc đề xuất:

```text
candidate_set_id: candidates_a001, candidates_a002, ...
```

Quy tắc sinh `candidate_set_id`:

* Dựa trên `segment_id`.
* Với `segment_id = a001`, dùng `candidate_set_id = candidates_a001`.
* Không dùng timestamp hoặc random ID.
* Nếu chạy lại với cùng input, ID nên giữ ổn định.

## 8. Quy trình xử lý đề xuất

### 8.1. Bước 1 - Đọc input

Matching Engine đọc:

* `audio_segments.json`
* `clip_metadata.json`
* `embedding_metadata.json`

Kiểm tra:

* Ba file parse được.
* Ba file có cùng `project_id`.
* Audio segments không rỗng.
* Clip metadata không rỗng.
* Embedding metadata không rỗng.

### 8.2. Bước 2 - Load embeddings

Load text embeddings:

* Map `segment_id -> text_vector`.
* Kiểm tra vector dimension đúng với `embedding_metadata.model.dimension`.
* Nếu thiếu text embedding cho segment nào, ghi warning/error.

Load visual embeddings:

* Map `visual_embedding -> clip_id`.
* Nếu embedding theo keyframe, map thêm `keyframe_id`.
* Kiểm tra vector dimension đúng.
* Nếu dùng index, load index theo `embedding_metadata.index.path`.

Nếu Stage 4 dùng quy tắc index row `i` tương ứng `visual_embeddings[i]`, Matching Engine phải giữ đúng rule này khi đọc kết quả search.

### 8.3. Bước 3 - Lọc clip candidate hợp lệ

Tạo danh sách clip có thể matching:

```text
status = usable
status = low_quality
```

Loại khỏi matching mặc định:

```text
status = too_short
status = error
```

Nếu clip không có visual embedding hợp lệ:

* Không đưa vào candidate chính.
* Ghi warning trong log.

### 8.4. Bước 4 - Tính semantic score

Với mỗi audio segment:

1. Lấy text vector theo `segment_id`.
2. So sánh với visual vectors.
3. Tính similarity.
4. Normalize similarity về `[0.0, 1.0]` nếu cần.
5. Gộp visual embedding score về clip-level score.

Nếu dùng cosine similarity với vector đã normalize:

```text
cosine_similarity nằm trong [-1.0, 1.0]
semantic_score = (cosine_similarity + 1.0) / 2.0
```

Nếu model hoặc index đã trả score trong `[0.0, 1.0]`, có thể dùng trực tiếp nhưng cần ghi rõ trong log.

### 8.5. Bước 5 - Gộp keyframe score về clip score

Data Contract của `matching_candidates.json` trả về `clip_id`, không trả về `keyframe_id`.

Vì vậy, nếu visual embedding được tạo theo keyframe, Matching Engine phải gộp nhiều keyframe score của cùng một clip về một clip-level `semantic_score`.

Cách gộp đề xuất:

```text
semantic_score_clip = max(semantic_score_keyframes_of_clip)
```

Lý do:

* Một clip có thể chỉ cần một keyframe khớp tốt với nội dung.
* Dễ triển khai và dễ giải thích trong MVP.

Có thể thử cách khác sau:

```text
average top-2 keyframe scores
weighted average theo quality_score keyframe
```

Nhưng MVP nên dùng `max` trước để đơn giản.

### 8.6. Bước 6 - Tính duration_fit_score

`duration_fit_score` đo clip có phù hợp với thời lượng audio segment không.

Input:

* `audio_segment.duration`
* `clip.duration`

Gợi ý:

```text
ratio = clip.duration / audio_segment.duration
```

Score đề xuất:

* Gần `1.0`: clip gần bằng duration segment.
* Clip dài hơn segment một chút vẫn tốt vì Timeline Planner có thể cắt.
* Clip ngắn hơn segment quá nhiều thì điểm thấp.

Rule đơn giản cho MVP:

```text
if clip.duration >= audio_duration:
    duration_fit_score = 1.0
else:
    duration_fit_score = clip.duration / audio_duration
```

Sau đó clamp về `[0.0, 1.0]`.

Ghi chú:

* Timeline Planner mới xử lý cắt/speed cụ thể.
* Matching Engine chỉ đánh giá clip có đủ thời lượng tương đối hay không.

### 8.7. Bước 7 - Tính visual_quality_score

`visual_quality_score` lấy từ `clip_metadata.json`.

Quy tắc:

* Nếu `clip.quality_score` là number, dùng trực tiếp.
* Nếu `clip.quality_score = null`, dùng `visual_quality_score = null` hoặc fallback trung tính `0.5` trong scoring nội bộ.
* Nếu dùng fallback trung tính, cần ghi rõ trong log hoặc reason.

Trong output candidate:

* Nếu không có quality thật, có thể để `visual_quality_score = null`.
* Không tự ghi `0.5` vào output nếu đó chỉ là giá trị nội bộ để tính toán.

### 8.8. Bước 8 - Tính continuity_score

`continuity_score` đo clip có nối hợp lý với clip của segment trước không.

Trong MVP, field này optional. Có thể triển khai đơn giản:

* Tránh chọn cùng một clip liên tiếp.
* Tránh nhảy qua lại quá nhiều giữa các video nếu không cần.
* Ưu tiên clip gần nhau theo thời gian trong cùng video nếu semantic score tương đương.

Nếu chưa triển khai continuity:

* Để `continuity_score = null`.
* Weight continuity nên là `0`.

### 8.9. Bước 9 - Tính diversity_score

`diversity_score` giúp top-k không toàn là các clip quá giống nhau hoặc cùng một đoạn gần nhau.

Trong MVP, có thể triển khai đơn giản:

* Phạt clip có cùng `video_id` và timestamp quá gần với candidate rank cao hơn.
* Ưu tiên top-k có nhiều cảnh khác nhau nếu semantic score không chênh quá lớn.

Nếu chưa triển khai diversity:

* Để `diversity_score = null`.
* Weight diversity nên là `0`.

### 8.10. Bước 10 - Áp dụng penalty

Penalty không phải score tốt; penalty là điểm trừ.

Các penalty nên có:

| Penalty | Khi dùng |
| ------- | -------- |
| `bad_clip_penalty` | Clip `low_quality` hoặc quality thấp |
| `repetition_penalty` | Clip đã dùng gần đây hoặc quá giống candidate khác |

Quy tắc:

* Penalty nằm trong `[0.0, 1.0]`.
* Penalty càng cao nghĩa là bị phạt càng nhiều.
* `final_score` sau penalty vẫn phải clamp về `[0.0, 1.0]`.

Ví dụ:

```text
bad_clip_penalty = 0.10 nếu status = low_quality
repetition_penalty = 0.15 nếu clip trùng với segment liền trước
```

### 8.11. Bước 11 - Tính final_score

`final_score` là điểm tổng hợp để rank candidate.

Công thức MVP đề xuất:

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

Trong đó:

* `semantic_score` là thành phần quan trọng nhất.
* Nếu optional score chưa có, có thể dùng weight `0` hoặc giá trị effective trung tính nội bộ.
* Output field optional chưa có dữ liệu thật nên để `null`.
* Không ghi score giả vào output chỉ để đủ công thức.

### 8.12. Bước 12 - Lấy top-k

Với mỗi audio segment:

1. Tính score cho tất cả clip hợp lệ.
2. Gộp theo `clip_id`.
3. Sắp xếp theo `final_score` giảm dần.
4. Loại candidate trùng `clip_id`.
5. Lấy tối đa `top_k` clip.
6. Gán `rank` bắt đầu từ `1`.

Nếu số clip hợp lệ ít hơn `top_k`, trả về ít hơn `top_k` candidate.

Không thêm candidate giả chỉ để đủ số lượng.

### 8.13. Bước 13 - Fallback

Fallback dùng khi không có clip nào khớp đủ tốt.

Ví dụ trường hợp cần fallback:

* Semantic score quá thấp cho tất cả clip.
* Segment quá trừu tượng.
* Segment query quá mơ hồ.
* Thiếu embedding cho segment.
* Footage không có cảnh liên quan.

Fallback đề xuất:

* Chọn clip `usable` có quality cao.
* Ưu tiên clip chưa dùng gần đây.
* Ưu tiên clip có duration đủ dài.
* Đặt `fallback_used = true`.
* Đặt `confidence = low`.
* Ghi reason rõ ràng.

Nếu không có clip nào usable:

* `selected_clip_id = null`.
* `candidates = []`.
* `confidence = low`.
* `fallback_used = true`.
* Ghi lỗi/cảnh báo trong log.

### 8.14. Bước 14 - Gán confidence

Confidence dùng ba mức:

```text
high
medium
low
```

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

Có thể kết hợp thêm:

* Khoảng cách score giữa rank 1 và rank 2.
* `semantic_score` riêng.
* `needs_review` của audio segment.
* `status` của clip được chọn.

Nếu audio segment có `needs_review = true`, có thể giảm confidence một mức hoặc ghi notes, tùy rule nhóm thống nhất.

### 8.15. Bước 15 - Ghi `matching_candidates.json`

Trước khi ghi file, cần kiểm tra:

* Có đủ top-level fields.
* `top_k` là integer dương.
* Nên có candidate set cho mỗi audio segment.
* `candidate_set_id` không trùng.
* `audio_segment_id` tồn tại trong `audio_segments.json`.
* `selected_clip_id` là `null` hoặc khớp với một `candidates[].clip_id`.
* `confidence` thuộc allowed values.
* `candidates` là array.
* Candidate `rank` bắt đầu từ `1` và tăng dần.
* Candidate không trùng `clip_id` trong cùng set.
* Candidate `clip_id` tồn tại trong `clip_metadata.json`.
* `final_score` nằm trong `[0.0, 1.0]`.
* Các score phụ nếu có nằm trong `[0.0, 1.0]` hoặc `null`.

## 9. Quy tắc scoring chi tiết

### 9.1. Semantic score là lõi

Trong MVP, `semantic_score` nên là thành phần quan trọng nhất vì bài toán là dựng video theo nội dung audio.

Nếu semantic score thấp, clip không nên được chọn chỉ vì chất lượng hình cao.

### 9.2. Quality không thay thế semantic

Clip đẹp nhưng không liên quan chỉ nên đứng cao khi không có clip liên quan nào tốt hơn hoặc khi fallback.

Vì vậy, `visual_quality_score` nên hỗ trợ ranking, không chi phối hoàn toàn ranking.

### 9.3. Duration fit là hỗ trợ timeline

Clip đủ dài giúp Timeline Planner dễ cắt theo audio segment.

Tuy nhiên, Matching Engine không nên xử lý speed/cut cụ thể. Stage này chỉ đánh giá độ phù hợp thời lượng ở mức score.

### 9.4. Penalty phải giải thích được

Nếu một clip bị tụt rank vì penalty, nên có `reason` hoặc log giải thích.

Ví dụ:

```text
Khớp nghĩa tốt nhưng bị giảm điểm vì clip chất lượng thấp.
```

### 9.5. Không ghi score giả

Nếu chưa tính được score phụ:

* Output field nên là `null` hoặc bỏ qua.
* Công thức nội bộ có thể dùng giá trị trung tính, nhưng không ghi giá trị đó như score thật.

## 10. Quy tắc top-k và selected clip

### 10.1. Top-k là clip-level

`matching_candidates.json` trả về candidate theo `clip_id`.

Nếu search index trả về keyframe, Matching Engine phải gộp keyframe về clip trước khi tạo top-k.

Không xuất:

```text
rank 1: v01_c003_k01
rank 2: v01_c003_k02
```

Mà phải xuất:

```text
rank 1: v01_c003
```

### 10.2. Không trùng clip trong cùng candidate set

Một candidate set không được có cùng `clip_id` nhiều lần.

Nếu một clip có nhiều keyframe khớp tốt, dùng keyframe tốt nhất để tính score clip-level.

### 10.3. selected_clip_id

`selected_clip_id` là clip mặc định để Timeline Planner dùng.

Quy tắc:

* Nếu có candidate, mặc định chọn clip rank 1.
* Nếu tất cả candidate quá kém nhưng vẫn cần fallback, chọn fallback rank 1 và `fallback_used = true`.
* Nếu không có candidate nào, `selected_clip_id = null`.

### 10.4. top_k không bắt buộc luôn đủ số lượng

Nếu chỉ có 3 clip hợp lệ và `top_k = 5`, trả về 3 candidate.

Không tạo candidate giả để đủ 5.

## 11. Quy tắc confidence và fallback

### 11.1. Confidence không chỉ là final_score

Confidence có thể dựa trên:

* `final_score` của clip được chọn.
* `semantic_score` của clip được chọn.
* Chênh lệch giữa rank 1 và rank 2.
* Audio segment có `needs_review` không.
* Có dùng fallback không.
* Clip được chọn có `status = low_quality` không.

MVP có thể bắt đầu với threshold theo `final_score`, sau đó cải thiện sau.

### 11.2. Segment trừu tượng

Segment `abstract` thường khó matching chính xác.

Với segment trừu tượng:

* Có thể chấp nhận clip bối cảnh chung.
* Nên ghi reason rõ hơn.
* Có thể giảm confidence nếu semantic score không nổi bật.
* UI nên cho người dùng review.

### 11.3. needs_review từ Audio Analyzer

Nếu audio segment có `needs_review = true`, Matching Engine không được bỏ qua segment đó.

Nhưng có thể:

* Ghi notes trong candidate set.
* Giảm confidence một mức.
* Đưa reason nhắc rằng transcript/query cần review.

### 11.4. Fallback không phải lỗi

Fallback là hành vi bình thường khi video nguồn thiếu cảnh khớp.

Điều quan trọng là:

* Không giả vờ confidence cao.
* Ghi `fallback_used = true`.
* Ghi reason đủ rõ để UI và người dùng biết cần kiểm tra.

## 12. Output phụ: `matching_engine_log.json`

### 12.1. Vai trò

`matching_engine_log.json` là file log phụ của Stage 5, dùng để debug similarity, scoring, ranking và fallback.

File này không phải Data Contract chính giữa các module. Các module sau không nên phụ thuộc vào file này để chạy logic chính.

Nên dùng file này để ghi:

* Config top-k và scoring weights.
* Số audio segment được matching.
* Số clip candidate hợp lệ.
* Segment nào thiếu embedding.
* Clip/keyframe nào thiếu embedding.
* Số fallback được dùng.
* Segment nào confidence thấp.
* Thống kê score trung bình.
* Thời gian chạy module nếu cần.

### 12.2. Cấu trúc đề xuất

Đây là cấu trúc đề xuất, không bắt buộc phải xem là schema liên module:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "created_at": "2026-06-11T10:20:00Z",
  "config": {
    "top_k": 5,
    "similarity_metric": "cosine",
    "score_weights": {
      "semantic": 0.60,
      "visual_quality": 0.15,
      "duration_fit": 0.15,
      "continuity": 0.05,
      "diversity": 0.05
    }
  },
  "summary": {
    "segment_count": 12,
    "matched_segment_count": 12,
    "fallback_count": 2,
    "low_confidence_count": 3,
    "candidate_clip_count": 28
  },
  "warnings": [],
  "errors": []
}
```

### 12.3. Nguyên tắc sử dụng

`matching_candidates.json` là nguồn dữ liệu chính cho các module sau. `matching_engine_log.json` chỉ dùng để:

* Debug vì sao clip được chọn.
* Debug vì sao fallback được dùng.
* Kiểm tra score và rank.
* Hỗ trợ leader review chất lượng stage.

Nếu `matching_candidates.json` và `matching_engine_log.json` có thông tin mâu thuẫn, các module pipeline phải ưu tiên `matching_candidates.json`.

## 13. Ví dụ `matching_candidates.json`

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
        },
        {
          "rank": 2,
          "clip_id": "v01_c004",
          "final_score": 0.71,
          "semantic_score": 0.79,
          "visual_quality_score": 0.74,
          "duration_fit_score": 0.90,
          "continuity_score": 0.60,
          "diversity_score": 0.70,
          "repetition_penalty": 0.0,
          "bad_clip_penalty": 0.0,
          "reason": "Khớp nội dung khá tốt và đủ thời lượng."
        }
      ]
    }
  ]
}
```

## 14. Quan hệ với các module khác

### 14.1. Audio Analyzer

Matching Engine đọc:

```text
audio_segments.json
items[*].segment_id
items[*].duration
items[*].segment_type
items[*].needs_review
```

Matching Engine không sửa transcript, query hoặc segment boundary.

### 14.2. Video Analyzer

Matching Engine đọc:

```text
clip_metadata.json
items[*].clip_id
items[*].duration
items[*].quality_score
items[*].status
```

Matching Engine không sửa clip metadata và không trích lại keyframe.

### 14.3. Embedding Indexer

Matching Engine đọc:

```text
embedding_metadata.json
text_embeddings
visual_embeddings
index
vector/index files
```

Nếu index result id map theo thứ tự `visual_embeddings`, Matching Engine phải dùng đúng thứ tự đó.

### 14.4. Timeline Planner

Timeline Planner đọc:

```text
matching_candidates.json
items[*].audio_segment_id
items[*].selected_clip_id
items[*].confidence
items[*].candidates
```

Timeline Planner dùng rank 1 hoặc `selected_clip_id` để tạo timeline ban đầu.

### 14.5. Review UI

Review UI đọc:

```text
matching_candidates.json
clip_metadata.json
audio_segments.json
```

UI dùng `candidates` để hiển thị top-k clip thay thế cho từng audio segment.

### 14.6. Evaluation

Evaluation có thể dùng `matching_candidates.json` để:

* Tính average semantic score.
* Tính low-confidence rate.
* Tính fallback rate.
* Tính repetition rate.
* Ghi nhận số lượng candidate mỗi segment.

## 15. Điều kiện handoff sang stage sau

Stage 5 được phép bàn giao cho Timeline Planner và Review UI khi thỏa các điều kiện sau:

```text
matching_candidates.json parse được
matching_candidates.json có đủ top-level required fields
top_k là integer dương
items không rỗng
nên có candidate set cho mỗi audio segment
candidate_set_id không trùng
audio_segment_id map đúng segment
confidence thuộc high/medium/low
selected_clip_id là null hoặc khớp với một candidates[].clip_id
candidate rank hợp lệ
candidate clip_id không trùng trong cùng set
candidate clip_id map đúng clip
final_score nằm trong [0.0, 1.0]
```

Nếu một số segment có `confidence = low`, pipeline vẫn được chạy tiếp. Đây là tín hiệu để Review UI highlight và để Timeline Planner đánh dấu `needs_review`.

Nếu một segment không có candidate nào:

* Candidate set vẫn nên tồn tại.
* `selected_clip_id = null`.
* `candidates = []`.
* `confidence = low`.
* `fallback_used = true`.
* Timeline Planner cần xử lý fallback tiếp hoặc báo cần người dùng can thiệp.

## 16. Ràng buộc kỹ thuật

### 16.1. Không tạo timeline ở Stage 5

Matching Engine không được ghi `timeline.json`.

Stage này chỉ tạo `matching_candidates.json`.

### 16.2. Không trả về keyframe làm candidate

Candidate item chỉ có `clip_id`, không có `keyframe_id`.

Nếu semantic score tính từ keyframe, phải gộp về clip-level trước khi xuất output.

### 16.3. Không bịa score

Nếu score phụ chưa tính được, để `null` hoặc bỏ field optional.

Không ghi score giả vào output chỉ để đủ field.

### 16.4. Không chọn clip lỗi

Không chọn clip `error` làm candidate.

Không chọn clip `too_short` làm candidate mặc định trong MVP.

### 16.5. Không phụ thuộc vào log phụ

Các module sau không được phụ thuộc vào `matching_engine_log.json` để chạy logic chính.

Nếu thông tin cần thiết cho Timeline Planner hoặc Review UI, thông tin đó phải nằm trong `matching_candidates.json`.

## 17. Re-run behavior

Matching Engine cần có quy tắc rõ ràng khi chạy lại với cùng `project_id`.

### 17.1. Mục tiêu

Chạy lại module không được làm `candidate_set_id` thay đổi bất ngờ nếu input và config không đổi.

Yêu cầu:

* Nếu input và config không đổi, candidate set ID giữ ổn định.
* Rank có thể thay đổi nếu score formula hoặc embedding thay đổi.
* Không ghi đè output cũ nếu người chạy chưa cho phép.

### 17.2. Quy tắc đề xuất

Nếu chạy lại với cùng `project_id`:

* Nếu có flag `--overwrite`, module được phép ghi đè `matching_candidates.json` và `matching_engine_log.json`.
* Nếu không có `--overwrite`, module nên báo output đã tồn tại và dừng an toàn, hoặc yêu cầu người dùng chọn output/run khác.
* Nếu đã có `timeline.json` dựa trên matching cũ, nên chạy lại Timeline Planner sau khi Stage 5 chạy lại.

## 18. Gợi ý cấu trúc code

Đây là gợi ý tổ chức module, không bắt buộc nếu nhóm đã có style code riêng.

```text
matching_engine/
│
├── __init__.py
├── main.py
├── config.py
├── embedding_loader.py
├── similarity_searcher.py
├── score_calculator.py
├── ranker.py
├── fallback_handler.py
├── matching_candidates_writer.py
└── validator.py
```

Vai trò từng file:

| File | Vai trò |
| ---- | ------- |
| `main.py` | Entry point chạy module |
| `config.py` | Đọc và validate cấu hình chạy module |
| `embedding_loader.py` | Load text/visual vectors hoặc index |
| `similarity_searcher.py` | Search visual embeddings theo text embedding |
| `score_calculator.py` | Tính semantic, duration, quality, penalty, final score |
| `ranker.py` | Gộp keyframe về clip, sort và lấy top-k |
| `fallback_handler.py` | Xử lý fallback khi không có match tốt |
| `matching_candidates_writer.py` | Tạo và ghi `matching_candidates.json` |
| `validator.py` | Kiểm tra input và output theo quy tắc đã chốt |

Nếu nhóm dùng ngôn ngữ hoặc framework khác, vẫn cần giữ nguyên trách nhiệm logic tương đương.

## 19. Gợi ý CLI

CLI tối thiểu:

```text
python -m matching_engine.main \
  --audio-segments data/intermediate/audio_segments.json \
  --clip-metadata data/intermediate/clip_metadata.json \
  --embedding-metadata data/intermediate/embedding_metadata.json \
  --output-dir data/intermediate \
  --top-k 5
```

Output mong đợi:

```text
data/intermediate/matching_candidates.json
data/intermediate/matching_engine_log.json
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

## 20. Test cases bắt buộc

### 20.1. Test input hợp lệ

Input:

```text
audio_segments.json
clip_metadata.json
embedding_metadata.json
vector/index files
```

Kỳ vọng:

* Tạo được `matching_candidates.json`.
* Có candidate set cho mỗi audio segment.
* Top-level có đúng `project_id`.
* `top_k` đúng config.

### 20.2. Test project_id không khớp

Kỳ vọng:

* Module dừng.
* Không tạo metadata giả.
* Báo lỗi rõ ràng.

### 20.3. Test gộp keyframe về clip

Kỳ vọng:

* Nếu nhiều keyframe của cùng một clip match tốt, output vẫn chỉ có một candidate với `clip_id`.
* Không có candidate trùng `clip_id` trong cùng candidate set.

### 20.4. Test rank và score

Kỳ vọng:

* Candidate được sort theo `final_score` giảm dần.
* `rank` bắt đầu từ `1`.
* `final_score` nằm trong `[0.0, 1.0]`.
* Score phụ nếu có nằm trong `[0.0, 1.0]` hoặc `null`.

### 20.5. Test clip low_quality

Kỳ vọng:

* Clip `low_quality` vẫn có thể xuất hiện trong candidates.
* Clip này có `bad_clip_penalty` hoặc reason/log giải thích.

### 20.6. Test clip too_short/error

Kỳ vọng:

* Clip `too_short` và `error` không được chọn mặc định trong MVP.
* Clip `error` không xuất hiện trong candidates.

### 20.7. Test fallback

Kỳ vọng:

* Khi semantic score rất thấp, candidate set có `fallback_used = true`.
* `confidence = low`.
* Reason giải thích rõ fallback.

### 20.8. Test không có candidate

Kỳ vọng:

* Candidate set vẫn tồn tại cho segment.
* `selected_clip_id = null`.
* `candidates = []`.
* `confidence = low`.
* `fallback_used = true`.

### 20.9. Test selected_clip_id

Kỳ vọng:

* Nếu có candidate, `selected_clip_id` là clip rank 1.
* Nếu không có candidate, `selected_clip_id = null`.
* `selected_clip_id` nếu khác null phải khớp với một `candidates[].clip_id`.

### 20.10. Test confidence

Kỳ vọng:

* `confidence` thuộc `high`, `medium`, `low`.
* Fallback luôn là `low`.
* Segment có score thấp không bị gán `high`.

### 20.11. Test top_k

Kỳ vọng:

* Số candidate trong mỗi set không vượt quá `top_k`.
* Nếu số clip hợp lệ ít hơn `top_k`, trả về ít hơn.
* Không tạo candidate giả để đủ top-k.

### 20.12. Test chạy lại module

Kỳ vọng:

* Nếu chạy lại không có `--overwrite` và output đã tồn tại, module dừng an toàn hoặc yêu cầu chọn output khác.
* Nếu chạy lại có `--overwrite`, module được phép ghi đè output cũ.
* Nếu input và config không đổi, `candidate_set_id` giữ ổn định.

## 21. Tiêu chí nghiệm thu

Module Matching Engine được xem là đạt yêu cầu MVP khi:

1. Đọc được `audio_segments.json`.
2. Đọc được `clip_metadata.json`.
3. Đọc được `embedding_metadata.json`.
4. Validate được `project_id` khớp giữa các file.
5. Load được text embeddings.
6. Load được visual embeddings hoặc visual index.
7. Map được visual embedding/index result về `clip_id`.
8. Tạo được candidate set cho mỗi audio segment.
9. Gộp được keyframe score về clip-level score.
10. Không có candidate trùng `clip_id` trong cùng set.
11. Tính được `semantic_score` cho candidate hợp lệ.
12. Tính được `final_score` trong `[0.0, 1.0]`.
13. Candidate được sort đúng theo rank.
14. Mỗi candidate có `rank`, `clip_id`, `final_score`.
15. `selected_clip_id` đúng rule.
16. `confidence` thuộc `high`, `medium`, `low`.
17. Clip `low_quality` được xử lý bằng penalty hoặc reason rõ ràng.
18. Clip `error` không xuất hiện trong candidates.
19. Clip `too_short` không được chọn mặc định trong MVP.
20. Fallback được đánh dấu rõ bằng `fallback_used`.
21. Tạo `matching_candidates.json` đúng schema đã chốt.
22. Tạo `matching_engine_log.json` để hỗ trợ debug.
23. Timeline Planner có thể dùng `selected_clip_id` để tạo timeline.
24. Review UI có thể hiển thị top-k clip thay thế.
25. Có quy tắc rõ ràng khi chạy lại cùng `project_id`.

## 22. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 5 cần tự kiểm tra:

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc được audio_segments.json
[ ] Đọc được clip_metadata.json
[ ] Đọc được embedding_metadata.json
[ ] Kiểm tra project_id các file khớp nhau
[ ] Load được text embeddings
[ ] Load được visual embeddings hoặc index
[ ] Map được index result về visual_embeddings
[ ] Map được visual embedding về clip_id
[ ] Không xuất keyframe_id làm candidate
[ ] Gộp keyframe score về clip-level
[ ] Tính được semantic_score
[ ] Tính được duration_fit_score nếu có
[ ] Dùng quality_score từ clip_metadata nếu có
[ ] Áp dụng penalty cho low_quality nếu cần
[ ] Không đưa clip error vào candidates
[ ] Không chọn clip too_short mặc định trong MVP
[ ] Tính final_score trong [0.0, 1.0]
[ ] Sort candidate theo final_score giảm dần
[ ] Rank bắt đầu từ 1
[ ] Không có clip_id trùng trong cùng candidate set
[ ] Sinh candidate_set_id dạng candidates_a001
[ ] Gán selected_clip_id đúng rule
[ ] Gán confidence high/medium/low đúng rule
[ ] Đánh dấu fallback_used khi dùng fallback
[ ] Ghi reason đủ hiểu cho candidate hoặc candidate set
[ ] Ghi đúng matching_candidates.json
[ ] Ghi được matching_engine_log.json
[ ] Không hard-code path cá nhân
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương khi chạy lại
[ ] Có test với dữ liệu mẫu nhỏ
[ ] Output có thể đưa cho Timeline Planner và Review UI chạy tiếp
```

## 23. Ghi chú triển khai MVP

Trong MVP, không cần làm Matching Engine quá phức tạp. Ưu tiên quan trọng nhất là tạo được top-k clip hợp lệ cho mỗi audio segment, có score rõ ràng và có fallback minh bạch.

Thứ tự ưu tiên nên là:

1. Đọc đúng input và validate mapping.
2. Load text/visual embedding ổn định.
3. Tính semantic similarity.
4. Gộp keyframe score về clip-level.
5. Kết hợp quality và duration ở mức đơn giản.
6. Lấy top-k clip không trùng.
7. Gán selected clip và confidence.
8. Ghi `matching_candidates.json` đúng schema.
9. Ghi log dễ debug.
10. Tối ưu continuity, diversity và penalty sau.

Nếu có tranh luận giữa việc scoring thật tinh vi và việc đảm bảo pipeline end-to-end chạy được, MVP nên ưu tiên công thức đơn giản, giải thích được và dễ tích hợp trước. Scoring có thể cải thiện dần miễn là `matching_candidates.json` không đổi schema.
