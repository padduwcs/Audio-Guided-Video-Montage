# Phân tích thiết kế hệ thống dựng video bán tự động theo audio thuyết minh

## 1. Mục tiêu bài toán

Bài toán cần xây dựng một hệ thống hỗ trợ tạo video hoàn chỉnh từ:

* Một hoặc nhiều video nguồn có sẵn
* Một file audio thuyết minh / voice-over có sẵn

Hệ thống không tự sinh video mới từ đầu, mà sử dụng các phân cảnh có trong video nguồn để trích xuất, chọn lọc, cắt ghép, sắp xếp và căn chỉnh sao cho hình ảnh phù hợp nhất với nội dung và nhịp độ của lời thuyết minh.

Mục tiêu không nên được hiểu là “khớp hoàn toàn tuyệt đối” giữa hình ảnh và lời nói, vì trong thực tế có nhiều đoạn thuyết minh mang tính trừu tượng, tổng quát hoặc cảm xúc, không phải lúc nào video nguồn cũng có đúng cảnh minh họa trực tiếp.

Cách phát biểu phù hợp hơn là:

> Hệ thống tối ưu mức độ phù hợp giữa hình ảnh và audio thuyết minh, trong phạm vi các video nguồn có sẵn, đồng thời đảm bảo thời lượng, chất lượng hình ảnh, nhịp dựng và khả năng chỉnh sửa của người dùng.

Thành phẩm mong muốn không chỉ là một video nháp, mà là một bản dựng có thể sử dụng được sau khi người dùng kiểm tra và tinh chỉnh cơ bản trên giao diện.

Vì vậy, hướng thiết kế phù hợp nhất không phải là tự động 100%, mà là bán tự động:

> Hệ thống tự tạo bản dựng ban đầu, sau đó người dùng có thể kiểm tra, đổi clip, chỉnh một số tham số quan trọng và render lại video cuối cùng.

---

## 2. Giả định và phạm vi bài toán

Để bài toán khả thi và rõ ràng hơn, cần xác định một số giả định đầu vào.

### 2.1. Giả định về video nguồn

* Video nguồn phải có liên quan tương đối đến nội dung audio thuyết minh.
* Video nguồn có thể gồm nhiều file khác nhau.
* Video nguồn có thể chứa nhiều cảnh dư thừa, cảnh không liên quan, cảnh rung, tối, mờ hoặc chất lượng thấp.
* Hệ thống chỉ sử dụng hình ảnh từ video nguồn, không sinh thêm cảnh mới.
* Nếu video nguồn thiếu cảnh phù hợp, hệ thống cần chọn cảnh thay thế gần nghĩa nhất hoặc cảnh fallback, đồng thời đánh dấu confidence thấp để người dùng kiểm tra.

### 2.2. Giả định về audio thuyết minh

* Audio thuyết minh là kênh âm thanh chính của video thành phẩm.
* Audio có thể là tiếng Việt ở giai đoạn hiện tại.
* Hệ thống cần chuyển audio thành transcript có timestamp.
* Người dùng nên được phép sửa transcript nếu ASR nhận sai tên riêng, địa danh hoặc thuật ngữ.

### 2.3. Giới hạn của hệ thống

Hệ thống không đảm bảo mọi đoạn hình đều khớp tuyệt đối với lời thuyết minh. Thay vào đó, hệ thống cố gắng:

* Chọn cảnh có liên quan nhất trong video nguồn
* Ưu tiên cảnh có chất lượng hình ảnh tốt
* Căn thời lượng cảnh với audio
* Hạn chế lặp cảnh quá gần nhau
* Đánh dấu các đoạn hệ thống không chắc chắn
* Cho phép người dùng chỉnh lại các đoạn chưa hợp

---

## 3. Định hướng thiết kế tổng thể

Hệ thống nên được thiết kế theo dạng pipeline nhiều module, trong đó mỗi module có input/output rõ ràng.

Pipeline tổng thể:

```text
Input:
- Video nguồn V1, V2, ..., Vn
- Audio thuyết minh A

Pipeline:
1. Chuẩn hóa dữ liệu đầu vào
2. Phân tích audio
3. Phân tích video nguồn
4. Trích đặc trưng và đánh chỉ mục video
5. So khớp audio segment với top-k clip phù hợp
6. Lập timeline dựng video
7. UI review và chỉnh sửa bán tự động
8. Render video hoàn chỉnh

Output:
- Video hoàn chỉnh
- Timeline JSON
- Danh sách candidate clips cho từng audio segment
- Báo cáo chất lượng / confidence
```

Điểm trung tâm của thiết kế là `timeline JSON`.

`timeline JSON` đóng vai trò như hợp đồng dữ liệu giữa các phần:

