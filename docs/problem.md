## 🎬 Phát biểu bài toán: Dựng video tự động dựa trên âm thanh thuyết minh (Audio-Guided Video Montage)

---

### 🎯 1. Mục tiêu tổng quát
Xây dựng một hệ thống biên tập và tổng hợp video tự động. Hệ thống nhận đầu vào là một tập hợp gồm **một hoặc nhiều video thô** và một **luồng âm thanh thuyết minh độc lập**. 

Đầu ra bắt buộc là một **video hoàn chỉnh duy nhất**, trong đó các phân cảnh được trích lọc từ tập video đầu vào, sắp xếp và đồng bộ hóa thời lượng sao cho hình ảnh khớp hoàn toàn về mặt ngữ nghĩa và nhịp độ với nội dung của lời thuyết minh.

---

### 📥 2. Không gian Dữ liệu Đầu vào (Inputs)

* **Tập hợp Video nguồn ($V = \{V_1, V_2, ..., V_n\}, n \ge 1$):** Tập hợp gồm một hoặc nhiều file video thô. Các video này đóng vai trò là kho dữ liệu hình ảnh (footage) cung cấp vật liệu dựng phim, có thể chứa các góc máy khác nhau, bối cảnh khác nhau và bao gồm cả những phân cảnh dư thừa, chưa qua biên tập.
* **Âm thanh thuyết minh ($A$):** File âm thanh (voice-over) chứa lời dẫn xuyên suốt. 
  > **Ghi chú:** Lời thuyết minh có thể là tiếng Việt ở giai đoạn hiện tại, nhưng kiến trúc hệ thống không bị giới hạn và có khả năng mở rộng để xử lý đa ngôn ngữ trong tương lai.

---

### 📤 3. Không gian Dữ liệu Đầu ra (Output)

* **Video hoàn chỉnh ($V'$):** Sản phẩm đa phương tiện duy nhất đã được kết xuất (render). $V'$ phải thỏa mãn đồng thời các hệ ràng buộc cốt lõi sau:

  * 🎞️ **Ràng buộc về nguồn cấp (Source Constraint):** Toàn bộ dữ liệu hình ảnh (visual sequence) cấu thành nên video $V'$ bắt buộc phải được trích xuất, cắt ghép và chọn lọc từ tập video đầu vào $V$.
  * 🔊 **Ràng buộc về âm thanh (Audio Track Constraint):** Kênh âm thanh chủ đạo và đồng nhất chạy xuyên suốt $V'$ chính là tệp âm thanh thuyết minh $A$.
  * 🧠 **Ràng buộc về ngữ nghĩa (Semantic Alignment):** Mỗi phân cảnh hình ảnh xuất hiện trong $V'$ phải có sự tương quan logic và minh họa chính xác cho thông điệp, ý nghĩa đang được phát ra từ âm thanh $A$ tại cùng một thời điểm tương ứng.
  * ⏱️ **Ràng buộc về thời gian (Temporal Synchronization):** Điểm bắt đầu, điểm kết thúc và nhịp độ của các phân cảnh hình ảnh phải được tính toán và căn chỉnh linh hoạt (thông qua các thao tác như cắt xén, tua nhanh, làm chậm, hoặc giữ khung hình) để khớp hoàn toàn với trường độ của lời dẫn trong $A$.

  

