# TÀI LIỆU CHUYÊN SÂU: CẤU PHẦN BM25+ (UNIFIED ROLE MODEL)

> Tài liệu này mô tả logic cốt lõi của module BM25+ trong hệ thống gợi ý kỹ năng,
> dựa trên mã nguồn thực tế tại `model_bm25.py`, `01_build_bm25.py`, `02_bm25_recommend.py`,
> `03_hybrid_rrf.py` và `hybrid_rrf.py`.

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1. Vị trí của BM25+ trong kiến trúc

Hệ thống gợi ý kỹ năng sử dụng **2 nhánh song song**:

| Nhánh | Phương pháp | Module |
|-------|------------|--------|
| **Keyword Retrieval** | BM25Plus (Lexical) | `model_bm25.py` |
| **Semantic Retrieval** | Sentence Embedding + FAISS (Dense Vector) | `recommend.py` |

Kết quả từ 2 nhánh được **kết hợp bằng Reciprocal Rank Fusion (RRF)** tại `hybrid_rrf.py` để tạo ra danh sách gợi ý cuối cùng.

```
                        ┌─────────────────────────┐
                        │    User Input            │
                        │  role + current skills   │
                        └──────────┬──────────────┘
                                   │
                     ┌─────────────┴──────────────┐
                     ▼                            ▼
            ┌────────────────┐           ┌────────────────┐
            │   BM25Plus     │           │ FAISS + Embed  │
            │  (Keyword)     │           │  (Semantic)    │
            │                │           │                │
            │ Exact token    │           │ Contextual     │
            │ matching       │           │ similarity     │
            └───────┬────────┘           └───────┬────────┘
                    │                            │
                    │  ranked skills             │  ranked skills
                    ▼                            ▼
            ┌─────────────────────────────────────────┐
            │     Reciprocal Rank Fusion (RRF)        │
            │     rrf_score = Σ 1/(k + rank_i)        │
            │                                         │
            │  Skill ở cả 2 bên → score cao hơn       │
            │  Skill chỉ 1 bên → vẫn có score         │
            └────────────────┬────────────────────────┘
                             ▼
                    Top-K Missing Skills
```

### 1.2. Dữ liệu đầu vào

BM25+ đọc dữ liệu từ **Silver Kaggle** trên MinIO:

```
Đường dẫn: silver/kaggle/jobs_silver.parquet
```

| Cột | Nguồn gốc | Vai trò |
|-----|-----------|---------|
| `title_core` | `silver_builder.py` → `title_utils.py` (lemmatize + bỏ seniority/work_mode) | Tên role đã chuẩn hóa |
| `skills_normalized` | `silver_builder.py` → `skill_mapping_applier.py` (ánh xạ qua whitelist Groq) | Danh sách skills đã chuẩn hóa |

**Pipeline xử lý dữ liệu trước khi BM25+ sử dụng:**

```
linkedin_job_postings.csv + job_skills.csv
        │
        ▼
  build_silver_jobs.py
  ├── title_raw → clean_title() → title_clean
  │   → lemmatize_titles() → title_lemma
  │   → build_title_core() → title_core   ← BM25+ dùng cột này
  ├── skills_raw → clean_skills() → skills_clean
  │   → skills_normalized = skills_clean (tạm)
        │
        ▼
  apply_skill_mapping_to_silver.py
  └── skills_clean → skill_mapping_applier → skills_normalized   ← BM25+ dùng cột này
        │
        ▼
  silver/kaggle/jobs_silver.parquet
```

---

## 2. CƠ CHẾ UNIFIED DOCUMENT MODEL

### 2.1. Tại sao gộp nhiều job thành một Document?

Đây là kỹ thuật **Document Aggregation** — gộp tất cả job có cùng `title_core` thành 1 tài liệu duy nhất cho 1 **Role**.

**Vấn đề của Item-based (1 job = 1 document):**
- Mỗi tin tuyển dụng viết rất tùy hứng (quá ngắn hoặc quá dài)
- BM25 score bị lệch bởi noise từ từng job cá biệt
- Với ~124,000 jobs → quá nhiều documents, query chậm

**Giải pháp Unified Role:**
- Gộp tất cả jobs cùng `title_core` thành 1 document
- Tạo ra "Profile chuẩn" cho mỗi role, phản ánh phân phối kỹ năng thực tế trên thị trường
- Số documents giảm từ ~124K xuống còn ~2,000-5,000 roles

### 2.2. Tokenization & Frequency Weighting