* Matching Engine đề xuất clip
* Timeline Planner quyết định cách sắp xếp clip
* UI cho người dùng xem và chỉnh sửa
* Renderer đọc timeline để xuất video cuối

Nhờ có `timeline JSON`, hệ thống không cần chạy lại toàn bộ pipeline mỗi khi người dùng chỉnh một đoạn nhỏ.

Ví dụ:

```text
Người dùng đổi clip ở đoạn 10-15 giây
→ UI cập nhật timeline JSON
→ Renderer render lại video
→ Không cần chạy lại ASR, scene detection, embedding hoặc matching
```

---

## 4. Kiến trúc module độc lập

Không nên thiết kế theo kiểu giai đoạn 1 làm xong hoàn toàn mới đến giai đoạn 2. Thay vào đó, nên chia hệ thống thành các module tương đối độc lập để nhiều thành viên có thể phát triển song song.

| Module            | Vai trò                                       | Có thể phát triển song song không? |
| ----------------- | --------------------------------------------- | ---------------------------------- |
| Input Processor   | Chuẩn hóa video/audio, lấy metadata           | Có                                 |
| Audio Analyzer    | ASR, transcript, timestamp, audio segment     | Có                                 |
| Video Analyzer    | Scene detection, keyframe, quality score      | Có                                 |
| Embedding Indexer | Tạo embedding và index cho clip/keyframe      | Có, nếu có dữ liệu mẫu             |
| Matching Engine   | Tìm top-k clip phù hợp cho từng audio segment | Có, nếu thống nhất schema          |
| Timeline Planner  | Lập timeline, xử lý duration, speed, fallback | Có thể làm với dữ liệu giả         |
| Review UI         | Cho người dùng xem, đổi clip, chỉnh tham số   | Có thể làm với timeline mẫu        |
| Renderer          | Render video cuối từ timeline JSON            | Có thể làm với timeline mẫu        |
| Evaluation        | Tính metric và báo cáo chất lượng             | Có thể làm sau                     |

Cách làm này giúp nhóm giảm phụ thuộc lẫn nhau.

Ví dụ:

* Người làm UI có thể dùng `timeline_sample.json`.
* Người làm renderer có thể dùng timeline giả để test FFmpeg.
* Người làm matching có thể xuất `matching_candidates.json`.
* Người làm audio và video có thể xử lý hai nhánh độc lập trước khi ghép lại.

---

## 5. Giai đoạn 1 — Chuẩn hóa dữ liệu đầu vào

### 5.1. Mục tiêu

Đưa video và audio về định dạng thống nhất để các bước sau xử lý ổn định.

Ví dụ chuẩn hóa:

* Video: `.mp4`, H.264, 1080p, 30fps
* Audio: `.wav` hoặc `.mp3`, sample rate thống nhất
* Metadata: duration, fps, resolution, bitrate

### 5.2. Quy trình

```text
Input video/audio
→ kiểm tra định dạng
→ chuẩn hóa resolution/fps nếu cần
→ trích metadata
→ lưu vào cấu trúc thư mục chuẩn
```

### 5.3. Output đề xuất

```json
{
  "media_id": "video_01",
  "path": "videos/normalized/video_01.mp4",
  "duration": 125.4,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "has_audio": true
}
```

Module này có thể phát triển sớm vì các module khác chỉ cần thống nhất format metadata là có thể dùng dữ liệu giả để test.

---

## 6. Giai đoạn 2 — Phân tích audio thuyết minh

### 6.1. Mục tiêu

Biến audio thành transcript có timestamp và chia thành các audio segment có ý nghĩa.

```text
Audio
→ transcript
→ timestamp
→ chia segment
→ sinh query tìm video
```

### 6.2. Output đề xuất

```json
[
  {
    "segment_id": "a001",
    "start": 0.0,
    "end": 5.2,
    "text": "Đây là khu vực cổng chính của khu tham quan.",
    "query": "main entrance of tourist area"
  },
  {
    "segment_id": "a002",
    "start": 5.2,
    "end": 10.8,
    "text": "Sau đó, đoàn di chuyển vào khu trưng bày.",
    "query": "people walking into exhibition area"
  }
]
```

### 6.3. Cách chia segment

Không nên chia quá nhỏ theo từng câu ngắn nếu câu đó không đủ ý nghĩa để chọn hình.

Nên chia theo:

* Ý nghĩa hoàn chỉnh
* Nhịp ngắt tự nhiên của voice-over
* Thời lượng đủ để dựng hình

Gợi ý:

| Loại segment     | Thời lượng gợi ý |
| ---------------- | ---------------- |
| Câu ngắn         | 3-5 giây         |
| Một ý hoàn chỉnh | 5-10 giây        |
| Đoạn mô tả dài   | 8-15 giây        |

### 6.4. Vì sao cần cho sửa transcript?

ASR có thể nhận sai:

* Tên riêng
* Địa danh
* Thuật ngữ chuyên ngành
* Từ tiếng Anh lẫn trong tiếng Việt

Nếu transcript sai, query sai. Nếu query sai, matching sẽ chọn sai clip. Vì vậy, sửa transcript là bước rẻ hơn nhiều so với sửa video sau cùng.

---

## 7. Giai đoạn 3 — Phân tích video nguồn

### 7.1. Mục tiêu

Từ video nguồn, tách ra danh sách clip candidate có thể dùng để dựng.

```text
Video nguồn
→ phát hiện scene/shot
→ tạo clip candidate
→ trích keyframe
→ tính quality score
```

### 7.2. Metadata mỗi clip

```json
{
  "clip_id": "v01_c003",
  "video_id": "video_01",
  "start": 24.5,
  "end": 31.2,
  "duration": 6.7,
  "keyframes": [
    "keyframes/v01_c003_01.jpg",
    "keyframes/v01_c003_02.jpg"
  ],
  "quality": {
    "blur_score": 0.83,
    "brightness": 0.71,
    "motion": 0.45,
    "quality_score": 0.78
  }
}
```

### 7.3. Quy tắc xử lý

* Bỏ clip quá ngắn, ví dụ dưới 1.5 giây.
* Clip quá dài, ví dụ trên 15-20 giây, nên chia nhỏ thêm.
* Không nhất thiết render vật lý từng clip ngay từ đầu.
* Nên lưu `video_id`, `start`, `end` để renderer cắt từ video gốc.
* Mỗi clip nên có nhiều keyframe, không chỉ một keyframe duy nhất.

### 7.4. Lưu ý quan trọng

Nếu chỉ dùng một keyframe đại diện cho cả clip thì kết quả matching có thể sai, vì keyframe đó chưa chắc thể hiện đúng nội dung của toàn bộ clip.

Nên ưu tiên:

* Lấy nhiều keyframe theo thời gian
* Lấy keyframe ở đầu, giữa, cuối clip
* Nếu có thể, lấy thêm thông tin chuyển động hoặc caption ngắn cho clip

---

## 8. Giai đoạn 4 — Trích đặc trưng và đánh chỉ mục video

### 8.1. Mục tiêu

Biến clip/keyframe thành vector để có thể tìm kiếm theo nghĩa.

Ý tưởng cơ bản:

```text
Audio segment text/query → text embedding
Video keyframe/clip → image embedding
So sánh vector → tìm clip gần nghĩa nhất
```

### 8.2. Hướng MVP

MVP có thể dùng hướng đơn giản:

```text
Transcript tiếng Việt
→ rút keyword hoặc mô tả ngắn
→ chuẩn hóa/dịch sang English query nếu cần
→ tạo text embedding
→ so với image embedding của keyframe
```

### 8.3. Giới hạn cần ghi rõ

Matching bằng text-image embedding là baseline hợp lý, nhưng có giới hạn:

* Keyframe không hiểu đầy đủ hành động kéo dài trong clip.
* CLIP/image embedding thường mạnh với vật thể/bối cảnh, nhưng yếu hơn với hành động phức tạp.
* Dịch tiếng Việt sang tiếng Anh có thể mất nghĩa.
* Câu trừu tượng như “chuyến đi để lại nhiều cảm xúc” rất khó tìm cảnh chính xác.
* Clip top 1 theo embedding chưa chắc là clip người dùng thấy hay nhất.

Vì vậy, hệ thống cần kết hợp nhiều điểm số khác nhau, không chỉ dựa vào semantic score.

### 8.4. Output đề xuất

```json
{
  "clip_id": "v01_c003",
  "embedding_id": "emb_v01_c003",
  "keyframe_embeddings": [
    "emb_v01_c003_01",
    "emb_v01_c003_02"
  ],
  "index_status": "ready"
}
```

---

## 9. Giai đoạn 5 — So khớp audio segment với top-k clip

### 9.1. Mục tiêu

Với mỗi audio segment, hệ thống trả về danh sách top-k clip phù hợp thay vì chỉ chọn một clip duy nhất.

Mặc định hệ thống chọn clip tốt nhất, nhưng người dùng có thể chọn clip khác trong top-k nếu clip mặc định chưa hợp.

Đây là điểm quan trọng giúp hệ thống thực tế hơn.

### 9.2. Vì sao cần top-k?

Clip có điểm cao nhất theo hệ thống chưa chắc là clip tốt nhất theo cảm nhận người dùng.

Ví dụ:

* Clip top 1 đúng nghĩa nhưng góc quay xấu.
* Clip top 2 hơi kém điểm hơn nhưng đẹp hơn.
* Clip top 3 có cảm xúc tốt hơn.
* Clip top 1 đã bị dùng gần đó, dễ gây lặp.
* Với câu trừu tượng, nhiều clip đều có thể chấp nhận được.

