# Phân tích thiết kế hệ thống dựng video bán tự động theo audio thuyết minh

## 1. Mục tiêu bài toán

Bài toán cần xây dựng một hệ thống giúp người dùng tạo video hoàn chỉnh từ:

- Video nguồn có sẵn
- Audio thuyết minh / voice-over có sẵn

Hệ thống không tự sinh video mới, mà sẽ trích xuất, chọn lọc, cắt ghép và căn chỉnh các đoạn hình ảnh từ video nguồn sao cho khớp với nội dung audio.

Thành phẩm mong muốn không chỉ là một video nháp, mà là một bản dựng có thể dùng được, hạn chế tối đa việc người dùng phải mang sang phần mềm hậu kỳ khác để chỉnh tiếp.

Tuy nhiên, không nên thiết kế theo hướng tự động 100%. Hướng phù hợp hơn là bán tự động:

> Hệ thống tự dựng bản đầu tiên, sau đó cho người dùng kiểm tra và tinh chỉnh trực tiếp trên giao diện.

---

## 2. Định hướng thiết kế chính

Hệ thống nên đi theo hướng pipeline nhiều module, mỗi module tạo ra dữ liệu trung gian rõ ràng.

Pipeline tổng thể:

```text
Input:
- Video nguồn V1, V2, ..., Vn
- Audio thuyết minh A

Pipeline:
1. Chuẩn hóa dữ liệu đầu vào
2. Phân tích audio
3. Phân tích và cắt video nguồn
4. Trích đặc trưng và đánh chỉ mục video
5. So khớp audio segment với top-k clip phù hợp
6. Tối ưu timeline
7. UI review và chỉnh sửa bán tự động
8. Render video hoàn chỉnh

Output:
- Video hoàn chỉnh
- Timeline JSON
- Danh sách candidate clips theo từng audio segment
- Báo cáo đánh giá chất lượng
````

Điểm quan trọng nhất là phải có `timeline JSON` làm dữ liệu trung gian.

Timeline JSON giúp:

* Dễ kiểm tra clip nào đang ghép với câu nào
* Dễ sửa từng đoạn mà không chạy lại toàn bộ pipeline
* Dễ render lại video sau khi người dùng chỉnh sửa
* Dễ phát triển UI chỉnh sửa
* Dễ chia việc cho các thành viên trong nhóm

---

## 3. Kiến trúc nên tách module độc lập

Không nên thiết kế kiểu giai đoạn 1 xong mới làm giai đoạn 2, rồi giai đoạn 2 xong mới làm giai đoạn 3.

Thay vào đó, nên tách thành các module có input/output rõ ràng để nhiều phần có thể phát triển song song.

Các module chính:

| Module            | Vai trò                                   | Có thể phát triển song song không?   |
| ----------------- | ----------------------------------------- | ------------------------------------ |
| Input Processor   | Chuẩn hóa video/audio                     | Có                                   |
| Audio Analyzer    | ASR, transcript, timestamp, audio segment | Có                                   |
| Video Analyzer    | Scene detection, keyframe, quality score  | Có                                   |
| Embedding Indexer | Tạo embedding và FAISS index              | Có, sau khi có metadata/keyframe mẫu |
| Matching Engine   | Tìm top-k clip cho từng audio segment     | Có, nếu đã thống nhất schema         |
| Timeline Planner  | Chọn clip, căn thời lượng, xử lý fallback | Có thể làm với dữ liệu giả trước     |
| Review UI         | Cho người dùng xem và chỉnh timeline      | Có thể làm với mock JSON trước       |
| Renderer          | Render video từ timeline JSON             | Có thể làm độc lập với timeline mẫu  |
| Evaluation        | Tính metric, báo cáo chất lượng           | Có thể làm sau khi có timeline mẫu   |

Thiết kế này giúp nhóm không bị phụ thuộc quá nhiều vào một luồng tuần tự.

Ví dụ:

* Người làm UI có thể dùng file `timeline_sample.json` để phát triển trước.
* Người làm render có thể dùng timeline giả để test FFmpeg.
* Người làm matching có thể xuất top-k candidate theo schema đã thống nhất.
* Người làm audio và video có thể xử lý hai nhánh song song.

---

## 4. Giai đoạn 1 — Chuẩn hóa dữ liệu đầu vào

### Mục tiêu

Đưa tất cả video và audio về định dạng thống nhất để các bước sau xử lý ổn định.

Ví dụ chuẩn hóa:

* Video: `.mp4`, H.264, 1080p, 30fps
* Audio: `.wav` hoặc `.mp3`, sample rate thống nhất
* Metadata: duration, fps, resolution, bitrate

### Việc cần làm

```text
Input video/audio
→ kiểm tra định dạng
→ chuẩn hóa resolution/fps
→ tách metadata
→ lưu vào cấu trúc thư mục chuẩn
```

### Output đề xuất

```json
{
  "media_id": "video_01",
  "path": "videos/normalized/video_01.mp4",
  "duration": 125.4,
  "fps": 30,
  "width": 1920,
  "height": 1080
}
```

### Ghi chú phát triển song song

Module này có thể làm độc lập tương đối sớm. Các module khác chỉ cần thống nhất format metadata là có thể dùng dữ liệu giả để phát triển trước.

---

## 5. Giai đoạn 2 — Phân tích audio thuyết minh

### Mục tiêu

Biến audio thành transcript có timestamp và chia thành các audio segment có ý nghĩa.

```text
Audio
→ transcript
→ timestamp
→ chia segment
→ sinh query tìm video
```

Ví dụ:

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

### Cách chia segment

Không nên chia quá nhỏ theo từng câu ngắn. Nên chia theo ý nghĩa và thời lượng.

| Loại segment     | Thời lượng gợi ý |
| ---------------- | ---------------- |
| Câu ngắn         | 3–5 giây         |
| Một ý hoàn chỉnh | 5–10 giây        |
| Đoạn mô tả dài   | 8–15 giây        |

### UI cần hỗ trợ

Người dùng nên có thể sửa transcript trước khi dựng.

Lý do:

* ASR có thể nhận sai tên riêng, địa danh, thuật ngữ.
* Transcript sai sẽ làm matching sai.
* Sửa transcript dễ hơn nhiều so với sửa video sau cùng.

### Ghi chú phát triển song song

Audio Analyzer chỉ cần xuất đúng schema `audio_segments.json`. Các module matching, timeline, UI có thể dùng file này hoặc file mẫu để phát triển độc lập.

---

## 6. Giai đoạn 3 — Phân tích và cắt video nguồn

### Mục tiêu

Từ video nguồn, tách ra danh sách clip candidate có thể dùng để dựng.

```text
Video nguồn
→ phát hiện scene/shot
→ tạo clip candidate
→ trích keyframe
→ tính quality score
```

### Metadata mỗi clip

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

### Quy tắc xử lý

* Bỏ clip quá ngắn dưới khoảng 1.5 giây.
* Clip quá dài trên 15–20 giây nên chia nhỏ thêm.
* Không nhất thiết render vật lý từng clip ngay từ đầu.
* Nên lưu `video_id`, `start`, `end` trong metadata để render cuối.

### Ghi chú phát triển song song

Video Analyzer có thể chạy song song với Audio Analyzer. Hai nhánh này chỉ gặp nhau ở Matching Engine.

---

## 7. Giai đoạn 4 — Trích đặc trưng và đánh chỉ mục video

### Mục tiêu

Biến keyframe/clip thành vector để có thể tìm kiếm theo nghĩa.

Ý tưởng:

```text
Audio segment text/query → text embedding
Video keyframe/clip → image embedding
So sánh vector → tìm clip gần nghĩa nhất
```

### Hướng MVP

Nên dùng hướng đơn giản:

```text
Transcript tiếng Việt
→ rút keyword hoặc mô tả ngắn
→ dịch/chuẩn hóa sang English query
→ tạo text embedding
→ so với image embedding của keyframe
```

### Output đề xuất

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

### Ghi chú phát triển song song

Module này phụ thuộc vào keyframe từ Video Analyzer, nhưng có thể phát triển trước bằng một tập keyframe mẫu.

---

## 8. Giai đoạn 5 — So khớp audio segment với top-k clip

### Mục tiêu

Với mỗi audio segment, hệ thống không chỉ chọn một clip duy nhất, mà trả về danh sách top-k clip phù hợp.

Mặc định hệ thống vẫn chọn clip tốt nhất, nhưng người dùng có thể mở danh sách top-k để thay thế nếu clip mặc định chưa hợp.

Đây là thay đổi quan trọng so với thiết kế tự động hoàn toàn.

### Vì sao cần top-k?

Vì clip có điểm cao nhất theo hệ thống chưa chắc là clip người dùng thích nhất.

Ví dụ:

* Clip top 1 đúng nghĩa nhưng góc quay xấu.
* Clip top 2 hơi kém điểm hơn nhưng đẹp hơn.
* Clip top 3 có cảm xúc tốt hơn, hợp với video hơn.
* Clip top 1 đã bị dùng gần đó, người dùng muốn tránh lặp.
* Với câu trừu tượng, nhiều clip đều có thể chấp nhận được.

### Hàm điểm đề xuất

```text
score = 0.50 * semantic_score
      + 0.20 * visual_quality_score
      + 0.15 * duration_fit_score
      + 0.10 * continuity_score
      + 0.05 * diversity_score
      - repetition_penalty
      - bad_clip_penalty