```python
# Từ model_bm25.py, hàm _build_bm25()
tokens = role_name.split() * ROLE_NAME_REPEAT    # "data engineer" → ["data", "engineer", "data", "engineer"]
for skill, count in skill_count_dict.items():
    tokens.extend(skill.split() * count)          # "python" × 90 lần → TF(python) = 90
```

| Kỹ thuật | Code | Mục đích |
|----------|------|----------|
| **Role Name Boosting** | `role.split() * 2` | Tạo "điểm neo" — khi user nhập tên role, BM25+ nhận diện đúng phân vùng ngay |
| **Skill TF Weighting** | `skill.split() * count` | Lặp lại skill theo tần suất thực tế → BM25+ tự hiểu đâu là core skill |

**Ví dụ:** Role "data engineer" có 100 jobs, trong đó 90 jobs yêu cầu Python, 30 jobs yêu cầu Go:
```
Document = ["data", "engineer", "data", "engineer",
            "python", "python", ...(×90)...,
            "go", "go", ...(×30)...,
            "sql", "sql", ...(×85)...]

→ BM25+ hiểu: python (TF=90) quan trọng hơn go (TF=30) cho role này
```

### 2.3. Lọc role rác (>= 3 jobs)

```python
role_counts = df["role"].value_counts()
valid_roles = role_counts[role_counts >= 3].index
```

Những role chỉ xuất hiện 1–2 lần thường là:
- Dữ liệu lỗi (title viết sai, quá đặc thù)
- Không mang tính đại diện cho thị trường
- Gây nhiễu cho danh sách gợi ý

→ Ngưỡng `>= 3 jobs` đảm bảo **ý nghĩa thống kê (Statistical Significance)**.

---

## 3. CÔNG THỨC TOÁN HỌC

### 3.1. BM25Plus Scoring

Với mỗi document (role), BM25Plus tính:

$$BM25Plus(Q, D) = \sum_{t \in Q} IDF(t) \cdot \left( \frac{f(t,D) \cdot (k_1 + 1)}{f(t,D) + k_1 \cdot (1 - b + b \cdot \frac{|D|}{avgdl})} + \delta \right)$$

Trong đó:
- $f(t,D)$ = term frequency của từ $t$ trong document $D$
- $k_1$ = tham số điều chỉnh bão hòa TF (mặc định 1.2–2.0)
- $b$ = tham số length normalization (mặc định 0.75)
- $\delta$ = **tham số đặc trưng của BM25+**, đảm bảo score luôn > 0

### 3.2. Recommend Score

```python
# Từ model_bm25.py, hàm query()
for doc_idx, bm25_score in matched_roles:
    job_count_role = max(self._doc_job_counts[doc_idx], 1)
    for skill, count in self._doc_skill_counts[doc_idx].items():
        if skill in user_skills_set:
            continue
        skill_scores[skill] += (count / job_count_role) * bm25_score
```

$$Skill\_Score(s) = \sum_{r \in TopK\_Roles} BM25\_Score(Query, r) \times \frac{Count(s, r)}{Total\_Jobs(r)}$$

**Ý nghĩa:** Điểm gợi ý kỹ năng kết hợp 2 yếu tố:
1. **BM25 Score** — role đó giống query bao nhiêu (lexical similarity)
2. **Skill Density** — kỹ năng đó phổ biến mức nào trong role đó (count/total_jobs)

→ Loại bỏ trường hợp một kỹ năng hiếm tình cờ xuất hiện trong role có BM25 score cao.

### 3.3. Score Normalization

```python
max_score = max(s for _, s in matched_roles)
if max_score > 0:
    matched_roles = [(idx, s / max_score) for idx, s in matched_roles]
```

Chuẩn hóa BM25 score về [0, 1] trước khi tính Skill Score → giúp ổn định kết quả khi BM25 raw score biến thiên lớn giữa các query.

---

## 4. TẠI SAO CHỌN BM25+ THAY VÌ CÁC PHƯƠNG PHÁP KHÁC?

### 4.1. So sánh TF-IDF vs BM25 vs BM25+

| Tiêu chí | TF-IDF | BM25 | BM25+ |
|----------|--------|------|-------|
| TF saturation | Không có — skill quá phổ biến dominate | Có — nhưng score có thể = 0 | Có — score luôn > 0 nhờ $\delta$ |
| Length normalization | Không | Có (tham số $b$) | Có (tham số $b$) |
| Document dài (Unified) | Score bị lệch nghiêm trọng | Score dễ bão hòa, mất phân cấp | Phân cấp rõ giữa "quan trọng" và "rất quan trọng" |
| Long-tail skills | Bị dìm bởi TF cao | Có thể bị score = 0 | Luôn có score > 0, được đánh giá công bằng |

