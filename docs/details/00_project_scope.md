# 00. Product Scope

## 1. Tên dự án

**Audio-Guided Video Montage**

Tên tiếng Việt đề xuất:

**Hệ thống dựng video bán tự động theo audio thuyết minh**

## 2. Mục tiêu sản phẩm

Dự án xây dựng một hệ thống hỗ trợ tạo video hoàn chỉnh từ:

* Một hoặc nhiều video nguồn có sẵn.
* Một file audio thuyết minh / voice-over có sẵn.

Hệ thống sẽ phân tích nội dung audio, phân tích video nguồn, chọn các đoạn video phù hợp với từng phần lời nói, lập timeline dựng video, cho phép người dùng kiểm tra và chỉnh sửa cơ bản, sau đó render ra video cuối.

Sản phẩm không tự sinh video mới từ đầu, mà tận dụng các cảnh có trong video nguồn để tạo ra một bản dựng mới phù hợp nhất với audio thuyết minh.

Mục tiêu chính:

* Giảm công sức chọn cảnh thủ công.
* Tự động đề xuất clip phù hợp với từng đoạn audio.
* Tạo timeline dựng video có thể chỉnh sửa.
* Cho phép người dùng kiểm tra, đổi clip và render lại video.
* Tạo video cuối đủ tốt để sử dụng sau khi review cơ bản.

## 3. Định vị sản phẩm

Sản phẩm được định vị là một hệ thống **dựng video bán tự động**, không phải hệ thống dựng video tự động hoàn toàn.

Hệ thống sẽ:

* Tự tạo bản dựng ban đầu.
* Đề xuất top-k clip phù hợp cho từng đoạn audio.
* Chọn clip tốt nhất làm mặc định.
* Đánh dấu những đoạn confidence thấp.
* Cho phép người dùng đổi clip hoặc chỉnh một số tham số cơ bản.
* Render video cuối dựa trên timeline đã được xác nhận.

Hệ thống không cố đảm bảo mọi đoạn hình khớp tuyệt đối với lời nói, vì video nguồn có thể thiếu cảnh phù hợp hoặc audio có những đoạn trừu tượng, cảm xúc, tổng quát.

## 4. Người dùng mục tiêu

Người dùng mục tiêu là người có sẵn video nguồn và audio thuyết minh, muốn tạo nhanh một video mới có hình ảnh khớp tương đối với lời nói.

Ví dụ:

* Sinh viên làm video báo cáo, video thuyết trình.
* Người tạo nội dung muốn dựng video từ footage có sẵn.
* Người làm video recap sự kiện, tham quan, du lịch.
* Người có video dài và muốn tạo bản dựng ngắn theo voice-over.
* Người không muốn tự chọn từng cảnh thủ công trong phần mềm dựng video chuyên nghiệp.

## 5. Use case chính

### Use case 1: Video tham quan

Người dùng có nhiều video quay trong một buổi tham quan và một file audio thuyết minh mô tả hành trình.

Hệ thống cần chọn các cảnh như cổng vào, khu trưng bày, người tham quan, không gian chung, hoạt động chính, rồi ghép theo nội dung audio.

### Use case 2: Video nấu ăn

Người dùng có video quay quá trình nấu ăn và một audio thuyết minh các bước thực hiện.

Hệ thống cần chọn cảnh sơ chế, trộn nguyên liệu, nấu, trình bày món ăn tương ứng với từng đoạn lời nói.

### Use case 3: Video giới thiệu địa điểm / sự kiện

Người dùng có footage về một địa điểm hoặc sự kiện, kèm audio giới thiệu.

Hệ thống cần dựng lại video theo thứ tự nội dung trong audio, ưu tiên cảnh đẹp, rõ, sáng, ít rung và liên quan đến lời thuyết minh.

## 6. Input của hệ thống

### 6.1. Video nguồn

Hệ thống nhận một hoặc nhiều video nguồn.

Yêu cầu:

