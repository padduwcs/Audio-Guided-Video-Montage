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
4. Tạo embedding cho audio segment và clip/keyframe, lưu metadata/index
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

* Người làm UI có thể dùng `timeline_sample.json`, `matching_candidates_sample.json`, `clip_metadata_sample.json`, `audio_segments_sample.json` và `media_metadata_sample.json`.
* Người làm renderer có thể dùng `timeline_sample.json`, `media_metadata_sample.json`, `render_config_sample.json` và media source mẫu để test FFmpeg.
* Người làm matching có thể xuất `matching_candidates.json`.
* Người làm audio và video có thể xử lý hai nhánh độc lập trước khi ghép lại.

---

> **Lưu ý:** File này mô tả *lý do thiết kế*. Triển khai code theo [`02_data_contract.md`](details/02_data_contract.md), `docs/schemas/`, `docs/samples/` và stage spec `03`–`10` — không lấy JSON từ file này làm contract.

## 5. Tóm tắt pipeline theo stage

| Stage | Spec | Ý tưởng thiết kế |
| ----- | ---- | ---------------- |
| 1 Input | [`03_stage_1_input_processing.md`](details/03_stage_1_input_processing.md) | Chuẩn hóa media; `status` ready/warning usable |
| 2 Audio | [`04_stage_2_audio_analysis.md`](details/04_stage_2_audio_analysis.md) | ASR → segment có ý nghĩa → query; sửa transcript rẻ hơn sửa video |
| 3 Video | [`05_stage_3_video_analysis.md`](details/05_stage_3_video_analysis.md) | Scene/shot → clip + nhiều keyframe; quality score |
| 4 Embedding | [`06_stage_4_embedding_indexing.md`](details/06_stage_4_embedding_indexing.md) | Text/image vector; index riêng, metadata mapping |
| 5 Matching | [`07_stage_5_matching_engine.md`](details/07_stage_5_matching_engine.md) | Top-k + score tổng hợp + confidence |
| 6 Timeline | [`08_stage_6_timeline_planning.md`](details/08_stage_6_timeline_planning.md) | 1 segment → nhiều visual items; speed/fallback |
| 7 Review UI | [`09_stage_7_review_ui.md`](details/09_stage_7_review_ui.md) | Review đơn giản; đổi clip trong top-k |
| 8 Render | [`10_stage_8_rendering.md`](details/10_stage_8_rendering.md) | Chỉ đọc timeline; không chạy lại pipeline |

Mẫu JSON: `docs/samples/*_sample.json`.

## 6. Lý do thiết kế quan trọng

### 6.1. Vì sao top-k thay vì top-1?

Clip điểm cao nhất chưa chắc đẹp hoặc phù hợp cảm nhận người dùng. Top-k + UI đổi clip thực tế hơn matching hoàn toàn tự động.

### 6.2. Vì sao `timeline.json` là trung tâm?

Người dùng chỉnh clip → cập nhật timeline → render lại. Không cần ASR, scene detection, embedding hay matching lại.

### 6.3. Một audio segment — nhiều visual items

Segment dài có thể cần nhiều clip; clip dài chỉ dùng một phần; đoạn trừu tượng cần B-roll. Chi tiết duration/speed: stage 6 spec.

### 6.4. Matching baseline và giới hạn

Text–image embedding là baseline hợp lý nhưng yếu với hành động phức tạp, câu trừu tượng, dịch Việt→Anh. Cần kết hợp quality, duration fit, penalty — công thức MVP: stage 5 spec.

### 6.5. UI và render tách biệt

UI không render nặng; không phức tạp như NLE chuyên nghiệp. Renderer không chọn clip — chỉ làm theo timeline.

## 7. Dữ liệu trung gian

Contract đầy đủ: [`02_data_contract.md`](details/02_data_contract.md) · [`01_system_architecture.md` §5](details/01_system_architecture.md).

| File | Sample |
| ---- | ------ |
| `media_metadata.json` | `docs/samples/media_metadata_sample.json` |
| `audio_segments.json` | `docs/samples/audio_segments_sample.json` |
| `clip_metadata.json` | `docs/samples/clip_metadata_sample.json` |
| `embedding_metadata.json` | `docs/samples/embedding_metadata_sample.json` |
| `matching_candidates.json` | `docs/samples/matching_candidates_sample.json` |
| `timeline.json` | `docs/samples/timeline_sample.json` |
| `render_config.json` | `docs/samples/render_config_sample.json` |
| `render_log.json` | `docs/samples/render_log_sample.json` |

Mapping cross-file: [`02` §13](details/02_data_contract.md).

## 8. Phân công và phát triển song song

Phân công nhóm: [`11_team_assignment.md`](details/11_team_assignment.md).

Phụ thuộc module, sample data, tích hợp theo lớp: [`01` §7, §10](details/01_system_architecture.md) · [`12_integration_plan.md`](details/12_integration_plan.md).

---

---

## 9. Rủi ro và cách giảm

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

## 10. Bộ tiêu chí đánh giá

### 10.1. Định lượng

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

### 10.2. Định tính

Cho người xem hoặc người dùng chấm 1-5:

| Tiêu chí           | Câu hỏi đánh giá                       |
| ------------------ | -------------------------------------- |
| Semantic alignment | Hình có liên quan đến lời nói không?   |
| Visual quality     | Hình có rõ, sáng, dễ xem không?        |
| Editing rhythm     | Nhịp cắt có tự nhiên không?            |
| Ease of editing    | UI chỉnh sửa có dễ dùng không?         |
| Final usefulness   | Video cuối có đủ tốt để sử dụng không? |

---

## 11. MVP nên làm đến đâu?

MVP nên tập trung vào một luồng end-to-end chạy ổn định thay vì cố làm nhiều chức năng nâng cao.

### 11.1. MVP bắt buộc

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

### 11.2. MVP nếu còn thời gian

```text
12. Highlight đoạn confidence thấp
13. Chỉnh speed bằng preset
14. Chọn transition cơ bản
15. Bật/tắt hoặc giảm âm lượng audio gốc
```

### 11.3. Không nên làm trong MVP

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

## 12. Kết luận thiết kế nên chọn

Thiết kế phù hợp nhất là:

> Một hệ thống dựng video bán tự động, trong đó pipeline tự tạo bản dựng ban đầu từ video nguồn và audio thuyết minh, còn người dùng có thể kiểm tra, chọn clip thay thế và render lại video cuối trên UI.

Điểm cốt lõi của thiết kế:

* Không cố làm AI tự dựng hoàn hảo 100%.
* Có `timeline JSON` làm trung tâm.
* Matching trả về top-k clip thay vì chỉ top-1.
* Timeline hỗ trợ một audio segment gồm một hoặc nhiều visual items.
* UI tập trung vào review và chỉnh những lỗi quan trọng.
* Renderer render theo timeline JSON hợp lệ và media source đã chuẩn hóa để xuất video cuối.
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