### 9.3. Hàm điểm đề xuất

```text
score = 0.45 * semantic_score
      + 0.20 * visual_quality_score
      + 0.15 * duration_fit_score
      + 0.10 * continuity_score
      + 0.10 * diversity_score
      - repetition_penalty
      - bad_clip_penalty
```

Ý nghĩa:

| Thành phần           | Ý nghĩa                                    |
| -------------------- | ------------------------------------------ |
| Semantic Score       | Clip có đúng nội dung đang nói không       |
| Visual Quality Score | Hình có nét, sáng, ít rung không           |
| Duration Fit Score   | Clip có đủ dài hoặc dễ căn với audio không |
| Continuity Score     | Clip có nối mượt với đoạn trước/sau không  |
| Diversity Score      | Có giúp video đa dạng cảnh hơn không       |
| Repetition Penalty   | Phạt nếu clip/cảnh bị dùng lại quá gần     |
| Bad Clip Penalty     | Phạt clip quá tối, mờ, rung hoặc lỗi       |

### 9.4. Output top-k candidate

```json
{
  "audio_segment_id": "a003",
  "selected_clip_id": "v02_c008",
  "candidates": [
    {
      "rank": 1,
      "clip_id": "v02_c008",
      "final_score": 0.84,
      "semantic_score": 0.88,
      "quality_score": 0.80,
      "duration_fit_score": 0.76,
      "reason": "Khớp nội dung tốt, chất lượng hình ổn, đủ thời lượng."
    },
    {
      "rank": 2,
      "clip_id": "v01_c004",
      "final_score": 0.79,
      "semantic_score": 0.81,
      "quality_score": 0.86,
      "duration_fit_score": 0.70,
      "reason": "Hình đẹp hơn nhưng khớp nghĩa thấp hơn một chút."
    }
  ]
}
```

### 9.5. Lưu ý về reason

Ở MVP, `reason` có thể là mô tả đơn giản dựa trên điểm số, không cần quá thông minh.

Ví dụ:

* “Khớp nội dung tốt, chất lượng hình cao.”
* “Chất lượng hình tốt nhưng thời lượng hơi ngắn.”
* “Confidence thấp, nên kiểm tra lại.”

---

## 10. Giai đoạn 6 — Lập timeline dựng video

### 10.1. Mục tiêu

Tạo timeline dựng cuối cùng từ audio segment và clip đã chọn.

Timeline phải đảm bảo:

* Có hình ảnh cho toàn bộ audio
* Cảnh phù hợp nhất có thể với nội dung lời nói
* Thời lượng hình khớp với thời lượng audio
* Nhịp dựng tự nhiên
* Hạn chế lặp cảnh
* Có fallback khi thiếu clip phù hợp

### 10.2. Không nên khóa cứng 1 segment = 1 clip

Trong bản thiết kế ban đầu, mỗi audio segment thường gắn với một clip. Cách này đơn giản nhưng chưa đủ linh hoạt.

Thực tế có thể xảy ra:

* Một audio segment dài cần nhiều clip ngắn.
* Một clip dài có thể được dùng cho một segment nhưng chỉ lấy một phần.
* Một đoạn thuyết minh trừu tượng cần cảnh B-roll thay thế.
* Một cảnh có thể kéo dài qua nhiều câu nếu nội dung liên tục.

Vì vậy, timeline nên hỗ trợ:

```text
1 audio segment → 1 hoặc nhiều visual items
```

### 10.3. Timeline JSON đề xuất

```json
[
  {
    "segment_id": "a001",
    "audio_start": 0.0,
    "audio_end": 10.0,
    "text": "Đầu tiên, chúng ta bước vào khu vực trưng bày chính.",
    "confidence": "high",
    "score": 0.82,
    "visual_items": [
      {
        "clip_id": "v01_c003",
        "video_source": "video_01.mp4",
        "clip_start": 34.5,
        "clip_end": 39.5,
        "speed": 1.0,
        "transition": "cut",
        "effect": null
      },
      {
        "clip_id": "v02_c008",
        "video_source": "video_02.mp4",
        "clip_start": 12.0,
        "clip_end": 17.0,
        "speed": 1.0,
        "transition": "fade",
        "effect": null
      }
    ],
    "candidates_ref": "candidates_a001"
  }
]
```

Cấu trúc này linh hoạt hơn vì một audio segment có thể dùng nhiều cảnh.

### 10.4. Trường hợp clip dài hơn audio segment

Ví dụ:

```text
Audio cần: 5 giây
Clip có: 12 giây
```

Cách xử lý:

* Cắt lấy đoạn phù hợp nhất.
* Nếu chưa có phân tích chi tiết, ưu tiên đoạn giữa clip.
* Nếu có quality/motion theo thời gian, chọn đoạn ổn định nhất.
* Tránh lấy đoạn đầu/cuối nếu thường chứa chuyển động máy hoặc cảnh chưa ổn định.

