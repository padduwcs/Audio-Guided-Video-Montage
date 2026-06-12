# 04. Stage 2 - Audio Analysis

## 1. Mục tiêu của stage

Stage 2 - Audio Analysis có nhiệm vụ phân tích audio thuyết minh đã được chuẩn hóa từ Stage 1, chuyển audio thành transcript có timestamp, chia transcript thành các audio segment có ý nghĩa và tạo `audio_segments.json` cho các stage phía sau.

Stage này là nhánh phân tích audio chính của hệ thống. Output của stage này sẽ quyết định hệ thống hiểu audio đang nói gì, nói ở thời điểm nào và nên dùng câu query nào để tìm clip hình ảnh tương ứng.

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

## 2. Vị trí trong pipeline

Stage này nằm sau Input Processor và chạy song song tương đối độc lập với Video Analyzer:

```text
Input Processor
        |
        |-- media_metadata.json
        |-- normalized audio file
        |
        v
Audio Analyzer
        |
        |-- audio_segments.json
        |-- audio_analysis_log.json
        |
        |--> Embedding Indexer
        |--> Matching Engine (later, after Embedding Indexer)
        |--> Timeline Planner (later, after Matching Engine)
        |--> Review UI (later, after Timeline Planner)
        |--> Evaluation (later)
```

Audio Analyzer không cần đọc video nguồn. Stage này chỉ cần audio đã chuẩn hóa và metadata liên quan đến audio.

## 3. Phạm vi trách nhiệm

### 3.1. Stage này cần làm

Audio Analyzer cần xử lý các phần sau:

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

### 3.2. Stage này không làm

Audio Analyzer không chịu trách nhiệm cho các phần sau:

* Không chuẩn hóa audio.
* Không chỉnh sửa trực tiếp file audio.
* Không detect scene/shot trong video.
* Không trích keyframe.
* Không tính embedding.
* Không matching audio segment với clip.
* Không chọn clip cho timeline.
* Không tạo `timeline.json`.
* Không render video cuối.

Nếu người dùng sửa transcript trên UI ở stage sau, UI có thể cập nhật dữ liệu phục vụ review, nhưng Audio Analyzer không phải là nơi quản lý timeline chỉnh sửa của người dùng.

## 4. Input

### 4.1. Input chính

Audio Analyzer đọc:

```text
data/intermediate/media_metadata.json
```

Audio path thực tế lấy từ:

```text
media_metadata.json -> audio.normalized_path
```

(Ví dụ sample: `data/normalized/voiceover.wav`.)

Không hard-code đường dẫn audio trong module.

### 4.2. Điều kiện input hợp lệ

`media_metadata.json` phải thỏa:

* Parse được JSON.
* Có top-level field `schema_version`.
* Có top-level field `project_id`.
* Có object `audio`.
* `audio.audio_id` tồn tại.
* `audio.normalized_path` tồn tại.
* `audio.duration > 0`.
* `audio.status` là `ready` hoặc `warning`.

Audio Analyzer được phép chạy với audio có `status = warning`, vì theo Stage 1, `ready` và `warning` đều là usable.

Audio Analyzer không được chạy nếu:

* Không có object `audio`.
* `audio.status = error`.
* File trong `audio.normalized_path` không tồn tại.
* File audio không đọc được.
* Duration audio bằng `0` hoặc không xác định được.

### 4.3. Cấu hình chạy module

Cấu hình dưới đây là cấu hình nội bộ của Audio Analyzer, không phải Data Contract bắt buộc giữa các module.

Ví dụ cấu hình:

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

Trong MVP, các giá trị đề xuất:

| Tham số | Giá trị đề xuất |
| ------- | --------------- |
| `language` | `vi` |
| `word_timestamps` | `true` nếu model hỗ trợ |
| `min_segment_duration` | `2.0` giây |
| `max_segment_duration` | `8.0` giây |
| `merge_short_segments` | `true` |
| `split_long_segments` | `true` |
| `generate_keywords` | `true` |
| `generate_translated_query` | `true` nếu embedding/matching cần tiếng Anh |
| `low_asr_confidence_threshold` | `0.65` |
| `manual_correction.enabled` | `false` trong MVP tự động |

Ghi chú:

* Không bắt buộc dùng đúng model ASR trong ví dụ. Thành viên có thể dùng model khác nếu output vẫn đúng contract.
* Nếu ASR không hỗ trợ word-level timestamp, có thể dùng sentence-level hoặc chunk-level timestamp.
* Nếu ASR không trả về confidence, dùng `asr_confidence = null`, không tự đặt bừa `0` hoặc `1`.
* Nếu chưa làm được `translated_query`, có thể để `translated_query = null` hoặc bỏ field này vì đây là optional field.
* Nếu có transcript đã được người dùng sửa, có thể dùng làm input nội bộ để tạo lại `audio_segments.json`, nhưng output cuối vẫn phải tuân thủ schema cũ.

## 5. Output

Stage này tạo output chính:

```text
data/intermediate/audio_segments.json
```

Stage này có thể tạo output phụ:

```text
data/intermediate/audio_analysis_log.json
```

