# Tài Liệu Phân Tích Sâu Thuật Toán Hệ Thống Gợi Ý Kỹ Năng

Tài liệu này phân tích chi tiết toán học, ưu nhược điểm và lý do lựa chọn các giải pháp thuật toán trong hệ thống lai (Hybrid Search) kết hợp giữa FAISS và BM25+.

---

## 1. Ưu và nhược điểm của FAISS (Facebook AI Similarity Search)

### Ưu điểm
* **Tốc độ siêu việt trên dữ liệu lớn:** Tối ưu hóa ở mức mã máy (C++, AVX) và hỗ trợ GPU, giúp tìm kiếm láng giềng gần nhất trên không gian hàng triệu vector chỉ trong mili-giây.
* **Hỗ trợ nén dữ liệu hiệu quả:** Tích hợp cơ chế Quantization (PQ, IVF) giúp giảm dung lượng RAM lưu trữ vector.
* **Tìm kiếm theo ngữ nghĩa (Semantic Search):** Hiểu được ngữ cảnh văn bản thông qua không gian nhúng của SentenceTransformer, tránh được hiện tượng bỏ sót từ đồng nghĩa.

### Nhược điểm
* **Không hỗ trợ khớp từ khóa chính xác (Exact Match):** Có xu hướng gom cụm ngữ nghĩa, đôi khi làm trôi mất các từ khóa công nghệ đặc định, hiếm gặp cần độ chính xác 100%.
* **Chi phí tài nguyên lớn:** Quá trình tính toán khoảng cách vector đa chiều đòi hỏi năng lực phần cứng cao.
* **Hệ thống tĩnh (Static Index):** Việc cập nhật, thêm mới dữ liệu theo thời gian thực (Incremental update) dễ làm lệch cấu trúc phân cụm, đòi hỏi phải re-build định kỳ.

---

## 2. Tại sao không dùng TF-IDF, BM25 mà lại chọn BM25+?

* **Hạn chế của TF-IDF:** Điểm số tăng tuyến tính theo tần suất xuất hiện từ ($TF$), dẫn đến việc các từ lặp lại nhiều lần gây nhiễu nặng tín hiệu chung của văn bản.
* **Cải tiến của BM25 so với TF-IDF:** BM25 đưa vào hàm tiệm cận để làm bão hòa tần suất từ (Term Frequency Saturation). Khi từ khóa xuất hiện vượt quá một ngưỡng nhất định, điểm số sẽ không tăng thêm nữa.
* **Hạn chế của BM25 truyền thống:** Gặp lỗi **Phạt quá nặng văn bản dài (Long Document Penalty)**. Trong các bài đăng tuyển dụng (Job Postings) chứa nhiều thông tin phụ trợ dài dòng, mẫu số của công thức BM25 sẽ tăng rất lớn, kéo tụt điểm số đóng góp của từ khóa chính về gần mức 0.
* **Lý do chọn BM25+:** BM25+ bổ sung hằng số thực nghiệm $\delta$ vào cấu trúc công thức. Điều này đảm bảo mỗi từ khóa khớp chính xác luôn đóng góp một lượng điểm tối thiểu là $\delta$, giúp bảo toàn tín hiệu từ khóa bất kể văn bản dài bao nhiêu.

---

## 3. Ưu và nhược điểm của BM25+

### Ưu điểm
* Khớp chính xác tuyệt đối các thuật ngữ công nghệ, tên riêng, mã kỹ năng đặc thù.
* Giải quyết triệt để lỗi triệt tiêu tín hiệu trên văn bản dài của BM25.
* Tốc độ thực thi tối ưu, mô hình gọn nhẹ.

### Nhược điểm
* Hoàn toàn không hiểu ngữ nghĩa (Lexical-only). Gõ sai chính tả hoặc dùng từ đồng nghĩa hệ thống sẽ không nhận diện được.

---

## 4. Nhược điểm khi phối hợp BM25+ cùng FAISS
* **Xung đột thang điểm:** Điểm BM25+ là một miền giá trị mở ($\ge 0$), còn điểm FAISS (Cosine Similarity) giới hạn trong khoảng $[0, 1]$ hoặc $[-1, 1]$. Không thể cộng trực tiếp các giá trị này một cách cơ học.
* **Độ trễ tính toán song song:** Phải tốn tài nguyên chạy đồng thời hai luồng thuật toán khác nhau trước khi tổng hợp kết quả.

---

## 5. Ưu điểm và cải tiến của hệ thống lai thông qua RRF (Reciprocal Rank Fusion)
Hệ thống sử dụng cơ chế **Hòa trộn thứ hạng nghịch đảo (RRF)** mang lại các bổ trợ đột phá:
* **Chuẩn hóa không phụ thuộc thang điểm:** RRF chuyển đổi điểm số thô thành vị trí xếp hạng ($Rank$). Giúp triệt tiêu sự xung đột về mặt đại lượng toán học giữa FAISS và BM25+.
* **Tương hỗ lưỡng cực:** FAISS quét diện rộng để tìm các công việc có cùng phân khúc ngữ nghĩa, trong khi BM25+ tinh lọc và đẩy các công việc chứa chính xác các kỹ năng cốt lõi lên vị trí ưu tiên cao nhất.

---

## 6. Ý nghĩa toán học của công thức BM25+

Công thức tính toán:
$$Score(D, q) = IDF(q) \cdot \left[ \frac{f(q, D) \cdot (k_1 + 1)}{f(q, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{avgdl}\right)} + \delta \right]$$

* **$IDF(q)$**: Đo lường mức độ quan trọng và độ hiếm của từ khóa trên toàn bộ kho dữ liệu.
* **$\frac{|D|}{avgdl}$**: Tỷ lệ chuẩn hóa độ dài văn bản hiện tại so với trung bình hệ thống.
* **$k_1$**: Tham số điều hướng tốc độ đạt trạng thái bão hòa của tần suất từ (Thường chọn $1.2 \rightarrow 2.0$).
* **$b$**: Tham số phạt độ dài văn bản (Thường chọn $0.75$).
* **$\delta$**: Hằng số bảo toàn tín hiệu cốt lõi (Thường chọn $1.0$).

---

## 7. Bản chất các con số cấu hình thực nghiệm

* **Tại sao tham số gộp RRF là 60?** Con số $k=60$ là hằng số thực nghiệm chuẩn hóa quốc tế (TREC). Nó cân bằng tầm ảnh hưởng giữa các tài liệu đứng đầu và loại bỏ nhiễu từ các tài liệu đứng quá xa phía sau. Nếu hạ thấp xuống (về 10), hệ thống sẽ cực đoan chỉ tin tưởng vị trí số 1, số 2. Nếu tăng lên quá cao (về 200), sự phân hóa chất lượng giữa các thứ hạng bị triệt tiêu.
* **Điều gì xảy ra nếu thay đổi $b$ và $k_1$?** Nếu tăng $b > 0.75$, hệ thống sẽ thanh lọc cực kỳ nặng tay các bài tuyển dụng dài. Nếu hạ $k_1$ về gần 0, tần suất xuất hiện từ không còn ý nghĩa, mô hình chỉ đếm xem từ đó có tồn tại hay là không.