### 10.5. Trường hợp clip ngắn hơn audio segment

Ví dụ:

```text
Audio cần: 10 giây
Clip có: 4 giây
```

Cách xử lý theo thứ tự ưu tiên:

1. Ghép thêm clip khác cùng chủ đề.
2. Dùng thêm clip trong top-k candidate.
3. Làm chậm nhẹ nếu clip đủ đẹp.
4. Dùng B-roll/fallback clip.
5. Giữ frame cuối rất ngắn nếu thật sự cần.

Không nên kéo chậm quá mạnh. Gợi ý speed nên nằm trong khoảng:

```text
0.75x - 1.25x
```

### 10.6. Trường hợp không có clip khớp nghĩa

Cách xử lý:

* Dùng cảnh toàn / establishing shot
* Dùng cảnh môi trường
* Dùng cảnh người tham quan / người nghe / hoạt động chung
* Dùng cảnh đẹp nhất có liên quan gần
* Đánh dấu confidence thấp

Đây là điểm quan trọng vì hệ thống không thể tạo ra cảnh không có trong video nguồn.

---

## 11. Giai đoạn 7 — UI review và chỉnh sửa bán tự động

### 11.1. Mục tiêu

UI giúp người dùng kiểm tra và tinh chỉnh bản dựng mà không cần chuyển sang phần mềm hậu kỳ khác cho các chỉnh sửa cơ bản.

Tuy nhiên, UI không nên phức tạp như Premiere, CapCut hay DaVinci Resolve.

Tư tưởng thiết kế nên là:

> Timeline đơn giản + preview từng đoạn + chỉnh những tham số quan trọng nhất.

### 11.2. Chức năng UI bắt buộc cho MVP

#### 1. Xem timeline theo audio segment

Mỗi dòng tương ứng một audio segment:

| Time  | Transcript       | Clip chọn | Score | Confidence | Action       |
| ----- | ---------------- | --------- | ----- | ---------- | ------------ |
| 0-6s  | Cổng chính...    | v01_c003  | 0.82  | Cao        | Xem / Đổi    |
| 6-12s | Khu trưng bày... | v02_c008  | 0.54  | Thấp       | Cần kiểm tra |

#### 2. Xem preview đoạn đang chọn

Người dùng cần xem được:

* Transcript của đoạn audio
* Clip đang được chọn
* Preview hình/video ngắn
* Confidence
* Lý do đề xuất ngắn gọn

#### 3. Chọn clip khác trong top-k

Khi bấm vào một segment, UI hiển thị:

* Clip hiện tại
* Danh sách top-k clip thay thế
* Thumbnail hoặc preview ngắn
* Score từng clip
* Nút chọn clip

Hành vi:

```text
Nếu người dùng không chỉnh
→ dùng clip rank 1

Nếu người dùng chọn clip khác
→ cập nhật timeline JSON
→ preview lại đoạn tương ứng
→ render lại khi cần
```

#### 4. Highlight đoạn confidence thấp

Các đoạn có confidence thấp nên được đánh dấu rõ để người dùng ưu tiên kiểm tra.

Ví dụ:

```text
High confidence: có thể bỏ qua nếu muốn
Medium confidence: nên xem lại
Low confidence: cần kiểm tra
```

### 11.3. Chức năng UI nên có nếu còn thời gian

Các chức năng sau hữu ích nhưng không nên là trọng tâm đầu tiên:

* Chỉnh speed bằng preset: 0.75x, 1.0x, 1.25x
* Chọn transition cơ bản: cut, fade, crossfade
* Chọn crop/fit: fit, fill, center crop, blur background
* Bật/tắt audio gốc của video
* Giảm âm lượng audio gốc

### 11.4. Chức năng chưa nên làm trong MVP

Không nên làm quá nhiều hiệu ứng nâng cao ở MVP, ví dụ:

* Bộ hiệu ứng phong phú như app dựng video chuyên nghiệp
* Keyframe animation phức tạp
* Color grading
* Multi-track timeline đầy đủ
* Chỉnh sửa audio chi tiết
* Template motion graphic nâng cao

Các chức năng này dễ làm hệ thống phình to và khó hoàn thành đúng hạn.

### 11.5. Output sau khi người dùng chỉnh

UI không sửa trực tiếp video. UI chỉ cập nhật `timeline JSON`.

Ví dụ:

```json
{
  "segment_id": "a003",
  "visual_items": [
    {
      "clip_id": "v01_c004",
      "clip_start": 20.0,
      "clip_end": 25.0,
      "speed": 1.1,
      "transition": "fade",
      "effect": null
    }
  ]
}
```

Renderer sẽ đọc timeline mới để xuất video.