* Định dạng phổ biến: `.mp4`, `.mov`, `.mkv`.
* Video nên có liên quan tương đối đến nội dung audio.
* Video có thể dài hơn hoặc ngắn hơn audio.
* Video có thể chứa cảnh dư thừa, cảnh xấu, cảnh không liên quan.
* Hệ thống chỉ sử dụng cảnh có sẵn trong video nguồn.

### 6.2. Audio thuyết minh

Hệ thống nhận một file audio làm kênh âm thanh chính của video cuối.

Yêu cầu:

* Định dạng phổ biến: `.wav`, `.mp3`, `.m4a`.
* Audio có thể là tiếng Việt trong phạm vi MVP.
* Audio cần được chuyển thành transcript có timestamp.
* Người dùng nên có khả năng sửa transcript nếu ASR nhận sai.

### 6.3. Tham số cấu hình cơ bản

Trong MVP, có thể hỗ trợ một số tham số cấu hình đơn giản:

* Resolution đầu ra, ví dụ `1920x1080`.
* FPS đầu ra, ví dụ `30fps`.
* Số lượng candidate clip cho mỗi audio segment, ví dụ `top_k = 5`.
* Có giữ âm thanh gốc của video nguồn hay không.
* Âm lượng audio gốc nếu được giữ lại.

## 7. Output của hệ thống

Hệ thống cần tạo ra các output chính sau:

### 7.1. Video hoàn chỉnh

File video cuối:

```text
final_video.mp4
```

Video cuối sử dụng audio thuyết minh làm âm thanh chính và hình ảnh được dựng từ video nguồn.

### 7.2. Timeline JSON

File timeline mô tả toàn bộ bản dựng:

```text
timeline.json
```

Timeline chứa:

* Audio segment.
* Transcript.
* Clip được chọn.
* Thời gian cắt clip.
* Speed.
* Transition.
* Confidence.
* Liên kết đến candidate clips.

### 7.3. Matching candidates

File danh sách top-k clip cho từng audio segment:

```text
matching_candidates.json
```

File này giúp UI hiển thị các clip thay thế để người dùng chọn lại.

### 7.4. Các file trung gian khác

Các file trung gian phục vụ debug và tích hợp:

```text
media_metadata.json
audio_segments.json
clip_metadata.json
embedding_metadata.json
embedding/index files
render_log.json
```

## 8. Phạm vi MVP

MVP cần tập trung vào một luồng end-to-end chạy được từ đầu vào đến video cuối.

### 8.1. Chức năng bắt buộc

MVP bắt buộc có:

1. Nhận video nguồn và audio thuyết minh.
2. Chuẩn hóa hoặc kiểm tra metadata của video/audio.
3. Chuyển audio thành transcript có timestamp.
4. Chia audio thành các segment có ý nghĩa.
5. Phân tích video nguồn để tách clip candidate.
6. Trích keyframe cho mỗi clip candidate.
7. Tính quality score cơ bản cho clip.
8. Tạo embedding hoặc đặc trưng để so khớp text với hình ảnh.
9. Tìm top-k clip phù hợp cho từng audio segment.
10. Mặc định chọn clip có điểm tốt nhất.
11. Tạo `timeline.json`.
12. Hiển thị timeline trên UI review cơ bản.
13. Cho phép người dùng chọn clip khác trong top-k.
14. Cập nhật timeline sau khi người dùng chỉnh.
15. Render video cuối từ timeline.

### 8.2. Chức năng nên có nếu còn thời gian

Các chức năng nên có nhưng không bắt buộc ở MVP đầu tiên:

* Highlight đoạn confidence thấp.
* Chỉnh speed bằng preset, ví dụ `0.75x`, `1.0x`, `1.25x`.
* Chọn transition cơ bản, ví dụ `cut`, `fade`, `crossfade`.
* Chọn crop mode, ví dụ `fit`, `fill`, `center_crop`.
* Bật/tắt audio gốc của video nguồn.
* Giảm âm lượng audio gốc.

## 9. Ngoài phạm vi MVP

Các chức năng sau không thuộc phạm vi MVP:

