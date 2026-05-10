import os
from dotenv import load_dotenv

# Đọc biến môi trường từ file .env
load_dotenv()


# Cấu hình MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "bigdata-nhom6")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


# Đường dẫn local
LOCAL_RAW_DIR = "data/raw"
LOCAL_RUNTIME_INDEX_DIR = "data/runtime_index"
LOCAL_TEMP_DIR = "data/temp"


# File raw Kaggle trên local
LOCAL_KAGGLE_JOB_POSTINGS = (
    f"{LOCAL_RAW_DIR}/kaggle/linkedin_job_postings.csv"
)

LOCAL_KAGGLE_JOB_SKILLS = (
    f"{LOCAL_RAW_DIR}/kaggle/job_skills.csv"
)


# Các vùng trên MinIO
MINIO_ZONES = [
    "bronze/kaggle/raw/",
    "bronze/crawler/raw/",

    "silver/kaggle/01_normalized/",
    "silver/kaggle/02_basic_clean/",
    "silver/kaggle/03_preclassified/",
    "silver/kaggle/04_industry_clean/",
    "silver/kaggle/05_final_clean/",

    "silver/crawler/01_normalized/",
    "silver/crawler/02_basic_clean/",
    "silver/crawler/03_preclassified/",
    "silver/crawler/04_industry_clean/",
    "silver/crawler/05_final_clean/",

    "gold/kaggle/encode/",
    "gold/crawler/encode/",

    "taxonomy/",

    "audit/kaggle/",
    "audit/crawler/",
]


# Đường dẫn Bronze
BRONZE_KAGGLE_JOB_POSTINGS = (
    "bronze/kaggle/raw/linkedin_job_postings.csv"
)

BRONZE_KAGGLE_JOB_SKILLS = (
    "bronze/kaggle/raw/job_skills.csv"
)


# Đường dẫn Silver Kaggle
SILVER_KAGGLE_NORMALIZED = (
    "silver/kaggle/01_normalized/jobs_normalized.parquet"
)

SILVER_KAGGLE_BASIC_CLEAN = (
    "silver/kaggle/02_basic_clean/jobs_basic_clean.parquet"
)

SILVER_KAGGLE_PRECLASSIFIED = (
    "silver/kaggle/03_preclassified/jobs_preclassified.parquet"
)

SILVER_KAGGLE_INDUSTRY_CLEAN = (
    "silver/kaggle/04_industry_clean/jobs_industry_clean.parquet"
)

SILVER_KAGGLE_FINAL_CLEAN = (
    "silver/kaggle/05_final_clean/jobs_final_clean.parquet"
)


# Đường dẫn Silver Crawler
SILVER_CRAWLER_NORMALIZED = (
    "silver/crawler/01_normalized/jobs_normalized.parquet"
)

SILVER_CRAWLER_BASIC_CLEAN = (
    "silver/crawler/02_basic_clean/jobs_basic_clean.parquet"
)

SILVER_CRAWLER_PRECLASSIFIED = (
    "silver/crawler/03_preclassified/jobs_preclassified.parquet"
)

SILVER_CRAWLER_INDUSTRY_CLEAN = (
    "silver/crawler/04_industry_clean/jobs_industry_clean.parquet"
)

SILVER_CRAWLER_FINAL_CLEAN = (
    "silver/crawler/05_final_clean/jobs_final_clean.parquet"
)


# Đường dẫn Gold Kaggle
GOLD_KAGGLE_JOBS_FOR_ENCODING = (
    "gold/kaggle/encode/jobs_for_encoding.parquet"
)

GOLD_KAGGLE_METADATA = (
    "gold/kaggle/encode/metadata.parquet"
)

GOLD_KAGGLE_TITLE_EMBEDDINGS = (
    "gold/kaggle/encode/title_embeddings.npy"
)

GOLD_KAGGLE_SKILLS_EMBEDDINGS = (
    "gold/kaggle/encode/skills_embeddings.npy"
)

GOLD_KAGGLE_FULL_EMBEDDINGS = (
    "gold/kaggle/encode/full_embeddings.npy"
)

GOLD_KAGGLE_TITLE_INDEX = (
    "gold/kaggle/encode/title.faiss.index"
)

GOLD_KAGGLE_SKILLS_INDEX = (
    "gold/kaggle/encode/skills.faiss.index"
)

GOLD_KAGGLE_FULL_INDEX = (
    "gold/kaggle/encode/full.faiss.index"
)

# Đường dẫn Gold Crawler
GOLD_CRAWLER_JOBS_FOR_ENCODING = (
    "gold/crawler/encode/jobs_for_encoding.parquet"
)

GOLD_CRAWLER_EMBEDDINGS = (
    "gold/crawler/encode/embeddings.npy"
)

GOLD_CRAWLER_FAISS_INDEX = (
    "gold/crawler/encode/faiss.index"
)

GOLD_CRAWLER_METADATA = (
    "gold/crawler/encode/metadata.parquet"
)


# Đường dẫn Taxonomy
TAXONOMY_OCCUPATION = "taxonomy/occupation_taxonomy.parquet"
TAXONOMY_TITLE_ALIAS = "taxonomy/title_alias.parquet"
TAXONOMY_SKILL = "taxonomy/skill_taxonomy.parquet"
TAXONOMY_SKILL_ALIAS = "taxonomy/skill_alias.parquet"


# Đường dẫn Audit
AUDIT_KAGGLE_LOW_CONFIDENCE = (
    "audit/kaggle/low_confidence_jobs.parquet"
)

AUDIT_KAGGLE_UNMAPPED_TITLES = (
    "audit/kaggle/unmapped_titles.parquet"
)

AUDIT_KAGGLE_UNMAPPED_SKILLS = (
    "audit/kaggle/unmapped_skills.parquet"
)

AUDIT_CRAWLER_LOW_CONFIDENCE = (
    "audit/crawler/low_confidence_jobs.parquet"
)

AUDIT_CRAWLER_UNMAPPED_TITLES = (
    "audit/crawler/unmapped_titles.parquet"
)

AUDIT_CRAWLER_UNMAPPED_SKILLS = (
    "audit/crawler/unmapped_skills.parquet"
)

# Cấu hình embedding
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

EMBEDDING_BATCH_SIZE = int(
    os.getenv("EMBEDDING_BATCH_SIZE", "128")
)

NORMALIZE_EMBEDDINGS = (
    os.getenv("NORMALIZE_EMBEDDINGS", "true").lower() == "true"
)