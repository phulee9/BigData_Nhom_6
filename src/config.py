import os
from pathlib import Path

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

LOCAL_CRAWLER_RAW_DIR = Path(
    os.getenv("LOCAL_CRAWLER_RAW_DIR", "data/raw/crawler")
)


# File raw Kaggle trên local
LOCAL_KAGGLE_JOB_POSTINGS = (
    f"{LOCAL_RAW_DIR}/kaggle/linkedin_job_postings.csv"
)

LOCAL_KAGGLE_JOB_SKILLS = (
    f"{LOCAL_RAW_DIR}/kaggle/job_skills.csv"
)


# Các vùng cố định trên MinIO
MINIO_ZONES = [
    "bronze/kaggle/raw/",
    "bronze/crawler/raw/",

    "silver/kaggle/01_normalized/",
    "silver/kaggle/02_basic_clean/",
    "silver/kaggle/03_preclassified/",
    "silver/kaggle/04_industry_clean/",
    "silver/kaggle/05_final_clean/",

    "silver/crawler/",

    "gold/kaggle/encode/",
    "gold/crawler/batches/",
    "gold/crawler/encode/",

    "taxonomy/",

    "audit/kaggle/",
    "audit/crawler/",
]


# Đường dẫn Bronze Kaggle
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


# Hàm lấy file crawler mới nhất ở local
def get_latest_crawler_file() -> Path:
    # Lấy file json mới nhất trong thư mục data/raw/crawler
    json_files = sorted(
        LOCAL_CRAWLER_RAW_DIR.glob("*.json"),
        key=lambda file_path: file_path.stat().st_mtime,
        reverse=True,
    )

    if not json_files:
        raise FileNotFoundError(
            f"Không tìm thấy file .json trong {LOCAL_CRAWLER_RAW_DIR}"
        )

    return json_files[0]


def get_batch_name_from_file(file_path: Path) -> str:
    # Lấy batch name từ tên file
    return file_path.stem


# Đường dẫn Bronze Crawler theo batch
def bronze_crawler_raw(batch_name: str) -> str:
    return f"bronze/crawler/raw/{batch_name}/jobs_raw.json"


# Đường dẫn Silver Crawler theo batch
def silver_crawler_normalized(batch_name: str) -> str:
    return f"silver/crawler/{batch_name}/01_normalized/jobs_normalized.parquet"


def silver_crawler_basic_clean(batch_name: str) -> str:
    return f"silver/crawler/{batch_name}/02_basic_clean/jobs_basic_clean.parquet"


def silver_crawler_preclassified(batch_name: str) -> str:
    return f"silver/crawler/{batch_name}/03_preclassified/jobs_preclassified.parquet"


def silver_crawler_industry_clean(batch_name: str) -> str:
    return f"silver/crawler/{batch_name}/04_industry_clean/jobs_industry_clean.parquet"


def silver_crawler_final_clean(batch_name: str) -> str:
    return f"silver/crawler/{batch_name}/05_final_clean/jobs_final_clean.parquet"


# Đường dẫn Gold Crawler theo batch
def gold_crawler_jobs_for_encoding_batch(batch_name: str) -> str:
    return f"gold/crawler/batches/{batch_name}/jobs_for_encoding.parquet"


# Đường dẫn Gold Crawler chính dùng cho recommendation
GOLD_CRAWLER_METADATA = (
    "gold/crawler/encode/metadata.parquet"
)

GOLD_CRAWLER_TITLE_EMBEDDINGS = (
    "gold/crawler/encode/title_embeddings.npy"
)

GOLD_CRAWLER_SKILLS_EMBEDDINGS = (
    "gold/crawler/encode/skills_embeddings.npy"
)

GOLD_CRAWLER_FULL_EMBEDDINGS = (
    "gold/crawler/encode/full_embeddings.npy"
)

GOLD_CRAWLER_TITLE_INDEX = (
    "gold/crawler/encode/title.faiss.index"
)

GOLD_CRAWLER_SKILLS_INDEX = (
    "gold/crawler/encode/skills.faiss.index"
)

GOLD_CRAWLER_FULL_INDEX = (
    "gold/crawler/encode/full.faiss.index"
)


# Đường dẫn runtime index local
LOCAL_KAGGLE_RUNTIME_INDEX_DIR = (
    f"{LOCAL_RUNTIME_INDEX_DIR}/kaggle"
)

LOCAL_CRAWLER_RUNTIME_INDEX_DIR = (
    f"{LOCAL_RUNTIME_INDEX_DIR}/crawler"
)


# Đường dẫn Taxonomy
TAXONOMY_OCCUPATION = "taxonomy/occupation_taxonomy.parquet"
TAXONOMY_TITLE_ALIAS = "taxonomy/title_alias.parquet"
TAXONOMY_SKILL = "taxonomy/skill_taxonomy.parquet"
TAXONOMY_SKILL_ALIAS = "taxonomy/skill_alias.parquet"


# Đường dẫn Audit Kaggle
AUDIT_KAGGLE_LOW_CONFIDENCE = (
    "audit/kaggle/low_confidence_jobs.parquet"
)

AUDIT_KAGGLE_UNMAPPED_TITLES = (
    "audit/kaggle/unmapped_titles.parquet"
)

AUDIT_KAGGLE_UNMAPPED_SKILLS = (
    "audit/kaggle/unmapped_skills.parquet"
)


# Đường dẫn Audit Crawler theo batch
def audit_crawler_low_confidence(batch_name: str) -> str:
    return f"audit/crawler/{batch_name}/low_confidence_jobs.parquet"


def audit_crawler_unmapped_titles(batch_name: str) -> str:
    return f"audit/crawler/{batch_name}/unmapped_titles.parquet"


def audit_crawler_unmapped_skills(batch_name: str) -> str:
    return f"audit/crawler/{batch_name}/unmapped_skills.parquet"


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

# PostgreSQL config for Power BI mart
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "bigdata")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

POSTGRES_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# PostgreSQL config for Power BI mart
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "bigdata")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

POSTGRES_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Groq config for CV extraction
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)