Trong đó:

* `audio_segments.json` là Data Contract chính cho các stage sau.
* `audio_analysis_log.json` là log phụ để debug ASR, segmentation và query generation.

Các module sau chỉ nên phụ thuộc vào `audio_segments.json`. Log phụ không phải contract bắt buộc.

## 6. Data Contract: `audio_segments.json`

### 6.1. Vai trò

`audio_segments.json` lưu transcript có timestamp và các audio segment dùng để matching với video.

File này giúp các module sau biết:

* Audio có những đoạn nội dung nào.
* Mỗi đoạn bắt đầu và kết thúc ở thời điểm nào.
* Text gốc của từng đoạn là gì.
* Query nào nên dùng để tìm clip phù hợp.
* Đoạn nào có độ tin cậy ASR thấp.
* Đoạn nào cần người dùng review.

### 6.2. Cấu trúc top-level

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

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `schema_version` | string | Phiên bản schema |
| `project_id` | string | ID dự án đang xử lý |
| `audio_id` | string | ID audio thuyết minh |
| `language` | string | Ngôn ngữ transcript |
| `created_at` | string | Thời điểm tạo file |
| `items` | array[object] | Danh sách audio segment |

Quy ước:

* `schema_version` dùng `"1.0"` trong MVP.
* `project_id` lấy từ `media_metadata.json`.
* `audio_id` lấy từ `media_metadata.json -> audio.audio_id`.
* `language` dùng `"vi"` trong MVP nếu audio tiếng Việt.
* `items` phải có ít nhất một segment nếu ASR chạy thành công và audio có lời nói.

### 6.3. Segment item

Required fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `segment_id` | string | ID audio segment |
| `start` | number | Thời điểm bắt đầu |
| `end` | number | Thời điểm kết thúc |
| `duration` | number | Thời lượng segment |
| `text` | string | Transcript gốc |
| `query` | string | Câu query dùng cho matching |
| `asr_confidence` | number/null | Độ tin cậy ASR nếu có |

Optional fields:

| Field | Type | Ý nghĩa |
| ----- | ---- | ------- |
| `keywords` | array[string] | Từ khóa chính |
| `translated_query` | string/null | Query tiếng Anh nếu cần |
| `segment_type` | string | Loại segment |
| `needs_review` | boolean | Có cần người dùng xem lại transcript không |
| `notes` | string | Ghi chú |

Allowed `segment_type`:

```text
description
action
transition
abstract
unknown
```

## 7. Quy tắc timestamp

Tất cả thời gian trong `audio_segments.json` dùng đơn vị giây.

Quy tắc bắt buộc:

* `start >= 0`
* `end > start`
* `duration = end - start`
* `end` không được vượt quá duration audio quá sai số nhỏ.
* Các segment không được overlap nhau.
* Thứ tự segment trong `items` phải tăng dần theo `start`.

Sai số làm tròn chấp nhận được:

```text
0.01s
```

Gợi ý làm tròn:

* `start`, `end`, `duration`: làm tròn 2 hoặc 3 chữ số thập phân.
* Khi tính `duration`, nên dùng cùng độ chính xác với `start` và `end` để tránh lệch nhỏ khó debug.

## 8. Quy tắc đặt ID

ID cần ngắn gọn, ổn định và dễ map giữa các file.

Với MVP, quy tắc đề xuất:

```text
segment_id: a001, a002, a003, ...
```

Quy tắc sinh `segment_id`:

* Đánh số theo thứ tự segment trong audio.
* Số thứ tự bắt đầu từ `1`.
* Dùng padding 3 chữ số trong MVP: `a001`, `a002`, `a003`.
* Nếu chạy lại với cùng audio và cùng rule segmentation, ID nên giữ ổn định.
* Không dùng text transcript làm ID.
* Không dùng timestamp làm ID chính, vì timestamp có thể thay đổi nhẹ khi đổi model ASR.

Nếu sau này hỗ trợ nhiều audio, có thể mở rộng ID, nhưng MVP chỉ có một audio chính nên không cần phức tạp hóa.

## 9. Quy trình xử lý đề xuất

### 9.1. Bước 1 - Đọc metadata

Audio Analyzer đọc `media_metadata.json` và lấy:

* `project_id`
* `audio.audio_id`
* `audio.normalized_path`
* `audio.duration`
* `audio.status`
* `audio.sample_rate`
* `audio.channels`

Nếu `audio.status = warning`, module vẫn chạy tiếp nhưng ghi lại warning trong `audio_analysis_log.json`.

### 9.2. Bước 2 - Validate audio file

Kiểm tra:

* File trong `audio.normalized_path` tồn tại.
* File đọc được.
* Duration thực tế gần với `audio.duration` trong metadata.
* Audio có stream hợp lệ.

Nếu duration thực tế lệch nhẹ do encode/decode, có thể tiếp tục. Nếu lệch lớn, nên ghi warning hoặc dừng tùy mức độ.

Gợi ý:

```text
Lệch <= 0.1s: chấp nhận
Lệch > 0.1s và <= 1.0s: warning
Lệch > 1.0s: cần xem lại, có thể dừng nếu ảnh hưởng timestamp
```

