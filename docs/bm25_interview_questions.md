# Bộ Câu Hỏi Phỏng Vấn Bảo Vệ Đồ Án Về Thuật Toán BM25+

Tài liệu này tổng hợp các câu hỏi phản biện mà Giảng viên/Hội đồng có thể đặt ra xoay quanh việc áp dụng thuật toán BM25+ trong hệ thống gợi ý lai (Hybrid Recommendation System).

---

### Nhóm 1: Bản chất Toán học & Tham số Cấu hình

#### Câu 1: Trong công thức BM25+, tham số $k_1$ và $b$ có ý nghĩa gì? Các em tinh chỉnh các thông số này như thế nào?
* **Trả lời phản biện:**
  * $k_1$ điều khiển tốc độ đạt trạng thái bão hòa của tần suất từ (Term Frequency Saturation). Giá trị càng cao thì sự chênh lệch giữa việc từ khóa xuất hiện nhiều lần hay ít lần càng phân hóa rõ rệt.
  * $b$ điều khiển mức độ phạt độ dài của văn bản (Document Length Penalty), có giá trị từ $0 \rightarrow 1$. Nếu $b=1$, hệ thống phạt tối đa các văn bản dài.
  * **Thực tế cấu hình:** Hệ thống áp dụng cấu hình tiêu chuẩn vàng dựa trên các thực nghiệm quốc tế (TREC) là $k_1 = 1.5$ và $b = 0.75$. Mức này giúp thuật toán cân bằng hoàn hảo giữa tính chất dài dòng của bài đăng tuyển dụng (Job Postings) và tần suất xuất hiện thực tế của các kỹ năng cốt lõi.

#### Câu 2: Tại sao lại cần thêm hằng số $\delta$ (delta) trong BM25+? Nó giải quyết lỗi gì của BM25 truyền thống?
* **Trả lời phản biện:**
  * BM25 truyền thống gặp phải một lỗi chí mạng mang tên **"Phạt quá nặng văn bản dài" (Long Document Penalty)**. Khi một bài đăng tuyển dụng quá dài (do chứa nhiều nội dung phụ như phúc lợi, mô tả công ty), thành phần mẫu số của BM25 tăng mạnh, kéo tụt điểm số thành phần tần suất từ của từ khóa chính về sát mức $0$.
  * BM25+ giải quyết lỗi này bằng cách bổ sung một hằng số thực nghiệm $\delta$ (thường bằng $1.0$). Điều này thiết lập một "mức điểm sàn tối thiểu", bảo toàn tín hiệu từ khóa không bị triệt tiêu bất kể văn bản có dài bao nhiêu.

---

### Nhóm 2: Động lực Lựa chọn công nghệ

#### Câu 3: Hệ thống đã dùng mô hình học sâu ngữ nghĩa (FAISS) rất mạnh rồi, tại sao còn kéo thêm một thuật toán cổ điển so khớp từ khóa như BM25+ làm gì?
* **Trả lời phản biện:**
  * Các mô hình không gian ngữ nghĩa vector (FAISS) rất giỏi trong việc tìm kiếm theo ngữ cảnh bao quát, nhưng lại có điểm yếu là dễ làm "trôi" hoặc bỏ sót các từ khóa công nghệ mang tính đặc định, hiếm gặp hoặc chính xác phiên bản (ví dụ: `Vue3`, `Next.js 14`, `S3`, `Golang`).
  * BM25+ đóng vai trò là một bộ lọc kiểm định từ vựng (Lexical Matching) chính xác 100%. Nó có nhiệm vụ kéo các công việc chứa đích danh các từ khóa công nghệ bắt buộc này lên vị trí ưu tiên cao nhất. Hệ thống lai (Hybrid Search) kết hợp cả hai sẽ mang lại kết quả gợi ý vừa đúng gu ngữ nghĩa, vừa chuẩn công nghệ phần cứng/phần mềm.

#### Câu 4: Tại sao các em không dùng các thuật toán phổ biến như TF-IDF hay Okapi BM25 cũ mà lại chọn phiên bản BM25+?
* **Trả lời phản biện:**
  * TF-IDF bị lỗi tăng điểm tuyến tính theo tần suất từ (từ khóa lặp lại 50 lần sẽ khiến điểm số tăng vọt 50 lần một cách phi lý), gây nhiễu nặng cho luồng xử lý.
  * Okapi BM25 cũ tuy xử lý được vấn đề bão hòa bằng hàm tiệm cận nhưng lại mắc lỗi phạt quá nặng văn bản dài đã nêu ở Câu 2. Vì đặc thù dữ liệu tuyển dụng thu thập từ Kaggle/Linkedin có văn phong tự do và dung lượng từ ngữ lớn, BM25+ là biến thể cải tiến toán học phù hợp nhất cho bài toán.

---

### Nhóm 3: Kiến trúc Hệ thống lai & Tình huống thực tế

#### Câu 5: Điểm số của BM25+ là miền giá trị mở ($\ge 0$), còn điểm tương đồng của FAISS (Cosine Similarity) nằm trong khoảng $[0, 1]$. Làm sao các em có thể cộng hai thang điểm lệch nhau này lại được?
* **Trả lời phản biện:**
  * Hệ thống hoàn toàn không cộng trực tiếp hay thực hiện các phép toán đại số thô trên điểm số của hai mô hình, vì việc đó sai lệch về mặt bản chất đại lượng.
  * Thay vào đó, hệ thống sử dụng thuật toán **Hòa trộn thứ hạng nghịch đảo RRF (Reciprocal Rank Fusion)** trong file `03_hybrid_rrf.py`. RRF triệt tiêu điểm số thô và chuyển sang tính toán dựa trên vị trí xếp hạng ($Rank$) của tài liệu trong từng danh sách kết quả độc lập bằng công thức: $1 / (60 + Rank)$. Nhờ vậy, thang điểm được chuẩn hóa hoàn hảo và không bị thiên vị cho bất kỳ mô hình nào.

#### Câu 6: Nếu người dùng nhập từ khóa sai chính tả hoặc dùng từ đồng nghĩa (ví dụ: 'Học máy' thay vì 'Machine Learning'), BM25+ xử lý ra sao?
* **Trả lời phản biện:**
  * Do BM25+ hoạt động hoàn toàn dựa trên bề mặt ký tự (Lexical-only), nó sẽ trả về điểm số $0$ khi từ khóa lệch hoặc sai chính tả.
  * Tuy nhiên, đây chính là lúc sức mạnh của kiến trúc hệ thống lai (Hybrid Search) phát huy tác dụng. Khi nhánh BM25+ không tìm được kết quả, nhánh **FAISS (Semantic Search)** chạy song song dựa trên không gian vector nhúng của mô hình `SentenceTransformer` sẽ bù đắp lỗ hổng bằng cách phân tích ngữ cảnh để tìm ra vị trí công việc tương đương cho ứng viên.

---

### Mẹo nhỏ ghi điểm trước Hội đồng:
1. Luôn dùng từ khóa **"Hệ thống lai tương hỗ"** (Hybrid Search) để chứng minh tư duy thiết kế biết dùng ưu điểm mô hình này bù trừ nhược điểm mô hình kia.
2. Khi thầy cô hỏi sâu về các con số cố định như `60` trong RRF hay `1.5` trong BM25+, hãy khẳng định đây là **"Hằng số thực nghiệm tối ưu được chứng minh qua các kỳ kiểm thử chuẩn hóa khoa học quốc tế (như TREC)"**, tránh trả lời là "do nhóm tự chọn bừa".