```

### Ý nghĩa các thành phần

| Thành phần           | Ý nghĩa                                   |
| -------------------- | ----------------------------------------- |
| Semantic Score       | Clip có đúng nội dung đang nói không      |
| Visual Quality Score | Hình có nét, sáng, ít rung không          |
| Duration Fit Score   | Clip có đủ dài cho audio segment không    |
| Continuity Score     | Clip có nối mượt với đoạn trước/sau không |
| Diversity Score      | Có giúp video đa dạng cảnh hơn không      |
| Repetition Penalty   | Phạt nếu clip bị dùng lại quá gần         |
| Bad Clip Penalty     | Phạt clip quá tối, mờ, rung hoặc lỗi      |

### Output top-k candidate

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
    },
    {
      "rank": 3,
      "clip_id": "v03_c011",
      "final_score": 0.72,
      "semantic_score": 0.74,
      "quality_score": 0.82,
      "duration_fit_score": 0.68,
      "reason": "Có thể dùng làm cảnh thay thế hoặc B-roll."
    }
  ]
}
```

### UI cần hỗ trợ ở giai đoạn này

Trong giao diện review, mỗi audio segment nên hiển thị:

* Transcript của đoạn audio
* Clip đang được chọn mặc định
* Score/confidence
* Danh sách top-k clip thay thế
* Preview nhanh từng clip
* Nút chọn clip khác
* Lý do hệ thống đề xuất clip đó

