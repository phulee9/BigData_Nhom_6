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

10. Thứ tự chạy đầy đủ

```bash
python scripts/minio/create_data_lake_zones.py
python scripts/kaggle/upload_raw_to_bronze.py
python scripts/kaggle/build_silver_jobs.py
python scripts/kaggle/build_skill_mapping_with_groq.py
python scripts/kaggle/apply_skill_mapping_to_silver.py
python scripts/kaggle/build_gold_encoding.py
python scripts/kaggle/build_faiss_indexes.py
```

