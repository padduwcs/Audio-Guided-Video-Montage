# 04. Stage 2 — Audio Analysis

| Module | `audio_analyzer/` |
| Core docs | [00](00_project_scope.md) · [01](01_system_architecture.md) · [02](02_data_contract.md) |
| Schema/Sample | [docs/schemas/audio_segments.schema.md](../schemas/audio_segments.schema.md) · [docs/samples/audio_segments_sample.json](../samples/audio_segments_sample.json) |

## 1. Mục tiêu stage

Stage 2 — Audio Analysis phân tích audio thuyết minh đã chuẩn hóa từ Stage 1, chuyển audio thành transcript có timestamp, chia transcript thành các audio segment có ý nghĩa và tạo `audio_segments.json` cho các stage phía sau.

Stage này là nhánh phân tích audio chính của hệ thống. Output quyết định hệ thống hiểu audio đang nói gì, nói ở thời điểm nào và nên dùng câu query nào để tìm clip hình ảnh tương ứng.

Mục tiêu chính:

* Đọc audio thuyết minh từ `media_metadata.json`.
* Chạy ASR để tạo transcript có timestamp.
* Chia transcript thành các segment có ý nghĩa để dựng video.
* Sinh `segment_id` ổn định cho từng audio segment.
* Sinh `query` phục vụ matching với video.
* Gán `segment_type` nếu xác định được.
* Gán `asr_confidence` nếu ASR cung cấp độ tin cậy.
* Đánh dấu `needs_review` cho những đoạn transcript hoặc segment có rủi ro.
* Xuất `audio_segments.json` đúng Data Contract hiện hành.
* Xuất log phụ để debug quá trình ASR và segmentation nếu cần.

## 2. Vị trí pipeline

**Chuỗi stage:** `① Input → ② Audio ∥ ③ Video → ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧ Render`

```text
  ① Input ──► ② Audio ─┐
                        ├──► ④ → ⑤ → ⑥ → ⑦ → ⑧
            ③ Video ───┘
                 ▲
            Stage này (song song ③)

  ── Chi tiết Stage ② ─────────────────────────────────────

        ┌── media_metadata.json
        │   audio.normalized_path
        ▼
┌─────────────────────────────┐
│  ② Audio Analyzer           │  ◄── bạn ở đây
└─────────────┬───────────────┘
              │ ghi
              ├─ audio_segments.json
              └─ audio_analysis_log.json
              │
              ▼
    ④ Embedding → ⑤ Matching → ⑥ Timeline → ⑦ Review → ⑧
```

| | |
|---|---|
| **Đọc (IN)** | `media_metadata.json`, file audio đã chuẩn hóa (`audio.normalized_path`) |
| **Ghi (OUT)** | `audio_segments.json`, `audio_analysis_log.json` |
| **Downstream** | Stage ④ (embedding text), ⑤, ⑥, ⑦ đọc `audio_segments.json` |