Hành vi mặc định:

```text
Nếu người dùng không chỉnh:
→ dùng clip rank 1

Nếu người dùng chọn clip khác trong top-k:
→ cập nhật selected_clip_id trong timeline
→ preview lại đoạn tương ứng
→ render lại khi cần
```

### Ghi chú phát triển song song

Matching Engine có thể được phát triển độc lập nếu đã có:

* `audio_segments.json`
* `clip_metadata.json`
* `embedding_index`

UI cũng có thể phát triển trước bằng file `matching_candidates_sample.json`.

---

## 9. Giai đoạn 6 — Tối ưu timeline

### Mục tiêu

Tạo timeline dựng cuối cùng từ audio segment và clip đã chọn.

Timeline phải đảm bảo:

* Khớp nội dung
* Khớp thời lượng audio
* Nhịp dựng tự nhiên
* Hạn chế lặp cảnh
* Có fallback khi thiếu clip phù hợp

### Tình huống 1: Clip dài hơn audio segment

Ví dụ:

```text
Audio cần: 5 giây
Clip có: 12 giây
```

Cách xử lý:

* Cắt lấy đoạn đẹp nhất.
* Ưu tiên đoạn giữa clip nếu chưa có phân tích chi tiết.
* Nếu có quality/motion theo thời gian, chọn đoạn ổn định nhất.

### Tình huống 2: Clip ngắn hơn audio segment

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

Không nên kéo chậm quá mạnh. Gợi ý speed nên nằm trong khoảng 0.75x–1.25x.

### Tình huống 3: Không có clip khớp nghĩa

Cách xử lý:

* Dùng cảnh toàn
* Dùng cảnh chuyển tiếp
* Dùng cảnh người tham quan/người nghe
* Dùng cảnh môi trường
* Dùng cảnh đẹp nhất có liên quan gần

Đồng thời đánh dấu confidence thấp để người dùng kiểm tra trong UI.

### Timeline JSON đề xuất

```json
[
  {
    "segment_id": "a001",
    "audio_start": 0.0,
    "audio_end": 6.2,
    "text": "Đầu tiên, chúng ta bước vào khu vực trưng bày chính.",
    "selected_clip_id": "v01_c003",
    "video_source": "video_01.mp4",
    "clip_start": 34.5,
    "clip_end": 40.7,
    "speed": 1.0,
    "transition": "cut",
    "effect": null,
    "score": 0.82,
    "confidence": "high",
    "candidates_ref": "candidates_a001"
  }
]
```

