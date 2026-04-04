import io, os
import pandas as pd
from minio import Minio
from multiprocessing import Pool, cpu_count
from dotenv import load_dotenv
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))
from nlp_utils import process_row

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")

# ── Kiểm tra Silver đã tồn tại chưa ───────────────────
try:
    client.stat_object(BUCKET, "silver/Silver_Jobs_Cleaned.csv")
    print("⚠ Silver đã tồn tại!")
    print("  Để update crawl mới: python spark_etl/update_silver.py")
    exit(0)
except:
    pass

# ── Đọc Kaggle từ Bronze ───────────────────────────────
print("⏳ [1/4] Đọc Kaggle từ Bronze...")
df_meta   = pd.read_csv(
    client.get_object(BUCKET,
    "bronze/kaggle/linkedin_job_postings.csv")
)
df_skills = pd.read_csv(
    client.get_object(BUCKET,
    "bronze/kaggle/job_skills.csv")
)
df_kaggle = pd.merge(df_meta, df_skills, on="job_link") \
              [["job_title", "job_skills"]] \
              .dropna()
print(f"✓ Kaggle: {len(df_kaggle):,} rows")

# ── Clean text ─────────────────────────────────────────
print(f"⏳ [2/4] Clean text ({cpu_count()} cores)...")
print("  job_title  → spaCy NER + synonym + lemmatize")
print("  job_skills → regex + synonym + lemmatize")

rows = df_kaggle[["job_title", "job_skills"]].to_dict("records")
with Pool(cpu_count()) as p:
    results = p.map(process_row, rows)

df_kaggle["job_title"],  \
df_kaggle["job_skills"] = zip(*results)

df_kaggle["title_skills"] = (
    df_kaggle["job_title"] + " " + df_kaggle["job_skills"]
)
df_kaggle = df_kaggle[
    (df_kaggle["job_title"]  != "") &
    (df_kaggle["job_skills"] != "")
].drop_duplicates(
    subset=["job_title", "job_skills"]
).reset_index(drop=True)

print(f"✓ Sau clean        : {len(df_kaggle):,} rows")
print(f"✓ Unique job_title : {df_kaggle['job_title'].nunique():,}")

# ── Lưu Silver ─────────────────────────────────────────
print("⏳ [3/4] Lưu Silver lên MinIO...")
csv_bytes = df_kaggle.to_csv(index=False).encode("utf-8")
client.put_object(
    bucket_name=BUCKET,
    object_name="silver/Silver_Jobs_Cleaned.csv",
    data=io.BytesIO(csv_bytes),
    length=len(csv_bytes),
    content_type="application/csv"
)
print(f"✓ Silver xong: {len(df_kaggle):,} rows")
print("  Tiếp theo: python spark_etl/silver_to_gold.py")