---

## 12. Giai đoạn 8 — Render video hoàn chỉnh

### 12.1. Mục tiêu

Từ `timeline JSON`, video nguồn và audio thuyết minh, render ra video cuối cùng.

```text
Timeline JSON
+ Video nguồn
+ Audio thuyết minh
→ Final video .mp4
```

### 12.2. Renderer cần hỗ trợ

* Cắt clip theo `clip_start`, `clip_end`
* Chỉnh speed
* Scale/crop về đúng resolution
* Thêm transition cơ bản
* Ghép voice-over làm audio chính
* Tắt hoặc giảm âm lượng audio gốc
* Xuất video cuối dạng `.mp4`

### 12.3. Nguyên tắc quan trọng

Không nên render lại toàn bộ pipeline khi người dùng chỉ sửa timeline.

Luồng đúng:

```text
Người dùng sửa timeline
→ cập nhật timeline JSON
→ render lại video
```

Không cần chạy lại:

* ASR
* Scene detection
* Embedding
* Matching

Trừ khi người dùng thay đổi input hoặc yêu cầu phân tích lại.

---

## 13. Thiết kế dữ liệu trung gian

### 13.1. `audio_segments.json`

```json
[
  {
    "segment_id": "a001",
    "start": 0.0,
    "end": 5.2,
    "text": "Đây là khu vực cổng chính.",
    "query": "main entrance"
  }
]
```

### 13.2. `clip_metadata.json`

```json
[
  {
    "clip_id": "v01_c001",
    "video_id": "video_01",
    "start": 10.2,
    "end": 17.5,
    "duration": 7.3,
    "keyframes": ["v01_c001_01.jpg", "v01_c001_02.jpg"],
    "quality_score": 0.81
  }
]
```

### 13.3. `matching_candidates.json`

```json
[
  {
    "audio_segment_id": "a001",
    "selected_clip_id": "v01_c001",
    "candidates": [
      {
        "clip_id": "v01_c001",
        "rank": 1,
        "score": 0.84
      },
      {
        "clip_id": "v02_c004",
        "rank": 2,
        "score": 0.78
      }
    ]
  }
]
```

### 13.4. `timeline.json`

```json
[
  {
    "segment_id": "a001",
    "audio_start": 0.0,
    "audio_end": 5.2,
    "text": "Đây là khu vực cổng chính.",
    "confidence": "high",
    "visual_items": [
      {
        "clip_id": "v01_c001",
        "video_source": "video_01.mp4",
        "clip_start": 10.2,
        "clip_end": 15.4,
        "speed": 1.0,
        "transition": "cut",
        "effect": null
      }
    ],
    "candidates_ref": "candidates_a001"
  }
]
```

Các file này là hợp đồng dữ liệu giữa các module. Khi đã thống nhất schema, các thành viên có thể làm song song dễ hơn.

---

## 14. Kiến trúc hệ thống đề xuất

```text
                                      ┌────────────────────┐
                                      │   Video sources    │
                                      └─────────┬──────────┘
                                                │
                                                v
                                      ┌────────────────────┐
                                      │  Video Analyzer    │
                                      │ scene/keyframe/meta│
                                      └─────────┬──────────┘
                                                │
                                                v
                                      ┌────────────────────┐
                                      │ Clip Metadata +    │
                                      │ Visual Embeddings  │
                                      └─────────┬──────────┘
                                                │
                ┌────────────────────┐          │
                │   Voice-over Audio │          │
                └─────────┬──────────┘          │
                          │                     │
                          v                     │
                ┌────────────────────┐          │
                │   Audio Analyzer   │          │
                │ ASR/segment/query  │          │
                └─────────┬──────────┘          │
                          │                     │
                          v                     │
                ┌────────────────────┐          │
                │  Audio Segments    │          │
                └─────────┬──────────┘          │
                          │                     v
                          │   ┌────────────────────────────────┐
                          └──>│        Matching Engine         │
                              │  top-k retrieval + reranking   │
                              └───────────────┬────────────────┘
                                              v
                              ┌────────────────────────────────┐
                              │        Timeline Planner        │
                              │ duration/speed/fallback logic  │
                              └───────────────┬────────────────┘
                                              v
                              ┌────────────────────────────────┐
                              │          Review UI             │
                              │ choose top-k / edit timeline   │
                              └───────────────┬────────────────┘
                                              v
                              ┌────────────────────────────────┐
                              │            Renderer            │
                              │       export final video       │
                              └────────────────────────────────┘
```

---

## 15. Phân công nhóm 5 người

### Người 1 — Leader / System Integration / Timeline Contract

Phụ trách:

* Thiết kế kiến trúc tổng thể
* Thống nhất schema JSON
* Quản lý luồng dữ liệu
* Tích hợp các module
* Đảm bảo demo end-to-end chạy được
* Phối hợp với renderer để đảm bảo timeline đúng