### Ghi chú phát triển song song

Timeline Planner có thể làm việc với dữ liệu giả trước. Chỉ cần thống nhất schema timeline là Renderer và UI có thể phát triển cùng lúc.

---

## 10. Giai đoạn 7 — UI review và chỉnh sửa bán tự động

### Mục tiêu

Đây là phần giúp hệ thống không chỉ tạo video nháp, mà cho phép người dùng tinh chỉnh trực tiếp để video cuối tốt hơn.

Người dùng không cần mang video sang phần mềm chỉnh sửa khác nếu chỉ cần các thao tác cơ bản.

### Tư tưởng thiết kế UI

UI không nên quá phức tạp như Premiere hay CapCut đầy đủ.

Nên thiết kế theo hướng:

> Timeline đơn giản + preview từng đoạn + chỉnh các tham số quan trọng.

### Các chức năng UI nên có cho MVP

#### 1. Xem timeline theo audio segment

Mỗi dòng tương ứng một audio segment:

| Time  | Transcript       | Clip chọn | Score | Confidence | Action       |
| ----- | ---------------- | --------- | ----- | ---------- | ------------ |
| 0–6s  | Cổng chính...    | v01_c003  | 0.82  | Cao        | Xem / Đổi    |
| 6–12s | Khu trưng bày... | v02_c008  | 0.54  | Thấp       | Cần kiểm tra |

#### 2. Chọn clip trong top-k

Khi bấm vào một segment, UI hiển thị:

* Clip đang chọn
* Top-k clip đề xuất
* Preview thumbnail/video ngắn
* Score từng clip
* Nút chọn clip thay thế

Mặc định dùng clip tốt nhất. Người dùng chỉ can thiệp khi thấy chưa hợp.

#### 3. Chỉnh tốc độ clip

Cho phép chỉnh:

* 0.75x
* 1.0x
* 1.25x
* hoặc slider trong giới hạn an toàn

Không nên cho chỉnh quá rộng ở MVP vì dễ làm video xấu.

#### 4. Chỉnh hiệu ứng chuyển cảnh

MVP chỉ cần vài lựa chọn:

* Cut
* Fade
* Crossfade
* Dip to black nếu cần

Không nên thêm quá nhiều hiệu ứng vì dễ làm sản phẩm rối.

#### 5. Chỉnh crop/fit cơ bản

Nếu video nguồn có nhiều tỉ lệ khác nhau, UI nên cho chọn:

* Fit
* Fill/Crop
* Center crop
* Blur background cho video dọc/ngang không khớp

#### 6. Chỉnh âm thanh cơ bản

Voice-over là audio chính.

Cho phép:

* Bật/tắt audio gốc của video
* Giảm âm lượng audio gốc
* Thêm fade in/fade out cơ bản
* Giữ voice-over rõ nhất

#### 7. Đánh dấu đoạn cần sửa

Các đoạn confidence thấp nên được highlight để người dùng ưu tiên kiểm tra.

Ví dụ:

```text
High confidence: không cần xem kỹ
Medium confidence: nên xem lại
Low confidence: cần kiểm tra
```

### Output sau khi người dùng chỉnh

UI không sửa trực tiếp video. UI chỉ cập nhật timeline JSON.

Ví dụ khi người dùng đổi clip:

```json
{
  "segment_id": "a003",
  "selected_clip_id": "v01_c004",
  "speed": 1.1,
  "transition": "fade",
  "effect": "slight_zoom"
}
```

Sau đó Renderer sẽ đọc timeline JSON mới để render lại video.

### Lợi ích của UI bán tự động

* Giảm áp lực AI phải chọn đúng 100%.
* Người dùng có quyền kiểm soát.
* Dễ demo hơn vì có thể sửa lỗi trực tiếp.
* Sản phẩm cuối có chất lượng tốt hơn.
* Không cần qua ứng dụng hậu kỳ khác cho các chỉnh sửa cơ bản.

---

## 11. Giai đoạn 8 — Render video hoàn chỉnh

### Mục tiêu

Từ timeline JSON đã được hệ thống tạo và người dùng chỉnh sửa, render ra video cuối cùng.

```text
Timeline JSON
+ Video nguồn
+ Audio thuyết minh
→ Final video .mp4
```

### Renderer cần hỗ trợ

