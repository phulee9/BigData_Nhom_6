# TÀI LIỆU PHẢN BIỆN CHUYÊN SÂU: CẤU PHẦN BM25+ (UNIFIED ROLE MODEL)

Tài liệu này tổng hợp logic cốt lõi từ các module `model_bm25.py`, `01_build_bm25.py` và `02_bm25_recommend.py`. Đây là "vũ khí" để giải trình tính đúng đắn và tối ưu của hệ thống trước Hội đồng.
---

## 💎 PHẦN 1: CHIẾN THUẬT TOKENIZATION & VIRTUAL DOCUMENTS

### ❓ Câu 1: Tại sao lại gộp nhiều Job thành một "Unified Document" thay vì để riêng lẻ?
**Trả lời:** Đây là kỹ thuật **Document Aggregation** nhằm mục đích **Triệt tiêu nhiễu (Denoising)**.
* **Vấn đề của Item-based:** Từng tin tuyển dụng riêng lẻ thường viết rất tùy hứng (quá ngắn hoặc quá dài), dẫn đến điểm số BM25 bị lệch.
* **Giải pháp Unified Role:** Khi gộp tất cả Job có cùng `job_title_canonical` thành một tài liệu duy nhất cho một **Role**, chúng ta tạo ra một "Profile chuẩn". Điều này giúp thuật toán tập trung vào phân phối xác suất của kỹ năng trên toàn bộ thị trường thay vì bị ảnh hưởng bởi một vài tin tuyển dụng cá biệt.

### ❓ Câu 2: Giải thích cơ chế lặp lại từ khóa (Token Weighting) trong code?
**Trả lời:** Hệ thống sử dụng cơ chế **Frequency-based Importance Weighting** thủ công để hỗ trợ BM25+:
* **Role Name Boosting (`ROLE_NAME_REPEAT = 2`):** Nhân đôi tên Role giúp tạo "điểm neo" (Anchor). Khi người dùng nhập tên Role, thuật toán sẽ nhận diện chính xác phân vùng dữ liệu đó ngay lập tức.
* **Skill Weighting (`skill * count`):** Trong code `tokens.extend(skill.split() * count)`, `count` chính là số lần kỹ năng đó xuất hiện thực tế.
    * *Ví dụ:* Nếu Role "Data Scientist" có 100 Jobs và 90 Jobs yêu cầu "Python", từ "Python" sẽ xuất hiện 90 lần. BM25+ sẽ tự hiểu đây là kỹ năng trọng tâm (Core Skill).
---

## 🏗️ PHẦN 2: QUY TRÌNH TRIỂN KHAI & HIỆU NĂNG

### ❓ Câu 3: Quy trình vận hành từ Offline sang Online diễn ra như thế nào?
**Trả lời:** Hệ thống tuân thủ kiến trúc **Batch-Processing Pipeline**:
1. **Giai đoạn Build Model (`01_build_bm25.py`):** Đọc dữ liệu từ MinIO, thực hiện tính toán tần suất, khởi tạo `BM25Plus` và lưu toàn bộ trạng thái vào file `pickle`.
2. **Giai đoạn Deployment:** Upload file pickle lên MinIO làm phiên bản model chính thức (`GOLD_KAGGLE_BM25_MODEL`).
3. **Giai đoạn Inference (`02_bm25_recommend.py`):** Khi hệ thống chạy, nó không tính toán lại từ đầu mà chỉ **deserialize** file pickle. Điều này giúp tốc độ Query đạt mức mili-giây, đáp ứng yêu cầu của một hệ thống Real-time Recommendation.

### ❓ Câu 4: Tại sao lại áp dụng ngưỡng lọc `valid_roles >= 3`?
**Trả lời:** Để đảm bảo **Ý nghĩa thống kê (Statistical Significance)**. Những Role chỉ xuất hiện 1-2 lần thường là dữ liệu lỗi hoặc các vị trí quá đặc thù, không mang tính đại diện. Việc lọc này giúp bộ gợi ý kỹ năng luôn bám sát xu hướng thực tế của thị trường lao động.
---

## 🤝 PHẦN 3: BẢN CHẤT TOÁN HỌC (DEEP DIVE)

### ❓ Câu 5: Công thức tính `recommend_score` có gì đặc biệt?
**Trả lời:** Đây là sự kết hợp giữa **Lexical Similarity** và **Local Density**:
$$Skill\_Score = \sum_{Role \in TopK} \left( BM25\_Score(Query, Role) \times \frac{Skill\_Count_{Role}}{Total\_Jobs_{Role}} \right)$$
* Hệ thống không chỉ nhìn vào việc Role đó giống bạn bao nhiêu (`bm25_score`), mà còn nhìn vào việc kỹ năng đó "phổ biến" mức nào trong Role đó (`count / job_count`).
* Điều này giúp loại bỏ trường hợp một kỹ năng hiếm gặp tình cờ xuất hiện trong một Role có điểm tương đồng thấp.

### ❓ Câu 6: Tại sao chọn BM25+ thay vì BM25 truyền thống hay TF-IDF?
**Trả lời:** * **TF-IDF:** Không có cơ chế bão hòa tần suất và không kiểm soát được độ dài văn bản (Length Normalization).
* **BM25 truyền thống:** Khi tài liệu cực dài (như Unified Document của chúng ta), BM25 dễ bị rơi vào trạng thái bão hòa điểm số.
* **BM25+:** Bổ sung tham số $\delta$ (delta) giúp đảm bảo điểm số luôn tăng (tuyến tính nhẹ) theo tần suất kỹ năng, giúp phân cấp rõ rệt giữa các kỹ năng "quan trọng" và "rất quan trọng".

---

## 🛠️ PHẦN 4: KHẢ NĂNG MỞ RỘNG

### ❓ Câu 7: Hệ thống xử lý kỹ năng người dùng đã biết như thế nào?
**Trả lời:** Sử dụng **Negative Filtering**. Toàn bộ `user_skills` sẽ được đưa vào một `set` để đối chiếu. Sau khi tính toán xong danh sách gợi ý, hệ thống sẽ thực hiện phép trừ tập hợp để đảm bảo 100% kết quả trả về là những kỹ năng người dùng **thực sự thiếu hụt**.

### ❓ Câu 8: Việc dùng MinIO có ưu điểm gì cho Big Data?
**Trả lời:** MinIO đóng vai trò là **Data Lake**. Nó cho phép lưu trữ các phiên bản Model (Checkpointing) khác nhau. Khi dữ liệu tuyển dụng tăng lên hàng triệu bản ghi, chúng ta chỉ cần chạy lại script Build trên một cụm Spark/Worker và cập nhật file Pickle, hệ thống gợi ý sẽ tự động "thông minh" lên mà không cần code lại logic.

---
> **💡 Mẹo bảo vệ:** Khi bị hỏi về độ chính xác, hãy tự tin nói: "Hệ thống của em không chỉ khớp từ khóa, mà còn mô phỏng lại phân phối kỹ năng của thị trường lao động thông qua cơ chế Unified Document Weighting."

