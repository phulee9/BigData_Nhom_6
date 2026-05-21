# TÀI LIỆU PHẢN BIỆN CHUYÊN SÂU: CẤU PHẦN BM25+ (BM25PLUS) TRONG HỆ THỐNG RECOMMENDATION

Tài liệu này được biên soạn dưới dạng bộ câu hỏi **Stress-test** từ Hội đồng chấm đồ án, đi kèm câu trả lời chuẩn kiến trúc hệ thống nhằm giúp sinh viên bảo vệ thành công cấu phần tìm kiếm và gợi ý kỹ năng.

---

## 💎 PHẦN 1: BẢN CHẤT TOÁN HỌC & THUẬT TOÁN

### ❓ Câu 1: Tại sao trong công thức BM25+ lại xuất hiện tham số $\delta$ (delta)?
**Bản chất:** Giải quyết lỗi bão hòa tần suất của BM25 truyền thống khi áp dụng vào tài liệu cực dài (Long Documents).

*   **Vấn đề:** Trong BM25 cũ, khi $TF$ tiến đến vô cùng, điểm số bị tiệm cận về một hằng số. Khi gộp hàng ngàn Job thành một **Virtual Unified Document**, lỗi này làm mất sự phân cấp giữa kỹ năng chính và phụ.
*   **Giải pháp:** **BM25+** bổ sung $\delta$ (thường $= 1.0$) để thiết lập một cận dưới tuyến tính. Điều này đảm bảo mối liên hệ giữa tần suất xuất hiện và điểm số khuyến nghị luôn giữ vững tính đơn điệu, không bao giờ bị bão hòa dù văn bản dài đến đâu.

### ❓ Câu 2: Ý nghĩa của tham số $k_1$ và $b$ trong việc tính điểm?
*   **$k_1$ (Term Frequency Saturation):** Điều phối mức độ ảnh hưởng của tần suất. $k_1$ càng cao, hệ thống càng ưu tiên những kỹ năng xuất hiện lặp lại nhiều lần trong Role.
*   **$b$ (Document Length Normalization):** Điều phối mức độ phạt độ dài văn bản.
    > **Cảnh báo:** Nếu tăng $b = 1$ (phạt tối đa), hệ thống sẽ thiên vị các Role ngách (văn bản ngắn) và kéo tụt điểm của các Role phổ biến (văn bản dài). Cấu hình $b = 0.75$ là điểm cân bằng hoàn hảo.
---

## 🏗️ PHẦN 2: KIẾN TRÚC "VIRTUAL UNIFIED DOCUMENT" (GOM CỤM ROLE)

### ❓ Câu 3: Việc lặp lại từ khóa (Role Name/Skill) có phải là "gian lận" dữ liệu?
Không, đây là cơ chế **Tái cấu trúc phân phối xác suất (Probability Distribution Resampling)**.
*   **Lặp tên Role:** Tạo "lực hút" (Keyword Anchor) để BM25+ nhận diện phân vùng Role ngay khi người dùng nhập Job Title.
*   **Lặp kỹ năng:** Biến ma trận tần suất dạng số thành dạng văn bản thô (Text Corpus) để BM25+ phát huy tối đa sức mạnh tính toán mà không cần qua các bước trung gian phức tạp.
*   **So với LLM:** Phương pháp này tối ưu hơn LLM về chi phí, độ trễ (Latency) và tránh được hiện tượng ảo tưởng (Hallucination).

### ❓ Câu 4: Xử lý rác dữ liệu và Spam từ khóa (Keyword Stuffing)?
Kiến trúc **Group By theo Role** chính là bộ lọc nhiễu tự nhiên:
*   Nếu để từng Job đơn lẻ, Job rác sẽ vọt lên Top.
*   Khi gom cụm, các từ khóa rác từ một vài tin tuyển dụng lẻ tẻ sẽ có tần suất cực thấp so với các kỹ năng chuẩn (SQL, Python,...) được hàng ngàn tin chính thống xác nhận. Chỉ số **IDF** sẽ tự động "đè" điểm của những từ khóa nhiễu này xuống mức tối thiểu.
---

## 🤝 PHẦN 3: SỰ PHỐI HỢP HYBRID (FAISS vs BM25+)

### ❓ Câu 5: Tại sao cần cả BM25+ khi đã có FAISS (Neural Search)?
Đây là mô hình **Hybrid Retrieval** (Song kiếm hợp bích):
1.  **FAISS (Semantic - Ngữ nghĩa):** Hiểu ngữ cảnh vĩ mô (ví dụ: Data Analyst tương đồng với Business Intelligence). Hoạt động tốt trên tầng Job đơn lẻ.
2.  **BM25+ (Lexical - Khớp từ khóa):** Đảm bảo độ chính xác tuyệt đối với các từ khóa kỹ năng cứng (ví dụ: Angular v14 khác v17).
3.  **Quan trọng:** FAISS không thể tính toán lộ trình kỹ năng thiếu hụt. BM25+ tạo ra ma trận trọng số vĩ mô để bóc tách chính xác những "mảnh ghép" còn thiếu trong CV ứng viên.

### ❓ Câu 6: Tại sao lấy điểm của Job để tính điểm cho Skill?
Dựa trên logic **Lan truyền trọng số theo ngữ cảnh (Contextual Weight Propagation)**:
$$Skill\_Score += Job\_Base\_Score \times Skill\_Source\_Weight$$
*   Chúng ta không tìm kỹ năng xuất hiện nhiều nhất một cách mù quáng.
*   Chúng ta tìm kỹ năng xuất hiện trong những **Job phù hợp nhất** với người dùng. Một Job có điểm cao (do FAISS/Location match) thì các kỹ năng bên trong nó xứng đáng có trọng số tích lũy lớn hơn.

---

## 🛠️ PHẦN 4: TIỀN XỬ LÝ & THỰC TẾ VẬN HÀNH

### ❓ Câu 7: Quy trình xử lý dữ liệu thô (Data Pipeline)?
Áp dụng pipeline 4 bước:
1.  **Clean HTML & Regex:** Loại bỏ rác định dạng.
2.  **Normalization:** Đồng bộ hóa font và Case (tránh hiểu nhầm Java và java).
3.  **Custom Stopwords:** Loại bỏ từ thừa ngành tuyển dụng (yêu cầu, mức lương, quyền lợi...).
4.  **Skill-Extraction (Hard Filtering):** Chỉ giữ lại các danh từ riêng thuộc bộ từ điển kỹ năng để BM25+ tập trung 100% vào chuyên môn.

### ❓ Câu 8: Làm sao kết hợp điểm số giữa FAISS và BM25+?
Vì hai thang điểm khác nhau, chúng ta sử dụng:
*   **Cách 1: Min-Max Scaling:** Đưa tất cả về khoảng $[0, 1]$ rồi tính tổng có trọng số ($\alpha \approx 0.7$ cho FAISS).
*   **Cách 2: Reciprocal Rank Fusion (RRF):** Chỉ quan tâm đến thứ hạng (Rank) để kết hợp kết quả một cách công bằng.

### ❓ Câu 9: Giới hạn và hướng phát triển?
*   **Cold Start:** Với Role mới chưa đủ dữ liệu, hệ thống ưu tiên 100% FAISS trước khi cập nhật văn bản gộp.
*   **Batch Update:** Cần chạy Cron Job cập nhật định kỳ (tuần/tháng) để bắt kịp các công nghệ mới nổi (LLM, Generative AI).

---
> **💡 Mẹo ghi điểm:** Luôn bám sát số liệu về thời gian phản hồi (mili-giây) và độ chính xác (Precision/Recall) để thuyết phục Hội đồng.