* Cắt clip theo start/end
* Chỉnh speed
* Scale/crop về đúng resolution
* Thêm transition cơ bản
* Ghép voice-over làm audio chính
* Giảm hoặc tắt audio gốc
* Xuất video cuối

### Nguyên tắc quan trọng

Không nên render lại toàn bộ pipeline khi người dùng chỉ sửa timeline.

Luồng đúng nên là:

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

## 12. Thiết kế dữ liệu trung gian

### File 1: audio_segments.json

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

### File 2: clip_metadata.json

```json
[
  {
    "clip_id": "v01_c001",
    "video_id": "video_01",
    "start": 10.2,
    "end": 17.5,
    "duration": 7.3,
    "keyframes": ["v01_c001_01.jpg"],
    "quality_score": 0.81
  }
]
```

### File 3: matching_candidates.json

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

### File 4: timeline.json

```json
[
  {
    "segment_id": "a001",
    "audio_start": 0.0,
    "audio_end": 5.2,
    "selected_clip_id": "v01_c001",
    "video_source": "video_01.mp4",
    "clip_start": 10.2,
    "clip_end": 15.4,
    "speed": 1.0,
    "transition": "cut",
    "effect": null,
    "confidence": "high"
  }
]
```

Các file này là hợp đồng dữ liệu giữa các module. Khi đã thống nhất schema, các thành viên có thể làm song song dễ hơn.

---

## 13. Kiến trúc hệ thống đề xuất

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
                          │                     │
                          │                     │
                          │                     v
                          │   ┌────────────────────────────────┐
                          │-->│        Matching Engine         │
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
                              │ choose top-k/edit speed/effect │
                              └───────────────┬────────────────┘
                                              v
                              ┌────────────────────────────────┐
                              │            Renderer            │
                              │       export final video       │
                              └────────────────────────────────┘