**BM25+ được chọn vì:**
- Unified Document rất dài (hàng trăm tokens) → TF-IDF không kiểm soát được
- BM25 truyền thống có thể cho score = 0 → mất thông tin ở long-tail skills
- BM25+ với $\delta$ đảm bảo mọi skill xuất hiện đều được "ghi nhận", chỉ khác ở mức độ

### 4.2. So sánh BM25+ vs FAISS (Embedding)

| Tiêu chí | BM25+ (Keyword) | FAISS (Semantic) |
|----------|-----------------|------------------|
| **Nguyên lý** | Exact token matching + TF weighting | Dense vector similarity (cosine) |
| **Điểm mạnh** | Chính xác tuyệt đối với keyword match | Hiểu ngữ nghĩa — "ML" ≈ "Machine Learning" |
| **Điểm yếu** | Không hiểu synonyms — "ML" ≠ "Machine Learning" | Có thể match sai do semantic drift |
| **Tốc độ query** | ~1ms (BM25 trên vài nghìn documents) | ~10-50ms (FAISS approximate search) |
| **Memory** | Nhẹ — chỉ cần inverted index | Nặng — embedding matrix + FAISS index |
| **Dữ liệu cần** | Chỉ cần text tokens | Cần pre-trained embedding model |
| **Phù hợp khi** | User biết rõ keyword ("python", "sql") | User mô tả mơ hồ ("data processing") |

### 4.3. Vấn đề cụ thể mà BM25+ giải quyết được mà FAISS không

1. **Exact Skill Matching:**
   - User có skill "Power BI" → BM25+ match chính xác với jobs yêu cầu "Power BI"
   - FAISS có thể nhầm "Power BI" ≈ "Tableau" (gần trong embedding space)

2. **Frequency Awareness:**
   - BM25+ biết "Python xuất hiện trong 90/100 jobs của Data Engineer" → gợi ý với confidence cao
   - FAISS chỉ biết "Python gần Data Engineer trong vector space" mà không biết tần suất

3. **Zero-shot cho skill mới:**
   - Một skill mới (vd: "Polars") xuất hiện trong 5 job descriptions
   - BM25+ lập tức match được khi rebuild (vì chỉ cần token match)
   - FAISS cần embedding model đã được train biết "Polars" → có thể miss

4. **Transparency (Giải thích được kết quả):**
   - BM25+ score phân tách rõ ràng: "role match score × skill density"
   - Embedding score là 1 con số duy nhất, không giải thích được tại sao

5. **Keyword-sensitive domains:**
   - Trong IT/Tech, skill names rất cụ thể: "PostgreSQL" ≠ "MySQL" ≠ "MongoDB"
   - Embedding thường đặt chúng gần nhau (đều là database), nhưng thực tế đây là những kỹ năng khác nhau
   - BM25+ phân biệt chính xác 100%

---

## 5. HẠN CHẾ CỦA BM25+

### 5.1. Hạn chế cố hữu

| Hạn chế | Ví dụ | Mức ảnh hưởng |
|---------|-------|---------------|
| **Không hiểu synonyms** | "ML" vs "Machine Learning" → BM25+ coi là khác nhau | Trung bình — đã giảm nhờ `skills_normalized` chuẩn hóa từ Groq |
| **Không hiểu ngữ cảnh** | "Java" (programming) vs "Java" (island) | Thấp — trong domain IT, context rõ ràng |
| **Vocabulary mismatch** | User gõ "data viz" nhưng data có "data visualization" | Trung bình — giảm nhờ `normalize_text_lower()` |
| **Cold start** | Role/skill mới chưa có trong data → không gợi ý được | Cao — cần rebuild khi có data mới |
| **Phụ thuộc data quality** | Nếu Silver data có skill lỗi → gợi ý sai | Cao — đã giảm nhờ Groq skill mapping |

### 5.2. Cách giải quyết hạn chế qua Hybrid RRF

| Hạn chế BM25+ | FAISS bù đắp như thế nào |
|----------------|--------------------------|
| Không hiểu synonyms | Embedding model hiểu "ML" ≈ "Machine Learning" |
| Vocabulary mismatch | Embedding match theo nghĩa, không cần exact token |
| Ngữ cảnh mơ hồ | Embedding nắm bắt context từ pre-trained model |