### 9.3. Bước 3 - Chạy ASR

Chạy ASR trên file audio normalized.

Output nội bộ tối thiểu cần có:

* text transcript
* timestamp theo câu, cụm từ hoặc word nếu model hỗ trợ
* confidence nếu model hỗ trợ

Yêu cầu:

* Không thay đổi audio trong bước này.
* Không cắt bỏ silence trong audio trước khi ASR nếu điều đó làm lệch timestamp.
* Timestamp phải tương ứng với audio normalized.
* Nếu ASR trả về timestamp theo chunk dài, bước segmentation cần chia nhỏ hợp lý hơn.

### 9.4. Bước 4 - Làm sạch transcript nhẹ

Có thể làm sạch transcript ở mức nhẹ trước khi tạo segment và query.

Được phép:

* Chuẩn hóa khoảng trắng.
* Bỏ ký tự lặp vô nghĩa.
* Chuẩn hóa dấu câu đơn giản.
* Sửa lỗi viết hoa/viết thường nếu không làm đổi nghĩa.

Không nên:

* Tự viết lại nội dung theo ý khác.
* Xóa tên riêng, địa danh, thuật ngữ quan trọng.
* Dịch toàn bộ transcript rồi thay thế `text` gốc.
* Tự thêm thông tin không có trong audio.

Field `text` nên giữ transcript gốc đã làm sạch nhẹ, không phải bản tóm tắt.

### 9.5. Bước 5 - Chia audio segment

Mục tiêu của segmentation là tạo các đoạn đủ ý nghĩa để chọn hình, không phải chỉ cắt theo từng câu máy móc.

Segment tốt nên thỏa:

* Có ý nghĩa tương đối hoàn chỉnh.
* Có thể dùng để tìm clip hình ảnh.
* Không quá ngắn khiến clip bị giật.
* Không quá dài khiến một clip khó minh họa toàn bộ ý.
* Bám theo nhịp ngắt tự nhiên của voice-over.

Gợi ý duration:

```text
min_segment_duration: 2.0s
max_segment_duration: 8.0s
```

Quy tắc:

* Segment ngắn hơn `2.0s` nên được gộp với segment trước hoặc sau nếu hợp nghĩa.
* Segment dài hơn `8.0s` nên được tách thành nhiều segment nếu có điểm ngắt tự nhiên.
* Không tách giữa một cụm danh từ quan trọng.
* Không tách giữa một hành động và đối tượng chính của hành động.
* Ưu tiên tách tại dấu câu, khoảng dừng tự nhiên hoặc chuyển ý.

Ví dụ:

```text
"Đây là khu vực cổng chính của khu tham quan. Sau đó, đoàn di chuyển vào khu trưng bày."
```

Nên tách thành:

```text
a001: Đây là khu vực cổng chính của khu tham quan.
a002: Sau đó, đoàn di chuyển vào khu trưng bày.
```

Không nên tách thành:

```text
a001: Đây là khu vực
a002: cổng chính
a003: của khu tham quan
```

### 9.6. Bước 6 - Xử lý khoảng lặng

Trong MVP, không cần tạo segment riêng cho mọi khoảng lặng ngắn.

Quy tắc đề xuất:

* Khoảng lặng ngắn giữa hai câu có thể được gộp vào segment trước hoặc sau.
* Không tạo segment rỗng chỉ vì có silence.
* Nếu có khoảng lặng dài và có ý nghĩa chuyển đoạn, có thể tạo segment `transition` nếu cần cho Timeline Planner.
* Nếu tạo segment cho khoảng nghỉ, `text` cần ghi rõ dạng dễ hiểu, ví dụ `"Khoảng nghỉ chuyển đoạn."`, và `segment_type = "transition"`.

Ghi chú:

* `text` là required field nên không để chuỗi rỗng.
* Nếu không chắc có cần segment silence hay không, MVP nên gộp khoảng lặng vào segment gần nhất để tránh làm phức tạp timeline.

### 9.7. Bước 7 - Sinh query

`query` là text dùng cho Matching Engine hoặc Embedding Indexer tìm clip phù hợp.

Query tốt nên:

* Ngắn hơn transcript gốc.
* Giữ lại danh từ, địa điểm, đối tượng, hành động chính.
* Bỏ bớt từ đệm, từ nối không quan trọng.
* Không thêm thông tin không có trong transcript.
* Không quá chung chung.

Ví dụ:

```text
text: "Đây là khu vực cổng chính của khu tham quan."
query: "khu vực cổng chính khu tham quan"
```

Ví dụ:

```text
text: "Sau đó, đoàn di chuyển vào khu trưng bày."
query: "đoàn di chuyển vào khu trưng bày"
```

Với các câu trừu tượng:

```text
text: "Chuyến đi này để lại rất nhiều kỷ niệm đáng nhớ."
query: "kỷ niệm đáng nhớ chuyến đi"
segment_type: "abstract"
```

Ghi chú:

* Với segment trừu tượng, query nên giữ lại ý chính có trong transcript như "kỷ niệm", "trải nghiệm", "đáng nhớ"; không nên bịa ra địa điểm, cảm xúc cụ thể hoặc hành động cụ thể không xuất hiện trong audio.
* Nếu query không đủ thông tin để matching tốt, đánh dấu `needs_review = true`.

### 9.8. Bước 8 - Trích keywords

`keywords` là optional nhưng nên có nếu làm được.

Keywords nên gồm:

* Địa điểm.
* Đối tượng chính.
* Hành động chính.
* Món ăn, vật thể, khu vực, sự kiện nếu có.

Ví dụ:

```json
"keywords": ["cổng chính", "khu tham quan"]
```

Không nên đưa quá nhiều từ không quan trọng vào keywords.

### 9.9. Bước 9 - Tạo translated query nếu cần

`translated_query` là optional.

Nên tạo `translated_query` khi:

* Embedding model hoạt động tốt hơn với tiếng Anh.
* Matching Engine dùng model image-text thiên về tiếng Anh.
* Nhóm muốn so sánh chất lượng matching giữa query tiếng Việt và tiếng Anh.

Không bắt buộc tạo `translated_query` nếu:

* Embedding model hỗ trợ tiếng Việt tốt.
* Chưa có module dịch ổn định.
* MVP muốn giảm độ phức tạp.

Quy tắc:

* `query` vẫn giữ tiếng Việt.
* `translated_query` là bản dịch hoặc diễn đạt tiếng Anh của `query`.
* Nếu chưa có, dùng `null` hoặc bỏ field.

### 9.10. Bước 10 - Gán segment_type

`segment_type` giúp các module sau hiểu kiểu nội dung của segment.

Quy tắc gợi ý:

| segment_type | Khi dùng |
| ------------ | -------- |
| `description` | Đoạn mô tả địa điểm, vật thể, bối cảnh, con người |
| `action` | Đoạn mô tả hành động, quá trình, thao tác |
| `transition` | Đoạn chuyển ý, di chuyển, chuyển cảnh, khoảng nghỉ |
| `abstract` | Đoạn cảm xúc, tổng kết, nhận xét chung, ý trừu tượng |
| `unknown` | Không xác định được loại nội dung |

Ví dụ:

```json
{
  "text": "Đây là khu vực cổng chính của khu tham quan.",
  "segment_type": "description"
}
```

```json
{
  "text": "Sau đó, đoàn di chuyển vào khu trưng bày.",
  "segment_type": "transition"
}
```

```json
{
  "text": "Đầu tiên, cho bột mì và trứng vào tô rồi trộn đều.",
  "segment_type": "action"
}
```

### 9.11. Bước 11 - Gán needs_review

`needs_review` là optional nhưng nên có trong MVP để UI highlight đoạn cần kiểm tra.

Nên đặt `needs_review = true` nếu:

* `asr_confidence` thấp hơn ngưỡng.
* ASR không chắc tên riêng, địa danh hoặc thuật ngữ.
* Text quá ngắn hoặc khó hiểu.
* Query quá chung chung.
* Segment quá dài hoặc quá ngắn nhưng không thể xử lý tốt.
* `segment_type = unknown`.
* `translated_query` không tạo được trong khi pipeline yêu cầu.

Nên đặt `needs_review = false` nếu:

* Transcript rõ.
* Timestamp hợp lý.
* Query đủ thông tin.
* Segment có duration hợp lý.

Nếu chưa triển khai rule review, có thể bỏ field này hoặc mặc định `false`, nhưng MVP nên có để hỗ trợ UI.

### 9.12. Bước 12 - Ghi `audio_segments.json`

Trước khi ghi file, cần kiểm tra:

* Có đủ top-level fields.
* `items` không rỗng nếu audio có lời nói.
* Mỗi item có đủ required fields.
* `segment_id` không trùng.
* `start`, `end`, `duration` hợp lệ.
* Segment được sắp xếp tăng dần theo `start`.
* Segment không overlap.
* `query` không rỗng.
* `asr_confidence` nằm trong `0.0` đến `1.0` hoặc `null`.
* `segment_type` nếu có thì thuộc allowed values.

### 9.13. Bước tùy chọn - Nhận transcript đã sửa

Kiến trúc tổng thể có nhắc đến khả năng sửa transcript nếu ASR nhận sai. Với MVP, phần sửa transcript có thể làm sau hoặc nằm ở Review UI, nhưng Audio Analyzer nên được thiết kế để không bị khóa cứng vào một lần ASR duy nhất.

Nếu có transcript đã được người dùng sửa:

* Có thể dùng transcript đã sửa để tạo lại `audio_segments.json`.
* Nếu chỉ sửa text mà không đổi timestamp, nên giữ nguyên `segment_id`.
* Nếu sửa làm thay đổi cách chia segment, cần tạo lại `segment_id` theo thứ tự segment mới.
* Không tự thay đổi timestamp nếu người dùng chỉ sửa lỗi chữ.
* Nếu người dùng sửa timestamp, cần validate lại toàn bộ `start`, `end`, `duration`.
* Cần ghi rõ trong `audio_analysis_log.json` rằng output đã dùng transcript correction.