```

---

## 14. Phân công nhóm 5 người

### Người 1 — Leader / System Integration

Phụ trách:

* Thiết kế kiến trúc tổng thể
* Thống nhất schema JSON
* Tích hợp các module
* Quản lý luồng dữ liệu
* Đảm bảo demo end-to-end chạy được

Kết quả cần giao:

* Cấu trúc project
* Schema dữ liệu chung
* Pipeline chạy từ input đến timeline/render

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
* Trích keyframe
* Tính quality score

Kết quả cần giao:

```json
[
  {
    "clip_id": "v01_c001",
    "start": 10.2,
    "end": 17.5,
    "keyframes": [...],
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
* Giải thích lý do chọn clip

Kết quả cần giao:

```json
{
  "audio_segment_id": "a003",
  "selected_clip_id": "v02_c008",
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

### Người 5 — Timeline / Renderer / UI

Phụ trách:

* Tạo timeline JSON
* Căn thời lượng clip với audio
* Xử lý speed, transition, fallback
* Xây UI review/chỉnh sửa cơ bản
* Render video cuối

Kết quả cần giao:

* `timeline.json`
* UI review timeline
* Chức năng chọn clip trong top-k
* Chức năng chỉnh speed/effect cơ bản
* `final_video.mp4`

---

## 15. Các phần có thể phát triển song song

### Có thể làm song song ngay từ đầu

| Phần              | Điều kiện             |
| ----------------- | --------------------- |
| Audio Analyzer    | Có file audio mẫu     |
| Video Analyzer    | Có video mẫu          |
| UI Review         | Có timeline JSON mẫu  |
| Renderer          | Có timeline JSON mẫu  |
| Schema thiết kế   | Làm ngay từ đầu       |
| Evaluation metric | Có timeline/video mẫu |

### Phụ thuộc một phần

| Phần              | Phụ thuộc                          |
| ----------------- | ---------------------------------- |
| Embedding Indexer | Cần keyframe từ Video Analyzer     |
| Matching Engine   | Cần audio segment và clip metadata |
| Timeline Planner  | Cần output từ Matching Engine      |

### Cách giảm phụ thuộc

Nên tạo dữ liệu mẫu sớm:

* `audio_segments_sample.json`
* `clip_metadata_sample.json`
* `matching_candidates_sample.json`
* `timeline_sample.json`

Nhờ đó, các thành viên có thể code module của mình mà không cần chờ module khác hoàn thành hoàn toàn.

---

## 16. Rủi ro và cách giảm

| Rủi ro                                   | Ảnh hưởng             | Cách giảm                                |
| ---------------------------------------- | --------------------- | ---------------------------------------- |
| ASR nhận sai transcript                  | Matching sai          | Cho người dùng sửa transcript            |
| Footage thiếu cảnh phù hợp               | Video sai nghĩa       | Dùng fallback + đánh dấu confidence thấp |
| Clip top 1 không hợp cảm nhận người dùng | Video chưa tốt        | Cho chọn clip trong top-k                |
| Scene detection cắt sai                  | Clip candidate xấu    | Lọc clip quá ngắn, chia clip quá dài     |
| CLIP hiểu sai tiếng Việt                 | Chọn sai hình         | Dịch/chuẩn hóa query sang tiếng Anh      |
| Video cuối bị lặp cảnh                   | Thiếu tự nhiên        | Thêm repetition penalty                  |
| Speed chỉnh quá mạnh                     | Video bị giả          | Giới hạn speed trong khoảng an toàn      |
| UI quá phức tạp                          | Không kịp hoàn thành  | Chỉ làm các chỉnh sửa cơ bản cho MVP     |
| Render lỗi codec                         | Không xuất được video | Chuẩn hóa video từ đầu                   |
| Nhóm khó tích hợp                        | Trễ tiến độ           | Thống nhất JSON schema sớm               |

---

## 17. Bộ tiêu chí đánh giá

### Định lượng

| Metric                 | Ý nghĩa                             |
| ---------------------- | ----------------------------------- |
| Segment coverage       | Tỉ lệ audio segment được gán clip   |
| Average semantic score | Điểm khớp nghĩa trung bình          |
| Low-confidence rate    | Tỉ lệ đoạn hệ thống không chắc      |
| Repetition rate        | Tỉ lệ clip bị dùng lặp              |
| Duration error         | Sai lệch thời lượng audio/video     |
| Processing time        | Thời gian xử lý                     |
| Render time            | Thời gian xuất video                |
| User edit count        | Người dùng phải chỉnh bao nhiêu lần |

### Định tính

Cho người xem hoặc người dùng chấm 1–5:

| Tiêu chí           | Câu hỏi đánh giá                     |
| ------------------ | ------------------------------------ |
| Semantic alignment | Hình có đúng nội dung lời nói không? |
| Visual quality     | Hình có rõ, sáng, dễ xem không?      |
| Editing rhythm     | Nhịp cắt có tự nhiên không?          |
| Ease of editing    | UI chỉnh sửa có dễ dùng không?       |
| Final usefulness   | Video cuối có đủ tốt để dùng không?  |

---

## 18. MVP nên làm đến đâu?

MVP nên tập trung vào các chức năng sau:

```text
1. Upload video + audio
2. ASR tạo transcript + timestamp
3. Chia audio thành segment
4. Scene detection video nguồn
5. Trích keyframe + quality score
6. Tạo embedding
7. Tìm top-k clip cho từng audio segment
8. Mặc định chọn clip tốt nhất
9. Tạo timeline JSON
10. UI cho xem timeline và đổi clip trong top-k
11. UI chỉnh speed/transition cơ bản
12. Render video cuối bằng timeline JSON
```

Không nên làm quá nhiều hiệu ứng nâng cao ở MVP.

Nên ưu tiên:

* Đúng nghĩa
* Dễ chỉnh
* Dễ demo
* Render ổn định
* Có dữ liệu trung gian rõ ràng

---

## 19. Kết luận thiết kế nên chọn

Thiết kế phù hợp nhất là:

> Một hệ thống dựng video bán tự động, trong đó AI/pipeline tự tạo bản dựng ban đầu, còn người dùng có thể kiểm tra và tinh chỉnh trực tiếp trên UI trước khi render video cuối.

Điểm cốt lõi của thiết kế:

* Không cố làm AI tự dựng hoàn hảo 100%.
* Có timeline JSON làm trung tâm.
* Matching không chỉ trả về 1 clip, mà trả về top-k clip.
* Mặc định chọn clip tốt nhất, nhưng cho người dùng đổi clip nếu muốn.
* UI cho phép chỉnh các yếu tố quan trọng như clip, tốc độ, transition, crop/fit và âm lượng cơ bản.
* Các module được tách độc lập để nhóm có thể phát triển song song.
* Renderer chỉ cần đọc timeline JSON để xuất video cuối.

Hướng này thực tế hơn vì:

* Phù hợp với nhóm sinh viên 5 người.
* Không cần train model lớn.
* Dễ chia việc.
* Dễ debug.
* Dễ demo.
* Có khả năng mở rộng.
* Tạo ra video cuối tốt hơn nhờ có bước người dùng tinh chỉnh.
