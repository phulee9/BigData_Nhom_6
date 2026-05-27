Hướng dẫn chạy pipeline Kaggle Jobs Skills Recommendation

1. Cài thư viện

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```


2. Cấu hình file `.env`

Tạo file `.env` ở thư mục gốc project:

Nếu chạy ngoài Docker thì đổi:

```env
MINIO_ENDPOINT=localhost:9000
```

3. Tạo bucket và các vùng data lake trên MinIO

Chạy file:

```bash
python scripts/minio/create_data_lake_zones.py
```

File này dùng để tạo bucket và các vùng/folder trên MinIO

Sau khi chạy xong, kiểm tra trên MinIO bucket:


4. Upload dữ liệu thô lên Bronze

Đặt 2 file raw ở local, ví dụ:

```text
data/raw/linkedin_job_postings.csv
data/raw/job_skills.csv
```

Sau đó chạy file upload dữ liệu thô:

```bash
python scripts/kaggle/upload_raw_to_bronze.py
```

File này dùng để upload dữ liệu lên đúng path:

```text
bronze/kaggle/linkedin_job_postings.csv
bronze/kaggle/job_skills.csv
```


5. Build Silver tạm

```bash
python scripts/kaggle/build_silver_jobs.py
```

File này dùng để:

```text
Đọc dữ liệu từ bronze/kaggle/
Join job_postings + job_skills
Loại duplicate job_link
Loại job thiếu title hoặc skills
Clean title
Clean skills
Xử lý title bằng spaCy
Tạo jobs_silver.parquet
```

Output:

```text
silver/kaggle/jobs_silver.parquet
```

Ở bước này:

```text
skills_normalized = skills_clean
```

6. Tạo skill mapping bằng Groq(có thể không cần chạy vì tốn rất nhiều groq,liên hệ tôi đẻ gửi luôn kết quả bước này)

```bash
python scripts/kaggle/build_skill_mapping_with_groq.py
```

File này dùng để:

```text
Đọc silver/kaggle/jobs_silver.parquet
Lấy skills_clean
Đếm unique skills
Lọc skills có freq >= 200 và word_count <= 4
Gửi skills lên Groq theo batch
Tạo skill_alias_mapping.csv
Tạo skill_whitelist.csv
```

Output:

```text
data/mapping/skill_alias_mapping.csv
data/mapping/skill_whitelist.csv
```

7. Apply skill mapping vào Silver

```bash
python scripts/kaggle/apply_skill_mapping_to_silver.py
```

File này dùng để:

```text
Đọc silver/kaggle/jobs_silver.parquet
Đọc data/mapping/skill_alias_mapping.csv
Chuẩn hóa skills_clean thành skills_normalized
Upload lại jobs_silver.parquet lên Silver
```

Output:

```text
silver/kaggle/jobs_silver.parquet
```

Sau bước này, Silver là bản final.

8. Build dữ liệu Gold để encode

```bash
python scripts/kaggle/build_gold_encoding.py
```

File này dùng để:

```text
Đọc Silver final
Loại dòng có title_core rỗng
Loại dòng có skills_normalized rỗng
Tạo doc_id
Tạo title_text
Tạo skills_text
```

Output:

```text
gold/kaggle/jobs_for_encoding.parquet
```

9. Encode title và skills, build FAISS index

```bash
python scripts/kaggle/build_faiss_indexes.py
```

File này dùng để:

```text
Đọc gold/kaggle/jobs_for_encoding.parquet
Encode title_text
Encode skills_text
Tạo metadata dùng chung
Build FAISS index cho title
Build FAISS index cho skills
```

Output:

```text
gold/kaggle/metadata/jobs_metadata.parquet
gold/kaggle/embeddings/title_embeddings.npy
gold/kaggle/embeddings/skills_embeddings.npy
gold/kaggle/index/title_faiss.index
gold/kaggle/index/skills_faiss.index
```

10. Thứ tự chạy pipeline đầy đủ (Bronze → Silver → Gold → FAISS)

```bash
python scripts/minio/create_data_lake_zones.py
python scripts/kaggle/upload_raw_to_bronze.py
python scripts/kaggle/build_silver_jobs.py
python scripts/kaggle/build_skill_mapping_with_groq.py
python scripts/kaggle/apply_skill_mapping_to_silver.py
python scripts/kaggle/build_gold_encoding.py
python scripts/kaggle/build_faiss_indexes.py
```


---

PHẦN 2: CHẠY RECOMMENDATION

11. Build BM25+ model

```bash
python scripts/recommend/01_build_bm25.py
```

File này dùng để:

```text
Đọc silver/kaggle/jobs_silver.parquet từ MinIO
Mỗi role (title_core) = 1 document
Nội dung document = tên role + tất cả skills
Fit BM25Plus trên tất cả documents
Upload model (pickle) lên MinIO
```

Output:

```text
gold/kaggle/bm25/bm25_model.pkl (trên MinIO)
```

12. Chuẩn bị data runtime index cho FAISS Embedding

Sau khi chạy xong bước 9, copy các file từ MinIO về local:

```text
data/runtime_index/kaggle/
├── jobs_metadata.parquet       ← từ gold/kaggle/metadata/jobs_metadata.parquet
├── title_faiss.index           ← từ gold/kaggle/index/title_faiss.index
└── skills_faiss.index          ← từ gold/kaggle/index/skills_faiss.index
```

Lưu ý:
- Tên file có thể là title_faiss.index hoặc title.faiss.index đều được
- Tên metadata có thể là jobs_metadata.parquet hoặc metadata.parquet đều được
- Hệ thống dùng 2 FAISS index: title + skills

13. Chạy Recommendation

Có 3 cách chạy:

13a. BM25+ standalone (chỉ keyword matching)

```bash
python scripts/recommend/02_bm25_recommend.py
```

Cách hoạt động:

```text
Load BM25+ model (pickle) từ MinIO
User nhập role + skills
BM25+ tính score cho từng document
Tìm Top 10 roles tương tự
Extract missing skills từ matched roles
```

Yêu cầu:
- MinIO phải đang chạy
- Đã có file gold/kaggle/bm25/bm25_model.pkl trên MinIO (chạy bước 11)

13b. Embedding standalone (FAISS semantic search)

```bash
python scripts/recommend/run_recommend.py
```

Cách hoạt động:

```text
Load SentenceTransformer model (all-MiniLM-L6-v2)
Load 2 FAISS indexes từ data/runtime_index/kaggle/
User nhập role + skills (hoặc upload CV PDF)
Encode query thành vectors
FAISS tìm Top 300 jobs gần nhất
Rerank bằng: semantic score + title fuzzy + skill overlap
Trả về Top 10 jobs + Top 10 missing skills
```

Yêu cầu:
- Đã có data trong data/runtime_index/kaggle/ (xem bước 12)

13c. Hybrid RRF (kết hợp BM25+ và Embedding)

```bash
python scripts/recommend/03_hybrid_rrf.py
```

Cách hoạt động:

```text
Load BM25+ model từ MinIO
Load Embedding model + FAISS indexes từ local
User nhập role + skills
Chạy song song 2 pipeline:
  - BM25+: keyword matching → Top 10 missing skills
  - Embedding: semantic search → Top 10 missing skills