Không đọc video nguồn — chỉ phụ thuộc output Stage ①. Chi tiết: [01 §4.2](01_system_architecture.md#42-audio-analyzer).

## 3. Trách nhiệm

### 3.1. Làm

1. Đọc `media_metadata.json`.
2. Kiểm tra audio có `status = ready` hoặc `status = warning`.
3. Lấy `audio.normalized_path`.
4. Kiểm tra file audio normalized tồn tại và đọc được.
5. Chạy ASR để tạo transcript có timestamp.
6. Làm sạch transcript ở mức nhẹ nếu cần.
7. Chia transcript thành các segment có ý nghĩa.
8. Tính `start`, `end`, `duration` cho từng segment.
9. Sinh `segment_id` theo quy tắc ổn định.
10. Sinh `query` từ nội dung segment.
11. Trích `keywords` nếu có thể.
12. Tạo `translated_query` nếu pipeline matching cần query tiếng Anh.
13. Gán `segment_type` nếu xác định được.
14. Gán `asr_confidence` nếu ASR có trả về.
15. Gán `needs_review` cho segment cần người dùng kiểm tra.
16. Xuất `audio_segments.json`.
17. Xuất `audio_analysis_log.json` để debug nếu cần.

### 3.2. Không làm

* Không chuẩn hóa audio hoặc chỉnh sửa trực tiếp file audio.
* Không detect scene/shot, trích keyframe, tính embedding.
* Không matching audio segment với clip, không chọn clip cho timeline.
* Không tạo `timeline.json`, không render video cuối.

Sửa transcript không thuộc Review UI trong MVP. Nếu có transcript correction, chạy lại Audio Analyzer theo §7.13; các module downstream đọc `audio_segments.json` mới.

## 4. Input cần đọc

### 4.1. Files

| File | Nguồn | Mục đích |
| ---- | ----- | -------- |
| `data/intermediate/media_metadata.json` | Stage 1 | Metadata + `audio.normalized_path` |
| Audio normalized | `media_metadata.json → audio.normalized_path` | Input ASR (ví dụ: `data/normalized/voiceover.wav`) |

Không hard-code đường dẫn audio trong module. Quy ước path: [02 §2.6](02_data_contract.md#26-path).

### 4.2. Fail-fast

`media_metadata.json` phải thỏa:

* Parse được JSON; có `schema_version`, `project_id`, object `audio`.
* `audio.audio_id`, `audio.normalized_path` tồn tại; `audio.duration > 0`.
* `audio.status` là `ready` hoặc `warning`.

**Dừng ngay** nếu:

* Không có object `audio`.
* `audio.status = error`.
* File trong `audio.normalized_path` không tồn tại hoặc không đọc được.
* Duration audio bằng `0` hoặc không xác định được.

Audio Analyzer **được phép** chạy với `status = warning` — theo Stage 1, `ready` và `warning` đều usable.

### 4.3. Config nội bộ

Cấu hình module, không phải Data Contract giữa các stage:

```json
{
  "project_id": "demo_01",
  "media_metadata_path": "data/intermediate/media_metadata.json",
  "output_dir": "data/intermediate",
  "language": "vi",
  "asr": {
    "provider": "whisper",
    "model": "base",
    "word_timestamps": true
  },
  "segmentation": {
    "min_segment_duration": 2.0,
    "max_segment_duration": 8.0,
    "merge_short_segments": true,
    "split_long_segments": true
  },
  "query": {
    "generate_keywords": true,
    "generate_translated_query": true
  },
  "review": {
    "low_asr_confidence_threshold": 0.65
  },
  "manual_correction": {
    "enabled": false,
    "correction_path": null
  }
}
```

| Tham số | Giá trị đề xuất MVP |
| ------- | ------------------- |
| `language` | `vi` |
| `word_timestamps` | `true` nếu model hỗ trợ |
| `min_segment_duration` | `2.0` giây |
| `max_segment_duration` | `8.0` giây |
| `merge_short_segments` / `split_long_segments` | `true` |
| `generate_keywords` | `true` |
| `generate_translated_query` | `true` nếu embedding/matching cần tiếng Anh |
| `low_asr_confidence_threshold` | `0.65` |
| `manual_correction.enabled` | `false` trong MVP tự động |

Ghi chú: không bắt buộc dùng đúng model ASR trong ví dụ; nếu ASR không hỗ trợ word-level timestamp, dùng sentence/chunk-level; nếu không trả confidence, dùng `asr_confidence = null`; nếu chưa có `translated_query`, để `null` hoặc bỏ field.

## 5. Output cần tạo

| Output | Path | Contract? |
| ------ | ---- | --------- |
| Audio segments | `data/intermediate/audio_segments.json` | **Có** — stage chính |
| Analysis log | `data/intermediate/audio_analysis_log.json` | Không — debug only |

Các module sau chỉ nên phụ thuộc vào `audio_segments.json`. Log phụ không phải contract bắt buộc; nếu mâu thuẫn, ưu tiên `audio_segments.json`.

## 6. Contract fields stage trực tiếp dùng

### 6.1. Đọc từ `media_metadata.json`

→ [02 §4](02_data_contract.md#4-media_metadatajson) · schema: [media_metadata.schema.md](../schemas/media_metadata.schema.md) · sample: [media_metadata_sample.json](../samples/media_metadata_sample.json)

| Field đọc | Quy tắc stage |
| --------- | ------------- |
| `project_id` | Copy sang `audio_segments.json` |
| `audio.audio_id` | Copy sang `audio_segments.json` |
| `audio.normalized_path` | Input ASR; không tự tìm raw |
| `audio.duration` | Validate timestamp segment; probe thực tế so khớp metadata |
| `audio.status` | Chỉ chạy nếu `ready` hoặc `warning` |
| `audio.sample_rate`, `audio.channels` | Ghi log nếu cần |

### 6.2. Ghi `audio_segments.json`

→ [02 §5](02_data_contract.md#5-audio_segmentsjson) · schema: [audio_segments.schema.md](../schemas/audio_segments.schema.md) · sample: [audio_segments_sample.json](../samples/audio_segments_sample.json)

**Top-level ghi:** `schema_version`, `project_id`, `audio_id`, `language`, `created_at`, `items`.

**Segment item — quy tắc stage (ngoài schema chung):**

| Field | Quy tắc stage |
| ----- | ------------- |
| `segment_id` | `a001`, `a002`, … — padding 3 chữ số; ổn định khi input + rule segmentation không đổi |
| `start`, `end`, `duration` | Giây; không overlap; sắp xếp tăng dần theo `start`; xem [02 §2.2](02_data_contract.md#22-đơn-vị-thời-gian) |
| `text` | Transcript gốc đã làm sạch nhẹ — không phải bản tóm tắt |
| `query` | Required, không rỗng; rút gọn từ transcript, không thêm thông tin ngoài audio |
| `asr_confidence` | `0.0`–`1.0` hoặc `null` — không bịa nếu ASR không trả về |
| `keywords` | Optional; địa điểm, đối tượng, hành động chính |
| `translated_query` | Optional; tiếng Anh bám sát `query`, không thêm ý mới |
| `segment_type` | Optional; allowed: `description`, `action`, `transition`, `abstract`, `unknown` |
| `needs_review` | Optional nhưng nên có trong MVP |

**MVP:** `items` phải có ít nhất một segment nếu ASR thành công và audio có lời nói; `language = "vi"` nếu audio tiếng Việt.

## 7. Quy trình xử lý riêng

### 7.1. Bước 1 — Đọc metadata

Đọc `media_metadata.json`, lấy `project_id`, `audio.audio_id`, `audio.normalized_path`, `audio.duration`, `audio.status`, `audio.sample_rate`, `audio.channels`.

Nếu `audio.status = warning`, vẫn chạy tiếp nhưng ghi warning trong `audio_analysis_log.json`.

### 7.2. Bước 2 — Validate audio file

Kiểm tra file tồn tại, đọc được, có stream hợp lệ, duration thực tế gần metadata:

```text
Lệch <= 0.1s: chấp nhận
Lệch > 0.1s và <= 1.0s: warning
Lệch > 1.0s: cần xem lại, có thể dừng nếu ảnh hưởng timestamp
```

### 7.3. Bước 3 — Chạy ASR

Chạy ASR trên file normalized. Output nội bộ tối thiểu: text, timestamp (word/sentence/chunk), confidence nếu có.

Yêu cầu:

* Không thay đổi audio; không cắt silence trước ASR nếu làm lệch timestamp.
* Timestamp phải map về audio normalized gốc (kể cả khi dùng bản denoise tạm).
* Nếu ASR trả chunk dài, bước segmentation chia nhỏ hợp lý hơn.

### 7.4. Bước 4 — Làm sạch transcript nhẹ

**Được phép:** chuẩn hóa khoảng trắng, bỏ ký tự lặp, chuẩn hóa dấu câu, sửa hoa/thường không đổi nghĩa.

**Không nên:** viết lại nội dung, xóa tên riêng/địa danh, dịch thay `text` gốc, thêm thông tin không có trong audio.

### 7.5. Bước 5 — Chia audio segment

Mục tiêu: tạo đoạn đủ ý nghĩa để chọn hình — không cắt máy móc theo từng câu.

Segment tốt: ý hoàn chỉnh tương đối; có thể dùng matching; không quá ngắn (clip giật) hoặc quá dài (một clip khó minh họa); bám nhịp ngắt tự nhiên voice-over.

```text
min_segment_duration: 2.0s
max_segment_duration: 8.0s
```

Quy tắc:

* Segment < `2.0s` → gộp với segment trước/sau nếu hợp nghĩa.
* Segment > `8.0s` → tách tại điểm ngắt tự nhiên (dấu câu, khoảng dừng, chuyển ý).
* Không tách giữa cụm danh từ quan trọng hoặc hành động + đối tượng chính.

Ví dụ tốt:

```text
"Đây là khu vực cổng chính của khu tham quan. Sau đó, đoàn di chuyển vào khu trưng bày."
→ a001: Đây là khu vực cổng chính của khu tham quan.
→ a002: Sau đó, đoàn di chuyển vào khu trưng bày.
```

Ví dụ không tốt: tách thành `a001: "Đây là"`, `a002: "khu vực"`, `a003: "cổng chính"`.

**Segment quá dài** — không nên gộp nhiều ý:

```text
a001: "Đây là khu vực cổng chính... Sau đó đoàn di chuyển... Bên trong có rất nhiều hiện vật..."
```

**Ưu tiên ý nghĩa:** một câu dài có thể tách nhiều segment; nhiều câu ngắn cùng cảnh có thể gộp.

**Không làm lệch timestamp khi gộp/tách:**

* `start` = mốc lời nói đầu segment; `end` = mốc lời nói cuối.
* Không tự tạo timestamp không có cơ sở; nếu ước lượng do ASR thiếu chi tiết, ghi trong log.

### 7.6. Bước 6 — Xử lý khoảng lặng

MVP: không tạo segment riêng cho mọi silence ngắn.

* Silence ngắn giữa hai câu → gộp vào segment trước/sau.
* Không tạo segment rỗng chỉ vì silence.
* Silence dài có ý chuyển đoạn → có thể tạo segment `transition` với `text` dạng `"Khoảng nghỉ chuyển đoạn."` (`text` required, không để rỗng).
* Nếu không chắc → gộp silence vào segment gần nhất.

### 7.7. Bước 7 — Sinh query

Query dùng cho Matching Engine / Embedding Indexer.

Query tốt: ngắn hơn transcript; giữ danh từ, địa điểm, đối tượng, hành động; bỏ từ đệm; không thêm thông tin ngoài transcript; không quá chung.

```text
text:  "Đây là khu vực cổng chính của khu tham quan."
query: "khu vực cổng chính khu tham quan"

text:  "Sau đó, đoàn di chuyển vào khu trưng bày."
query: "đoàn di chuyển vào khu trưng bày"

text:  "Chuyến đi này để lại rất nhiều kỷ niệm đáng nhớ."
query: "kỷ niệm đáng nhớ chuyến đi"
segment_type: "abstract"
```

**Query trừu tượng:** giữ ý chính trong transcript; không bịa địa điểm/cảm xúc/hành động cụ thể. Nếu query quá mơ hồ → `needs_review = true`; Matching Engine có thể dùng clip fallback (cảnh tổng, không khí chung).

**Query yếu:** nếu không sinh được query tốt, dùng text đã làm sạch làm query + `needs_review = true` + ghi `notes` nếu cần.

**Ví dụ query sai:**

```text
text:  "Mọi người tiếp tục tham quan."
query: "mọi người tham quan khu trưng bày lịch sử ở tầng hai"  ← không được thêm thông tin
```

### 7.8. Bước 8 — Trích keywords

Optional nhưng nên có. Gồm: địa điểm, đối tượng, hành động, món ăn/vật thể/khu vực/sự kiện. Ví dụ: `["cổng chính", "khu tham quan"]`. Không đưa quá nhiều từ không quan trọng.

### 7.9. Bước 9 — Translated query

Optional. Tạo khi embedding/matching model thiên về tiếng Anh. `query` giữ tiếng Việt; `translated_query` là bản dịch bám sát `query`, không thêm ý mới. Chưa có module dịch ổn định → `null` hoặc bỏ field.

### 7.10. Bước 10 — Gán segment_type

| `segment_type` | Khi dùng |
| ------------ | -------- |
| `description` | Mô tả địa điểm, vật thể, bối cảnh, con người |
| `action` | Hành động, quá trình, thao tác |
| `transition` | Chuyển ý, di chuyển, chuyển cảnh, khoảng nghỉ |
| `abstract` | Cảm xúc, tổng kết, nhận xét chung, ý trừu tượng |
| `unknown` | Không xác định được |

### 7.11. Bước 11 — Gán needs_review

Đặt `needs_review = true` nếu:

* `asr_confidence` < ngưỡng (`0.65`).
* ASR không chắc tên riêng, địa danh, thuật ngữ.
* Text quá ngắn/khó hiểu; query quá chung.
* Segment quá dài/ngắn nhưng không xử lý tốt được.
* `segment_type = unknown`.
* `translated_query` không tạo được trong khi pipeline yêu cầu.
* Timestamp có khả năng lệch; segment `abstract`.

`needs_review = false` khi transcript rõ, timestamp hợp lý, query đủ thông tin, duration hợp lý.

`asr_confidence = null` không bắt buộc `needs_review = true`, nhưng nên dùng rule khác phát hiện rủi ro.

### 7.12. Bước 12 — Ghi output

Trước khi ghi `audio_segments.json`: validate top-level fields; `items` không rỗng nếu có lời nói; mỗi item đủ required fields; `segment_id` không trùng; timestamp hợp lệ, không overlap; `query` không rỗng; `asr_confidence` trong `[0.0, 1.0]` hoặc `null`; `segment_type` thuộc allowed values nếu có.

**Log phụ** (`audio_analysis_log.json`): ASR provider/model, audio path, duration metadata vs probed, raw ASR chunks, số segment, merge/split, segment `needs_review`, warnings/errors, thời gian chạy. Cấu trúc đề xuất — không phải inter-module schema.

### 7.13. Bước tùy chọn — Transcript đã sửa

Thiết kế module không khóa cứng một lần ASR. Nếu có transcript correction:

* Dùng transcript đã sửa tạo lại `audio_segments.json`.
* Chỉ sửa text, không đổi timestamp → giữ `segment_id`.
* Sửa làm thay đổi cách chia segment → tạo lại `segment_id` theo thứ tự mới.
* Sửa timestamp → validate lại toàn bộ `start`, `end`, `duration`.
* Ghi rõ trong log rằng output dùng transcript correction.

File correction nội bộ (không phải contract MVP). Ví dụ:

```json
{
  "segment_id": "a003",
  "corrected_text": "Khach tham quan di chuyen sang khu trai nghiem tiep theo.",
  "corrected_query": "khach tham quan di chuyen khu trai nghiem"
}
```

Sau khi áp dụng correction, chạy lại Stage 2 rồi pipeline từ Embedding Indexer trở đi (xem [`12_integration_plan.md`](12_integration_plan.md) §12.2).

## 8. Error / fallback / re-run behavior

### 8.1. Lỗi chặn pipeline

| Tình huống | Hành vi |
| ---------- | ------- |
| `audio.status = error` | Dừng; không tạo `audio_segments.json` giả |
| File audio không tồn tại/không đọc được | Dừng; báo lỗi rõ |
| ASR không nhận lời nói nào | Dừng hoặc báo lỗi; không tạo metadata giả; pipeline không chạy tiếp |

### 8.2. Cảnh báo không chặn

| Tình huống | Hành vi |
| ---------- | ------- |
| `audio.status = warning` | Chạy tiếp; ghi warning trong log |
| Một số segment `needs_review = true` | Pipeline chạy tiếp — cảnh báo cho UI |
| Duration metadata lệch nhẹ (≤ 1.0s) | Warning; tiếp tục nếu timestamp vẫn hợp lý |

### 8.3. Ràng buộc stage

* Không thay đổi file audio normalized (không cắt silence, đổi speed, dịch timestamp theo cảm tính).
* Không bịa `asr_confidence` — không có data → `null`, không đặt `1.0` vì transcript "có vẻ đúng".
* Không bịa query — chỉ rút gọn/diễn đạt lại từ transcript.
* Các module sau không phụ thuộc `audio_analysis_log.json`.

Quy ước thời gian, score, ID, path chung: [02 §2](02_data_contract.md#2-quy-ước-chung).

### 8.4. Re-run

* Cùng `project_id` + input/rule segmentation không đổi → `segment_id` và thứ tự segment nên ổn định.
* Đổi ASR model hoặc segmentation rule → boundary có thể thay đổi; ghi trong log.
* Không `--overwrite` → báo output đã tồn tại, dừng an toàn.
* Có `--overwrite` → ghi đè `audio_segments.json` và log.
* Nếu đã có `matching_candidates.json` hoặc `timeline.json` từ output cũ → chạy lại stage sau để tránh lệch `segment_id`/timestamp/query.

## 9. Handoff condition

Stage 2 bàn giao `audio_segments.json` cho Embedding Indexer khi:

```text
audio_segments.json parse được
có đủ top-level required fields
items không rỗng (nếu audio có lời nói)
mỗi item có đủ required fields
segment_id không trùng
timestamp hợp lệ, không overlap, sắp xếp tăng dần
query không rỗng
asr_confidence ∈ [0.0, 1.0] hoặc null
```

Consumer tiếp theo: Embedding Indexer (`query`, `translated_query`); Matching Engine (`segment_id`, `query`, `segment_type`); Timeline Planner (`start`, `end`, `duration`, `text`); Review UI (`text`, `needs_review`, `asr_confidence`). Chi tiết mapping: [01 §4.2](01_system_architecture.md#42-audio-analyzer) và [02 §13](02_data_contract.md#13-quy-tắc-mapping-giữa-các-file).

## 10. Test cases

| # | Test | Input / điều kiện | Kỳ vọng |
| - | ---- | ----------------- | ------- |
| 1 | Audio hợp lệ | `media_metadata.json` + `voiceover.wav` | Tạo `audio_segments.json`; ≥ 1 segment; top-level đúng `project_id`, `audio_id`, `language`; mỗi segment đủ required fields |
| 2 | Audio `status = warning` | Audio warning | Vẫn chạy; warning trong log; tạo segments nếu ASR OK |
| 3 | Audio `status = error` | Audio error | Dừng; không tạo file giả; báo lỗi rõ |
| 4 | Timestamp hợp lệ | Output segments | `start >= 0`; `end > start`; `duration = end - start`; không overlap; tăng dần theo `start`; không vượt duration audio |
| 5 | ASR không có confidence | Model không trả confidence | `asr_confidence = null`; không bịa; pipeline tiếp nếu text/timestamp OK |
| 6 | Segment quá ngắn | Nhiều câu rất ngắn | Gộp nếu hợp nghĩa; không tạo segment vụn |
| 7 | Segment quá dài | Chunk ASR rất dài | Tách tại điểm ngắt tự nhiên; không gộp nhiều ý |
| 8 | Query không rỗng | Mọi segment | Có `query`; query yếu/chung → `needs_review = true` |
| 9 | segment_type | Output có field | Thuộc allowed values; không sinh `speech`, `silence`, `normal` |
| 10 | Chạy lại module | Output đã tồn tại | Không `--overwrite` → dừng an toàn; có `--overwrite` → ghi đè; input/rule không đổi → ID ổn định |

CLI tối thiểu (nếu cần smoke test): `python -m audio_analyzer.main --media-metadata data/intermediate/media_metadata.json --output-dir data/intermediate`.

## 11. Acceptance criteria

Module Audio Analyzer đạt yêu cầu MVP khi:

1. Đọc được `media_metadata.json`; lấy đúng `audio.normalized_path`.
2. Chạy với `status = ready` hoặc `warning`; dừng đúng khi `error`.
3. Tạo transcript có timestamp; chia segment có ý nghĩa.
4. Tạo `audio_segments.json` đúng schema hiện hành.
5. Mỗi segment có `segment_id`, `start`, `end`, `duration`, `text`, `query`, `asr_confidence`.
6. Thời gian dùng giây; segment không overlap, sắp xếp theo thời gian.
7. `segment_id` ổn định nếu input và rule segmentation không đổi.
8. `query` không rỗng, đủ dùng cho Matching Engine.
9. `asr_confidence` ∈ `[0.0, 1.0]` hoặc `null`.
10. `needs_review` gán cho đoạn rủi ro nếu triển khai.
11. `segment_type` nếu có thì thuộc allowed values.
12. Tạo `audio_analysis_log.json` hỗ trợ debug.
13. Embedding Indexer / Matching Engine dùng được `query`/`translated_query`.
14. Timeline Planner dùng được timestamp; Review UI hiển thị transcript và highlight review.
15. Có quy tắc rõ khi chạy lại cùng `project_id`.

## 12. Checklist

```text
[ ] Đọc và hiểu docs/details/02_data_contract.md
[ ] Đọc được media_metadata.json
[ ] Lấy đúng audio.normalized_path
[ ] Validate được audio normalized tồn tại và đọc được
[ ] Chạy được ASR
[ ] Có transcript có timestamp
[ ] Chia được segment có ý nghĩa
[ ] Không chia segment quá vụn
[ ] Không để segment quá dài chứa nhiều ý
[ ] Sinh đúng segment_id dạng a001, a002, ...
[ ] Tính đúng start, end, duration bằng giây
[ ] Không có segment overlap
[ ] Sinh được query không rỗng
[ ] Sinh được keywords nếu có thể
[ ] Sinh được translated_query nếu pipeline cần
[ ] Gán segment_type đúng allowed values nếu có
[ ] asr_confidence là number trong [0.0, 1.0] hoặc null
[ ] Không bịa confidence nếu ASR không trả về
[ ] Gán needs_review cho segment rủi ro nếu triển khai
[ ] Ghi đúng audio_segments.json
[ ] Ghi được audio_analysis_log.json
[ ] Không hard-code path cá nhân
[ ] Có quy tắc --overwrite hoặc cơ chế tương đương khi chạy lại
[ ] Có test với audio mẫu ngắn
[ ] Output có thể đưa cho Embedding Indexer; Matching Engine, Timeline Planner, Review UI dùng ở các bước sau
```