| Hạn chế FAISS | BM25+ bù đắp như thế nào |
|----------------|--------------------------|
| Semantic drift (match sai) | BM25+ anchor lại bằng exact keyword |
| Không biết tần suất | BM25+ tính chính xác skill density |
| Black-box score | BM25+ cung cấp interpretable score |

→ **Hybrid RRF kết hợp 2 bên** tạo ra kết quả tốt hơn cả 2 bên đứng riêng.

---

## 6. HYBRID RRF — CƠ CHẾ KẾT HỢP

### 6.1. Công thức RRF

```python
# Từ hybrid_rrf.py
rrf_score[skill] = Σ 1 / (k + rank_i)
```

$$RRF\_Score(s) = \sum_{r \in \{BM25, EMB\}} \frac{1}{k + rank_r(s)}$$

Với $k = 60$ (hằng số chuẩn trong Information Retrieval literature).

### 6.2. Tính chất của RRF

| Tính chất | Giải thích |
|-----------|------------|
| **Rank-based, không phải score-based** | Không phụ thuộc vào scale khác nhau giữa BM25 score và cosine similarity |
| **Skill ở cả 2 bên → boost mạnh** | RRF score = 1/(k+r₁) + 1/(k+r₂) > chỉ 1 bên |
| **Skill chỉ 1 bên → vẫn có mặt** | Không bị mất hoàn toàn, chỉ score thấp hơn |
| **Parameter-free** | Chỉ có k=60, không cần tune nhiều hyperparams |
| **Robust** | Không bị dominate bởi 1 retriever nào |

### 6.3. Ví dụ cụ thể

User query: `role="data engineer"`, `skills=["python", "sql"]`

| Skill | BM25+ rank | FAISS rank | RRF score | Nhận xét |
|-------|-----------|-----------|-----------|----------|
| Apache Spark | #1 | #2 | 1/61 + 1/62 = 0.0326 | Cả 2 bên đồng ý → score cao nhất |
| Airflow | #3 | #5 | 1/63 + 1/65 = 0.0312 | Đồng thuận |
| Docker | #2 | — | 1/62 = 0.0161 | Chỉ BM25+ thấy → vẫn có score |
| ETL Design | — | #1 | 1/61 = 0.0164 | Chỉ FAISS thấy (semantic match) |

---

## 7. QUY TRÌNH VẬN HÀNH

### 7.1. Offline: Build Model

```bash
python scripts/recommend/01_build_bm25.py
```

```
1. load_from_minio()
   → Đọc silver/kaggle/jobs_silver.parquet từ MinIO
   → Cột: title_core, skills_normalized

2. _build_bm25()
   → Normalize text, parse skills
   → Lọc role >= 3 jobs
   → Group by role → skill_count_dict
   → Build token arrays
   → BM25Plus.fit(corpus)

3. upload_pickle()
   → Serialize toàn bộ BM25PlusRecommender
   → Upload lên MinIO tại gold/kaggle/bm25/bm25_model.pkl
```

### 7.2. Online: Query

```bash
python scripts/recommend/02_bm25_recommend.py
```

```
1. download_pickle() → Deserialize BM25PlusRecommender
   → Không cần rebuild, sẵn sàng query ngay

2. query(target_role, user_skills, top_k)
   → Tokenize query
   → BM25+ get_scores()
   → Top matched roles
   → Extract & filter missing skills
   → Return list[dict] {skill, recommend_score, job_count}
```

**Tốc độ Query:** ~1-5ms (deserialize 1 lần, query nhiều lần)

### 7.3. Hybrid: BM25+ + FAISS

```bash
python scripts/recommend/03_hybrid_rrf.py
```

```
1. Load BM25+ model (pickle từ MinIO)
2. Load Embedding model + FAISS indexes
3. User nhập role + skills
4. BM25+ query → ranked missing skills
5. FAISS query → ranked missing skills
6. RRF fusion → combined ranking
7. Output: Top-K hybrid missing skills
```

---

## 8. CÂU HỎI PHẢN BIỆN

### ❓ Q1: Tại sao không dùng FAISS luôn cho cả 2 nhánh?

**Trả lời:** FAISS (Dense Retrieval) có 2 điểm yếu mà BM25+ khắc phục:
- **Semantic drift:** Embedding có thể đặt "PostgreSQL" và "MongoDB" gần nhau vì cùng là database, nhưng thực tế đây là 2 skill khác nhau. BM25+ phân biệt chính xác.
- **Frequency blindness:** FAISS chỉ biết "gần" hay "xa" trong vector space, không biết "Python xuất hiện trong 90% jobs". BM25+ nắm bắt chính xác tần suất từ dữ liệu.