Kết quả cần giao:

* Cấu trúc project
* Schema dữ liệu chung
* Pipeline chạy từ input đến timeline/render
* Dữ liệu mẫu cho các module khác test

---

### Người 2 — Audio / NLP

Phụ trách:

* ASR bằng Whisper/faster-whisper/WhisperX
* Tạo transcript có timestamp
* Chia audio thành segment
* Sinh query cho từng segment
* Cho phép sửa transcript nếu cần

Kết quả cần giao:

```json
[
  {
    "segment_id": "a001",
    "start": 0.0,
    "end": 5.2,
    "text": "...",
    "query": "..."
  }
]
```

---

### Người 3 — Video Preprocessing / Computer Vision

Phụ trách:

* Chuẩn hóa video
* Scene detection
* Tạo clip candidate
* Trích nhiều keyframe cho mỗi clip
* Tính quality score

Kết quả cần giao:

```json
[
  {
    "clip_id": "v01_c001",
    "video_id": "video_01",
    "start": 10.2,
    "end": 17.5,
    "keyframes": ["..."],
    "quality_score": 0.81
  }
]
```

---

### Người 4 — Matching / Retrieval

Phụ trách:

* Tạo embedding cho text và keyframe
* Xây index tìm kiếm
* Trả về top-k clip cho từng audio segment
* Rerank bằng score tổng hợp
* Gán confidence cho kết quả matching

Kết quả cần giao:

```json
{
  "audio_segment_id": "a003",
  "selected_clip_id": "v02_c008",
  "confidence": "high",
  "candidates": [
    {
      "rank": 1,
      "clip_id": "v02_c008",
      "score": 0.84
    },
    {
      "rank": 2,
      "clip_id": "v01_c004",
      "score": 0.76
    }
  ]
}
```

---

### Người 5 — UI Review / Renderer

Phụ trách:

* Xây UI review timeline
* Hiển thị transcript, clip được chọn, confidence
* Cho phép chọn clip khác trong top-k
* Cập nhật timeline JSON sau khi người dùng chỉnh
* Render video cuối từ timeline JSON

Kết quả cần giao:

* UI review cơ bản
* Chức năng đổi clip
* Chức năng render video cuối
* `final_video.mp4`

Lưu ý: phần Timeline Planner nên có sự hỗ trợ từ Leader để tránh Người 5 bị quá tải.

---

## 16. Các phần có thể phát triển song song

### 16.1. Có thể làm song song ngay từ đầu

| Phần              | Điều kiện             |
| ----------------- | --------------------- |
| Audio Analyzer    | Có file audio mẫu     |
| Video Analyzer    | Có video mẫu          |
| UI Review         | Có timeline JSON mẫu  |
| Renderer          | Có timeline JSON mẫu  |
| Schema thiết kế   | Làm ngay từ đầu       |
| Evaluation metric | Có timeline/video mẫu |

### 16.2. Phụ thuộc một phần

| Phần              | Phụ thuộc                          |
| ----------------- | ---------------------------------- |
| Embedding Indexer | Cần keyframe từ Video Analyzer     |
| Matching Engine   | Cần audio segment và clip metadata |
| Timeline Planner  | Cần output từ Matching Engine      |
| UI hoàn chỉnh     | Cần timeline và candidate schema   |

### 16.3. Cách giảm phụ thuộc

Nên tạo dữ liệu mẫu sớm:

* `audio_segments_sample.json`
* `clip_metadata_sample.json`
* `matching_candidates_sample.json`
* `timeline_sample.json`

Nhờ đó, các thành viên có thể phát triển module của mình mà không cần chờ module khác hoàn thành hoàn toàn.

---

## 17. Rủi ro và cách giảm

| Rủi ro                                   | Ảnh hưởng             | Cách giảm                            |
| ---------------------------------------- | --------------------- | ------------------------------------ |
| ASR nhận sai transcript                  | Matching sai          | Cho người dùng sửa transcript        |
| Video nguồn thiếu cảnh phù hợp           | Video sai nghĩa       | Dùng fallback + confidence thấp      |
| Clip top 1 không hợp cảm nhận người dùng | Video chưa tốt        | Cho chọn clip trong top-k            |
| Scene detection cắt sai                  | Clip candidate xấu    | Lọc clip quá ngắn, chia clip quá dài |
| Keyframe không đại diện đúng clip        | Matching sai          | Dùng nhiều keyframe mỗi clip         |
| CLIP hiểu sai tiếng Việt                 | Chọn sai hình         | Chuẩn hóa query, dịch nếu cần        |
| Video cuối bị lặp cảnh                   | Thiếu tự nhiên        | Thêm repetition penalty              |
| Speed chỉnh quá mạnh                     | Video bị giả          | Giới hạn speed 0.75x-1.25x           |
| UI quá phức tạp                          | Không kịp hoàn thành  | Chỉ làm review + đổi clip cho MVP    |
| Render lỗi codec                         | Không xuất được video | Chuẩn hóa video từ đầu               |
| Nhóm khó tích hợp                        | Trễ tiến độ           | Thống nhất JSON schema sớm           |