* Tự sinh video mới bằng AI.
* Tạo cảnh không có trong video nguồn.
* Dựng video chuyên nghiệp nhiều track như Premiere, CapCut hoặc DaVinci Resolve.
* Hiệu ứng nâng cao.
* Keyframe animation phức tạp.
* Color grading.
* Motion graphic template.
* Chỉnh sửa audio chi tiết.
* Tạo caption đẹp tự động.
* Nhận diện hành động phức tạp ở mức chính xác cao.
* Đảm bảo 100% hình ảnh khớp tuyệt đối với mọi câu trong audio.

## 10. Giả định

Dự án dựa trên các giả định sau:

* Video nguồn có liên quan tương đối đến nội dung audio.
* Audio thuyết minh là kênh âm thanh chính.
* Người dùng chấp nhận review và chỉnh sửa cơ bản sau khi hệ thống tạo bản dựng ban đầu.
* Hệ thống có thể gặp đoạn không tìm được clip phù hợp và cần fallback.
* Matching bằng embedding chỉ là baseline, có thể chưa chính xác tuyệt đối.
* Tiếng Việt là ngôn ngữ ưu tiên trong MVP.
* Nhóm không train model lớn từ đầu, mà ưu tiên dùng thư viện/model có sẵn.

## 11. Ràng buộc kỹ thuật

Một số ràng buộc kỹ thuật cần thống nhất:

* Tất cả thời gian trong JSON dùng đơn vị giây.
* Score nằm trong khoảng `0.0` đến `1.0`.
* Confidence dùng ba mức: `high`, `medium`, `low`.
* Mỗi module phải xuất output đúng schema.
* Renderer render theo timeline và media source đã chuẩn hóa, không chạy lại toàn bộ pipeline.
* UI chỉ chỉnh timeline, không chỉnh trực tiếp video nguồn.
* Các file video/audio nặng không nên commit lên GitHub.

## 12. Tiêu chí thành công của MVP

MVP được xem là đạt yêu cầu khi:

* Có thể chạy được một demo end-to-end với video/audio mẫu.
* Audio được chuyển thành transcript có timestamp.
* Video nguồn được tách thành clip candidate.
* Mỗi audio segment có danh sách top-k clip đề xuất.
* Hệ thống tạo được timeline JSON hợp lệ.
* UI hiển thị được timeline và cho đổi clip trong top-k.
* Timeline sau khi chỉnh có thể dùng để render lại video.
* Renderer xuất được `final_video.mp4`.
* Video cuối có hình ảnh liên quan tương đối đến audio.
* Các file trung gian đủ rõ để debug và báo cáo.

## 13. Kết quả demo mong muốn

Kịch bản demo tối thiểu:

1. Người dùng đưa vào:

   * 1 audio thuyết minh.
   * 1 hoặc nhiều video nguồn.

2. Hệ thống xử lý và tạo:

   * `media_metadata.json`
   * `audio_segments.json`
   * `clip_metadata.json`
   * `embedding_metadata.json`
   * embedding/index files
   * `matching_candidates.json`
   * `timeline.json`
   * `render_log.json`

3. Người dùng mở UI review:

   * Xem từng audio segment.
   * Xem transcript.
   * Xem clip đang được chọn.
   * Xem score/confidence.
   * Đổi clip nếu chưa phù hợp.

4. Hệ thống render:

   * Đọc timeline đã cập nhật.
   * Xuất video cuối `final_video.mp4`.

## 14. Định nghĩa sản phẩm hoàn thành ở mức đồ án

Ở mức đồ án, sản phẩm không cần hoàn hảo như công cụ thương mại, nhưng cần chứng minh được:

* Bài toán thực tế có ý nghĩa.
* Pipeline xử lý rõ ràng.
* Các module có input/output tách biệt.
* Có cơ chế matching audio-video.
* Có timeline trung gian để chỉnh sửa.
* Có UI review bán tự động.
* Có renderer xuất video cuối.
* Có thể đánh giá kết quả bằng metric và nhận xét định tính.

Sản phẩm cuối cần thể hiện được tư tưởng chính:

**Hệ thống tự đề xuất bản dựng ban đầu dựa trên audio thuyết minh, sau đó cho phép người dùng kiểm tra và tinh chỉnh trên timeline đơn giản để tạo ra video hoàn chỉnh.**