### ❓ Q2: Nếu user gõ sai keyword thì sao?

**Trả lời:** BM25+ sẽ miss vì exact match thất bại. Nhưng FAISS sẽ bắt được qua semantic similarity. Đây chính là lý do cần Hybrid — 2 nhánh bù đắp cho nhau.

### ❓ Q3: BM25+ có handle được tiếng Việt không?

**Trả lời:** Hệ thống hiện tại xử lý dữ liệu tiếng Anh (Kaggle LinkedIn Jobs). BM25+ hoạt động trên word-level tokenization, nên nếu mở rộng sang tiếng Việt cần thêm word segmentation (vd: VnCoreNLP). Tuy nhiên, domain IT/Tech chủ yếu dùng thuật ngữ tiếng Anh ("Python", "SQL"), nên ảnh hưởng thấp.

### ❓ Q4: Tại sao serialize bằng pickle mà không dùng database?

**Trả lời:** Pickle cho phép lưu trọn vẹn trạng thái BM25Plus (inverted index, TF counts, IDF weights) trong 1 file duy nhất. Khi load lại, hệ thống query ngay mà không cần rebuild. MinIO đóng vai trò Data Lake, cho phép versioning model — rollback về phiên bản cũ nếu cần.

### ❓ Q5: Data tăng lên hàng triệu bản ghi thì sao?

**Trả lời:**
- BM25+ build trên **role-level** (unified document), không phải job-level. Dù 10 triệu jobs, số roles vẫn chỉ khoảng 5,000-10,000 → BM25+ vẫn nhanh.
- Build time tăng tuyến tính theo số jobs (group by + count), nhưng query time gần như không đổi (BM25 search trên vài nghìn documents).
- Nếu cần scale hơn nữa, chỉ cần chạy lại script build trên cụm Spark/Worker, upload pickle mới lên MinIO → hệ thống tự động cập nhật.

### ❓ Q6: Tại sao gợi ý skill mà không gợi ý job?

**Trả lời:** BM25+ được thiết kế chuyên biệt cho **skill gap analysis** — giúp user biết cần học thêm gì. Việc gợi ý job phù hợp được xử lý bởi nhánh FAISS (semantic search trên job-level). Hai nhánh phục vụ 2 mục đích khác nhau:
- **FAISS:** "Job nào phù hợp với bạn?" (job-level ranking)
- **BM25+:** "Bạn cần học thêm skill gì?" (skill-level aggregation)

### ❓ Q7: RRF với k=60 có tối ưu không?

**Trả lời:** k=60 là giá trị chuẩn trong Information Retrieval literature (Cormack et al., 2009). Giá trị này đã được chứng minh robust trên nhiều benchmark. Hệ thống không cần tune k vì RRF bản chất là parameter-free — chỉ dựa trên rank, không phụ thuộc vào scale của score.

---

## 9. CẤU TRÚC MÃ NGUỒN

| File | Vai trò |
|------|---------|
| `src/recommendation/core/model_bm25.py` | BM25PlusRecommender class — build & query |
| `src/recommendation/core/hybrid_rrf.py` | reciprocal_rank_fusion() — kết hợp BM25+ và FAISS |
| `src/recommendation/utils/text.py` | normalize_text_lower(), parse_skills_lower() — tiện ích text |
| `scripts/recommend/01_build_bm25.py` | Build model từ MinIO → pickle → upload |
| `scripts/recommend/02_bm25_recommend.py` | Load pickle → interactive query |
| `scripts/recommend/03_hybrid_rrf.py` | Hybrid: BM25+ + FAISS + RRF |

### Cấu hình chính (trong `model_bm25.py`)

```python
SILVER_KAGGLE_JOBS = "silver/kaggle/jobs_silver.parquet"   # Đường dẫn Silver trên MinIO
COL_TITLE = "title_core"                                   # Cột title trong Silver
COL_SKILLS = "skills_normalized"                            # Cột skills trong Silver

SCORE_THRESHOLD = 0.0      # Ngưỡng BM25 score tối thiểu
MAX_SIMILAR_ROLES = 10     # Số roles tương tự để extract skills
ROLE_NAME_REPEAT = 2       # Lặp role name bao nhiêu lần trong document
```