---

## 18. Bộ tiêu chí đánh giá

### 18.1. Định lượng

| Metric                 | Ý nghĩa                             |
| ---------------------- | ----------------------------------- |
| Segment coverage       | Tỉ lệ audio segment được gán hình   |
| Average semantic score | Điểm khớp nghĩa trung bình          |
| Low-confidence rate    | Tỉ lệ đoạn hệ thống không chắc      |
| Repetition rate        | Tỉ lệ clip/cảnh bị dùng lặp         |
| Duration error         | Sai lệch thời lượng audio/video     |
| Processing time        | Thời gian xử lý pipeline            |
| Render time            | Thời gian xuất video                |
| User edit count        | Người dùng phải chỉnh bao nhiêu lần |

### 18.2. Định tính

Cho người xem hoặc người dùng chấm 1-5:

| Tiêu chí           | Câu hỏi đánh giá                       |
| ------------------ | -------------------------------------- |
| Semantic alignment | Hình có liên quan đến lời nói không?   |
| Visual quality     | Hình có rõ, sáng, dễ xem không?        |
| Editing rhythm     | Nhịp cắt có tự nhiên không?            |
| Ease of editing    | UI chỉnh sửa có dễ dùng không?         |
| Final usefulness   | Video cuối có đủ tốt để sử dụng không? |

---

## 19. MVP nên làm đến đâu?

MVP nên tập trung vào một luồng end-to-end chạy ổn định thay vì cố làm nhiều chức năng nâng cao.

### 19.1. MVP bắt buộc

```text
1. Nhận video + audio đầu vào
2. ASR tạo transcript + timestamp
3. Chia audio thành segment
4. Scene detection video nguồn
5. Trích keyframe + quality score
6. Tạo embedding cho text/keyframe
7. Tìm top-k clip cho từng audio segment
8. Mặc định chọn clip tốt nhất
9. Tạo timeline JSON
10. UI xem timeline và đổi clip trong top-k
11. Render video cuối bằng timeline JSON
```

### 19.2. MVP nếu còn thời gian

```text
12. Highlight đoạn confidence thấp
13. Chỉnh speed bằng preset
14. Chọn transition cơ bản
15. Bật/tắt hoặc giảm âm lượng audio gốc
```

### 19.3. Không nên làm trong MVP

```text
- Hiệu ứng nâng cao
- Timeline nhiều track như phần mềm dựng phim chuyên nghiệp
- Color grading
- Motion graphic/template phức tạp
- Chỉnh audio chi tiết
- Tự động tạo caption đẹp
```

Ưu tiên của MVP:

* Có pipeline chạy được từ đầu đến cuối
* Kết quả hình tương đối khớp lời thuyết minh
* Người dùng đổi được clip chưa hợp
* Render video ổn định
* Có dữ liệu trung gian rõ ràng để debug và báo cáo

---

## 20. Kết luận thiết kế nên chọn

Thiết kế phù hợp nhất là:

> Một hệ thống dựng video bán tự động, trong đó pipeline tự tạo bản dựng ban đầu từ video nguồn và audio thuyết minh, còn người dùng có thể kiểm tra, chọn clip thay thế và render lại video cuối trên UI.

Điểm cốt lõi của thiết kế:

* Không cố làm AI tự dựng hoàn hảo 100%.
* Có `timeline JSON` làm trung tâm.
* Matching trả về top-k clip thay vì chỉ top-1.
* Timeline hỗ trợ một audio segment gồm một hoặc nhiều visual items.
* UI tập trung vào review và chỉnh những lỗi quan trọng.
* Renderer chỉ đọc timeline JSON để xuất video cuối.
* Các module có input/output rõ ràng để phát triển song song.
* Hệ thống có confidence/fallback để xử lý khi video nguồn thiếu cảnh phù hợp.

Hướng này thực tế vì:

* Phù hợp với nhóm sinh viên 5 người.
* Không cần train model lớn.
* Dễ chia việc.
* Dễ debug.
* Dễ demo.
* Có khả năng mở rộng.
* Tạo ra video cuối tốt hơn nhờ có bước người dùng tinh chỉnh.

Tóm lại, đề tài nên được định vị là:

> Audio-Guided Video Montage bán tự động: hệ thống tự đề xuất bản dựng ban đầu dựa trên audio thuyết minh, sau đó cho phép người dùng kiểm tra và tinh chỉnh trên timeline đơn giản để tạo video hoàn chỉnh.