Gợi ý dữ liệu correction nội bộ:

```json
{
  "project_id": "demo_01",
  "audio_id": "audio_01",
  "items": [
    {
      "segment_id": "a001",
      "text": "Đây là khu vực cổng chính của khu tham quan.",
      "start": 0.0,
      "end": 5.2
    }
  ]
}
```

File correction này không phải Data Contract chính trong MVP. Nếu nhóm chưa làm UI sửa transcript, có thể bỏ qua phần này.

## 10. Quy tắc segmentation chi tiết

### 10.1. Segment không nên quá nhỏ

Không nên chia theo từng cụm quá ngắn nếu cụm đó không đủ ý nghĩa để chọn hình.

Ví dụ không tốt:

```text
a001: "Đây là"
a002: "khu vực"
a003: "cổng chính"
```

Lý do:

* Matching khó tìm clip phù hợp.
* Timeline dễ bị cắt quá nhanh.
* UI review bị chia vụn.

### 10.2. Segment không nên quá dài

Không nên để một segment chứa quá nhiều ý khác nhau.

Ví dụ không tốt:

```text
a001: "Đây là khu vực cổng chính của khu tham quan. Sau đó đoàn di chuyển vào khu trưng bày. Bên trong có rất nhiều hiện vật lịch sử."
```

Lý do:

* Một clip khó minh họa hết nhiều ý.
* Matching có thể bị nhiễu vì nhiều keyword.
* Timeline Planner khó chọn duration hình phù hợp.

### 10.3. Ưu tiên ý nghĩa hơn câu chữ máy móc

Segment nên đi theo ý nghĩa dựng video.

Một câu dài có thể tách thành nhiều segment nếu chứa nhiều hành động hoặc nhiều bối cảnh.

Nhiều câu ngắn có thể gộp lại nếu cùng nói về một cảnh.

### 10.4. Không làm lệch timestamp

Khi gộp hoặc tách segment:

* `start` lấy theo mốc bắt đầu của phần lời nói đầu tiên trong segment.
* `end` lấy theo mốc kết thúc của phần lời nói cuối cùng trong segment.
* Không tự tạo timestamp không có cơ sở.
* Nếu phải ước lượng timestamp do ASR không trả chi tiết, cần ghi rõ trong `audio_analysis_log.json`.

## 11. Quy tắc query chi tiết

### 11.1. Query cho Matching Engine

Matching Engine cần query đủ rõ để so khớp với clip.

Query nên ưu tiên:

* Danh từ cụ thể.
* Địa điểm.
* Hành động nhìn thấy được.
* Đối tượng chính.
* Bối cảnh.

Query nên giảm:

* Từ đệm.
* Từ nối.
* Đại từ không rõ nghĩa.
* Các cụm quá chung như "rất đẹp", "thật tuyệt", nếu đứng một mình.

### 11.2. Query cho nội dung trừu tượng

Với nội dung trừu tượng, không nên cố ép query thành cảnh quá cụ thể.

Ví dụ:

```text
text: "Đây là trải nghiệm rất đáng nhớ với cả đoàn."
query: "trải nghiệm đáng nhớ cả đoàn"
segment_type: "abstract"
needs_review: true
```

Matching Engine có thể dùng các clip fallback như cảnh tổng, cảnh mọi người, cảnh không khí chung.

### 11.3. Query và translated_query

Nếu có `translated_query`, hai field nên có quan hệ rõ:

```text
query: tiếng Việt, bám sát transcript
translated_query: tiếng Anh, bám sát query
```

Không dùng `translated_query` để thêm ý mới.

## 12. Quy tắc confidence và review

### 12.1. `asr_confidence`

`asr_confidence` là độ tin cậy của ASR cho segment.

Quy tắc:

* Nếu model trả confidence theo segment, dùng trực tiếp sau khi chuẩn hóa về `0.0` đến `1.0`.
* Nếu model trả confidence theo word, có thể lấy trung bình hoặc trung bình có trọng số theo duration.
* Nếu model không trả confidence, dùng `null`.
* Không tự đặt `1.0` chỉ vì transcript nhìn có vẻ đúng.
* Không tự đặt `0.0` khi không có dữ liệu confidence.

### 12.2. `needs_review`

`needs_review` không chỉ phụ thuộc vào `asr_confidence`.

Một segment có thể cần review dù confidence cao nếu:

* Query quá mơ hồ.
* Segment quá dài.
* Segment chứa tên riêng quan trọng.
* Segment thuộc loại `abstract`.
* Timestamp có khả năng lệch.

Một segment có `asr_confidence = null` không bắt buộc phải `needs_review = true`, nhưng nếu ASR model không có confidence, nên dùng thêm rule khác để phát hiện rủi ro.

## 13. Output phụ: `audio_analysis_log.json`

### 13.1. Vai trò

`audio_analysis_log.json` là file log phụ của Stage 2, dùng để debug ASR, segmentation và query generation.

File này không phải Data Contract chính giữa các module. Các module sau không nên phụ thuộc vào file này để chạy logic chính.

Nên dùng file này để ghi:

* ASR model/provider đã dùng.
* Đường dẫn audio input.
* Duration audio theo metadata và theo probe thực tế.
* Raw ASR chunks nếu cần.
* Số segment tạo ra.
* Segment nào bị merge/split.
* Segment nào bị `needs_review`.
* Lý do gán warning hoặc error.
* Thời gian chạy module nếu cần.

### 13.2. Cấu trúc đề xuất

Đây là cấu trúc đề xuất, không bắt buộc phải xem là schema liên module:

```json
{
  "schema_version": "1.0",
  "project_id": "demo_01",
  "audio_id": "audio_01",
  "created_at": "2026-06-11T10:05:00Z",
  "asr": {
    "provider": "whisper",
    "model": "base",
    "language": "vi",
    "word_timestamps": true
  },
  "input": {
    "audio_path": "data/normalized/voiceover.wav",
    "metadata_duration": 16.0,
    "probed_duration": 16.0
  },
  "summary": {
    "segment_count": 12,
    "needs_review_count": 2,
    "min_segment_duration": 2.4,
    "max_segment_duration": 7.8
  },
  "warnings": [],
  "errors": []
}
```

### 13.3. Nguyên tắc sử dụng

`audio_segments.json` là nguồn dữ liệu chính cho các module sau. `audio_analysis_log.json` chỉ dùng để:

* Debug vì sao transcript sai.
* Debug vì sao segment bị chia/gộp.
* Kiểm tra query sinh ra có hợp lý không.
* Hỗ trợ leader review chất lượng stage.

Nếu `audio_segments.json` và `audio_analysis_log.json` có thông tin mâu thuẫn, các module pipeline phải ưu tiên `audio_segments.json`.

## 14. Ví dụ `audio_segments.json`