RRF Fusion: kết hợp 2 danh sách bằng công thức
  rrf_score = Σ 1/(60 + rank)
Skill xuất hiện ở cả 2 bên → score cao hơn
Trả về Top 10 hybrid missing skills
```

Yêu cầu:
- MinIO phải đang chạy (cho BM25+)
- Đã có file gold/kaggle/bm25/bm25_model.pkl trên MinIO (chạy bước 11)
- Đã có data trong data/runtime_index/kaggle/ (xem bước 12)


14. Tổng hợp vị trí data

Data trên MinIO:

```text
bronze/kaggle/linkedin_job_postings.csv    ← Raw data
bronze/kaggle/job_skills.csv               ← Raw data
silver/kaggle/jobs_silver.parquet          ← Data đã clean
gold/kaggle/jobs_for_encoding.parquet      ← Data để encode
gold/kaggle/metadata/jobs_metadata.parquet  ← Metadata job
gold/kaggle/embeddings/title_embeddings.npy ← Title vectors
gold/kaggle/embeddings/skills_embeddings.npy ← Skills vectors
gold/kaggle/index/title_faiss.index        ← FAISS index title
gold/kaggle/index/skills_faiss.index       ← FAISS index skills
gold/kaggle/bm25/bm25_model.pkl           ← BM25+ model
```

Data trên local:

```text
data/raw/linkedin_job_postings.csv         ← Raw CSV gốc
data/raw/job_skills.csv                    ← Raw CSV gốc
data/mapping/skill_alias_mapping.csv       ← Skill mapping (Groq)
data/mapping/skill_whitelist.csv           ← Skill whitelist (Groq)
data/runtime_index/kaggle/                 ← FAISS runtime index
  ├── jobs_metadata.parquet
  ├── title_faiss.index
  └── skills_faiss.index
```

15. Thứ tự chạy đầy đủ (pipeline + recommendation)

```bash
# Pipeline data
python scripts/minio/create_data_lake_zones.py
python scripts/kaggle/upload_raw_to_bronze.py
python scripts/kaggle/build_silver_jobs.py
python scripts/kaggle/build_skill_mapping_with_groq.py
python scripts/kaggle/apply_skill_mapping_to_silver.py
python scripts/kaggle/build_gold_encoding.py
python scripts/kaggle/build_faiss_indexes.py

# Build models
python scripts/recommend/01_build_bm25.py

# Copy FAISS data từ MinIO về data/runtime_index/kaggle/

# Chạy recommendation (chọn 1 trong 3)
python scripts/recommend/02_bm25_recommend.py
python scripts/recommend/run_recommend.py
python scripts/recommend/03_hybrid_rrf.py
```