Mẫu chuẩn: `docs/samples/audio_segments_sample.json`.

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
      "text": "Day la khu vuc cong chinh cua khu tham quan.",
      "query": "khu vuc cong chinh khu tham quan",
      "translated_query": "main entrance of tourist area",
      "segment_type": "description",
      "asr_confidence": 0.91,
      "needs_review": false
    },
    {
      "segment_id": "a002",
      "start": 5.2,
      "end": 10.8,
      "duration": 5.6,
      "text": "Ben trong la khu trung bay voi nhieu hien vat noi bat.",
      "query": "khu trung bay hien vat noi bat",
      "translated_query": "exhibition area with notable artifacts",
      "segment_type": "description",
      "asr_confidence": 0.84,
      "needs_review": false
    },
    {
      "segment_id": "a003",
      "start": 10.8,
      "end": 16.0,
      "duration": 5.2,
      "text": "Khach tham quan di chuyen sang khu trai nghiem tiep theo.",
      "query": "khach tham quan di chuyen khu trai nghiem",
      "translated_query": "visitors moving to the next experience area",
      "segment_type": "action",
      "asr_confidence": 0.66,
      "needs_review": true
    }
  ]
}
```

## 15. Quan hệ với các module khác

### 15.1. Input Processor

Audio Analyzer đọc:

```text
media_metadata.json
audio.normalized_path
```

Audio Analyzer không tự tìm audio raw và không tự normalize lại audio.

### 15.2. Embedding Indexer

Embedding Indexer có thể đọc:

```text
audio_segments.json
items[*].query
items[*].translated_query
```

Nếu có `translated_query`, Embedding Indexer có thể ưu tiên field này khi dùng model image-text thiên về tiếng Anh.

Nếu không có `translated_query`, Embedding Indexer dùng `query`.

### 15.3. Matching Engine

Matching Engine đọc:

```text
audio_segments.json
items[*].segment_id
items[*].query
items[*].translated_query
items[*].segment_type
```

Matching Engine dùng `segment_id` để tạo `candidate_set_id`.

Ví dụ:

```text
segment_id = a001
candidate_set_id = candidates_a001
```

### 15.4. Timeline Planner

Timeline Planner đọc:

```text
audio_segments.json
items[*].start
items[*].end
items[*].duration
items[*].text
```

Timeline Planner dùng timestamp và duration để tạo các item trong `timeline.json`.

### 15.5. Review UI

Review UI đọc:

```text
audio_segments.json
items[*].text
items[*].needs_review
items[*].asr_confidence
```

UI nên highlight các segment có `needs_review = true` hoặc `asr_confidence` thấp nếu field này có giá trị.

### 15.6. Evaluation

Evaluation có thể dùng `audio_segments.json` để:

* Tính coverage theo segment.
* Tính tỷ lệ segment cần review.
* Đánh giá duration error.
* So sánh matching quality theo từng segment type.

## 16. Điều kiện handoff output

Stage 2 được phép bàn giao `audio_segments.json` cho Embedding Indexer; các module về sau như Matching Engine, Timeline Planner và Review UI có thể dùng cùng output này khi thỏa các điều kiện sau:

```text
audio_segments.json parse được
audio_segments.json có đủ top-level required fields
items không rỗng
mỗi item có đủ required fields
segment_id không trùng
timestamp hợp lệ và không overlap
query không rỗng
asr_confidence là number trong [0.0, 1.0] hoặc null
```

Nếu ASR không nhận được lời nói nào:

* Không tạo metadata giả.
* Module nên báo lỗi rõ ràng hoặc tạo log giải thích.
* Pipeline không nên chạy tiếp vì không có segment để matching.

Nếu một số segment có `needs_review = true`, pipeline vẫn được chạy tiếp. Đây là cảnh báo cho UI và người dùng, không phải lỗi chặn pipeline.

## 17. Ràng buộc kỹ thuật

### 17.1. Không làm lệch audio timeline

Audio Analyzer không được thay đổi file audio normalized trong quá trình phân tích.

Không được:

* Cắt silence khỏi audio rồi dùng timestamp của file đã cắt.
* Thay đổi speed audio.
* Dịch timestamp theo cảm tính.

Nếu có xử lý phụ để ASR tốt hơn, ví dụ tạo bản audio tạm đã denoise, timestamp output vẫn phải map về audio normalized gốc.

### 17.2. Không bịa confidence

Nếu ASR model không trả về confidence, dùng:

```json
"asr_confidence": null
```

Không dùng:

```json
"asr_confidence": 1.0
```

chỉ vì transcript được tạo thành công.

### 17.3. Không bịa query

Query được phép rút gọn hoặc diễn đạt lại nhẹ để phục vụ matching, nhưng không được thêm thông tin không có trong transcript.

Ví dụ không tốt:

```text
text: "Mọi người tiếp tục tham quan."
query: "mọi người tham quan khu trưng bày lịch sử ở tầng hai"
```

Nếu transcript không nói "khu trưng bày lịch sử ở tầng hai", không nên thêm vào query.

### 17.4. Không để query rỗng

`query` là required field.

Nếu text quá ngắn hoặc khó sinh query:

* Dùng text đã làm sạch làm query.
* Gán `needs_review = true`.
* Ghi lý do trong `notes` nếu cần.

### 17.5. Không phụ thuộc vào log phụ

Các module sau không được phụ thuộc vào `audio_analysis_log.json` để chạy logic chính.

Nếu thông tin cần thiết cho Matching, Timeline hoặc UI, thông tin đó phải nằm trong `audio_segments.json`.

## 18. Re-run behavior

Audio Analyzer cần có quy tắc rõ ràng khi chạy lại với cùng `project_id`.

### 18.1. Mục tiêu

Chạy lại module không được làm `segment_id` thay đổi bất ngờ nếu audio và rule segmentation không đổi.

Yêu cầu:

* Nếu input audio và cấu hình segmentation không đổi, segment order và `segment_id` nên giữ ổn định.
* Nếu đổi ASR model hoặc segmentation rule, segment boundary có thể thay đổi, nhưng cần ghi trong `audio_analysis_log.json`.
* Không ghi đè output cũ nếu người chạy chưa cho phép.

### 18.2. Quy tắc đề xuất

Nếu chạy lại với cùng `project_id`:

* Nếu có flag `--overwrite`, module được phép ghi đè `audio_segments.json` và `audio_analysis_log.json`.
* Nếu không có `--overwrite`, module nên báo output đã tồn tại và dừng an toàn, hoặc yêu cầu người dùng chọn output/run khác.
* Nếu đã có `matching_candidates.json` hoặc `timeline.json` dựa trên `audio_segments.json` cũ, nên chạy lại các stage sau để tránh lệch `segment_id`, timestamp hoặc query.

## 19. Gợi ý cấu trúc code

Đây là gợi ý tổ chức module, không bắt buộc nếu nhóm đã có style code riêng.

```text
audio_analyzer/
│
├── __init__.py
├── main.py
├── config.py
├── asr_runner.py
├── transcript_cleaner.py
├── segmenter.py
├── query_builder.py
├── audio_segments_writer.py
└── validator.py
```

Vai trò từng file:

| File | Vai trò |
| ---- | ------- |
| `main.py` | Entry point chạy module |
| `config.py` | Đọc và validate cấu hình chạy module |
| `asr_runner.py` | Chạy ASR và trả transcript có timestamp |
| `transcript_cleaner.py` | Làm sạch transcript nhẹ |
| `segmenter.py` | Chia transcript thành audio segment |
| `query_builder.py` | Sinh query, keywords, translated_query |
| `audio_segments_writer.py` | Tạo và ghi `audio_segments.json` |
| `validator.py` | Kiểm tra input và output theo quy tắc hiện hành |

Nếu nhóm dùng ngôn ngữ hoặc framework khác, vẫn cần giữ nguyên trách nhiệm logic tương đương.

## 20. Gợi ý CLI

CLI tối thiểu:

```text
python -m audio_analyzer.main \
  --media-metadata data/intermediate/media_metadata.json \
  --output-dir data/intermediate
```

Output mong đợi:

```text
data/intermediate/audio_segments.json
data/intermediate/audio_analysis_log.json
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

## 21. Test cases bắt buộc

### 21.1. Test audio hợp lệ

Input:

```text
media_metadata.json
voiceover.wav
```

Kỳ vọng:

* Tạo được `audio_segments.json`.
* Tạo được ít nhất một segment.
* Top-level có đúng `project_id`, `audio_id`, `language`.
* Mỗi segment có đủ required fields.

### 21.2. Test audio có status warning

Kỳ vọng:

* Audio Analyzer vẫn chạy.
* Warning được ghi vào `audio_analysis_log.json`.
* Nếu ASR thành công, vẫn tạo `audio_segments.json`.

### 21.3. Test audio có status error

Kỳ vọng:

* Module dừng.
* Không tạo `audio_segments.json` giả.
* Báo lỗi rõ ràng.

### 21.4. Test timestamp hợp lệ

Kỳ vọng:

* `start >= 0`.
* `end > start`.
* `duration = end - start`.
* Segment không overlap.
* Segment tăng dần theo `start`.
* Không có segment vượt quá duration audio quá sai số cho phép.

### 21.5. Test ASR không có confidence

Kỳ vọng:

* `asr_confidence = null`.
* Không tự đặt confidence giả.
* Pipeline vẫn chạy nếu text và timestamp hợp lệ.

### 21.6. Test segment quá ngắn

Input có nhiều câu rất ngắn.

Kỳ vọng:

* Segment quá ngắn được gộp nếu hợp nghĩa.
* Không tạo nhiều segment vụn khó matching.

### 21.7. Test segment quá dài

Input có một câu hoặc chunk ASR rất dài.

Kỳ vọng:

* Segment dài được tách nếu có điểm ngắt tự nhiên.
* Không tạo segment chứa quá nhiều ý khác nhau.

### 21.8. Test query không rỗng

Kỳ vọng:

* Mọi segment đều có `query`.
* Nếu query yếu hoặc quá chung, gán `needs_review = true`.

### 21.9. Test segment_type

Kỳ vọng:

* Nếu có `segment_type`, giá trị phải thuộc allowed values.
* Không sinh giá trị ngoài danh sách như `speech`, `silence`, `normal`.

### 21.10. Test chạy lại module

Kỳ vọng:

* Nếu chạy lại không có `--overwrite` và output đã tồn tại, module dừng an toàn hoặc yêu cầu chọn output khác.
* Nếu chạy lại có `--overwrite`, module được phép ghi đè output cũ.
* Nếu input và rule segmentation không đổi, ID giữ ổn định.

## 22. Tiêu chí nghiệm thu

Module Audio Analyzer được xem là đạt yêu cầu MVP khi:

1. Đọc được `media_metadata.json`.
2. Lấy đúng `audio.normalized_path`.
3. Chạy được với audio có `status = ready` hoặc `warning`.
4. Dừng đúng khi audio có `status = error`.
5. Tạo được transcript có timestamp.
6. Chia được audio thành segment có ý nghĩa.
7. Tạo `audio_segments.json` đúng schema hiện hành.
8. Mỗi segment có `segment_id`, `start`, `end`, `duration`, `text`, `query`, `asr_confidence`.
9. Tất cả thời gian dùng giây.
10. Segment không overlap và được sắp xếp theo thời gian.
11. `segment_id` ổn định nếu input và rule segmentation không đổi.
12. `query` không rỗng và đủ dùng cho Matching Engine.
13. `asr_confidence` là số từ `0.0` đến `1.0` hoặc `null`.
14. `needs_review` được gán cho các đoạn rủi ro nếu triển khai.
15. `segment_type` nếu có thì thuộc allowed values.
16. Tạo `audio_analysis_log.json` để hỗ trợ debug.
17. Embedding Indexer hoặc Matching Engine có thể dùng `query`/`translated_query` để chạy tiếp.
18. Timeline Planner có thể dùng timestamp để tạo timeline.
19. Review UI có thể hiển thị transcript và highlight đoạn cần review.
20. Có quy tắc rõ ràng khi chạy lại cùng `project_id`.

## 23. Checklist cho người phụ trách module

Trước khi bàn giao, người phụ trách Stage 2 cần tự kiểm tra:

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
[ ] Output có thể đưa cho Embedding Indexer chạy tiếp; Matching Engine, Timeline Planner và Review UI có thể dùng ở các bước sau
```

## 24. Ghi chú triển khai MVP

Trong MVP, không cần làm Audio Analyzer quá phức tạp. Ưu tiên quan trọng nhất là tạo được `audio_segments.json` ổn định, có timestamp đúng và query đủ tốt để matching.

Thứ tự ưu tiên nên là:

1. Đọc đúng audio normalized từ `media_metadata.json`.
2. Chạy ASR ra transcript có timestamp.
3. Chia segment hợp lý, không quá vụn.
4. Ghi `audio_segments.json` đúng schema.
5. Sinh `query` đủ tốt cho Matching Engine.
6. Đánh dấu `needs_review` cho đoạn rủi ro.
7. Ghi log dễ debug.
8. Tối ưu chất lượng transcript và query sau.

Nếu có tranh luận giữa việc làm query thật thông minh và việc đảm bảo pipeline end-to-end chạy được, MVP nên ưu tiên pipeline chạy được trước. Query có thể cải thiện dần miễn là contract không đổi.
