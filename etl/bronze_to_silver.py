import io
import json
import os
import sys
import pandas as pd
from minio import Minio
from multiprocessing import Pool, cpu_count
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from nlp_utils import process_row, get_whitelist

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")


def read_kaggle() -> pd.DataFrame:
    # Đọc và merge 2 file Kaggle từ Bronze
    df_meta   = pd.read_csv(client.get_object(BUCKET, "bronze/kaggle/linkedin_job_postings.csv"))
    df_skills = pd.read_csv(client.get_object(BUCKET, "bronze/kaggle/job_skills.csv"))
    df = pd.merge(df_meta, df_skills, on="job_link")[["job_title", "job_skills"]].dropna()
    print(f"Kaggle: {len(df):,} rows")
    return df


def read_monster() -> pd.DataFrame:
    # Đọc file crawl Monster mới nhất từ Bronze
    objs  = list(client.list_objects(BUCKET, prefix="bronze/crawled/", recursive=True))
    dates = sorted(
        {o.object_name.split("/")[2] for o in objs if len(o.object_name.split("/")) >= 3},
        reverse=True
    )

    monster_list = []
    if dates:
        latest = dates[0]
        for o in objs:
            if o.object_name.startswith(f"bronze/crawled/{latest}/") and o.object_name.endswith(".json"):
                data = json.loads(client.get_object(BUCKET, o.object_name).read().decode())
                monster_list.extend(data if isinstance(data, list) else [data])

    rows = []
    for row in monster_list:
        skills = row.get("skills", [])
        if not skills:
            continue
        job_skills = ", ".join([s.strip() for s in skills if isinstance(s, str) and s.strip()])
        if not job_skills:
            continue
        rows.append({"job_title": row.get("title", ""), "job_skills": job_skills})

    df = pd.DataFrame(rows).dropna() if rows else pd.DataFrame(columns=["job_title", "job_skills"])
    print(f"Monster: {len(df):,} rows")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # Clean job_title và job_skills bằng multiprocessing
    print(f"Clean text ({cpu_count()} cores)...")
    print("  job_title  → spaCy NER + synonym + lemmatize")
    print("  job_skills → whitelist filter + lemmatize")

    rows = df[["job_title", "job_skills"]].to_dict("records")
    with Pool(cpu_count()) as p:
        results = p.map(process_row, rows)

    df["job_title"], df["job_skills"] = zip(*results)
    df["title_skills"] = df["job_title"] + " " + df["job_skills"]

    df = df[
        (df["job_title"]  != "") &
        (df["job_skills"] != "")
    ].drop_duplicates(subset=["job_title", "job_skills"]).reset_index(drop=True)

    print(f"Sau clean        : {len(df):,} rows")
    print(f"Unique job_title : {df['job_title'].nunique():,}")
    return df


def save_silver(df: pd.DataFrame):
    # Lưu Silver lên MinIO
    print("Luu Silver len MinIO...")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    client.put_object(
        bucket_name  = BUCKET,
        object_name  = "silver/Silver_Jobs_Cleaned.csv",
        data         = io.BytesIO(csv_bytes),
        length       = len(csv_bytes),
        content_type = "application/csv"
    )
    print(f"Silver xong! Shape: {df.shape}")
    print("Tiep theo: python etl/silver_to_gold.py")


if __name__ == "__main__":
    # Kiểm tra whitelist trước khi chạy
    if not get_whitelist():
        print("[LOI] Chua co whitelist!")
        print("  Chay truoc: python etl/build_skill_whitelist.py")
        sys.exit(1)

    print("[1/5] Doc Kaggle tu Bronze...")
    df_kaggle = read_kaggle()

    print("[2/5] Doc Monster tu Bronze...")
    df_monster = read_monster()

    print("[3/5] Gop 2 nguon...")
    df_all = pd.concat([df_kaggle, df_monster], ignore_index=True) \
               .dropna(subset=["job_title", "job_skills"])
    print(f"Tong: {len(df_all):,} rows")

    print("[4/5] Clean text...")
    df_all = clean_data(df_all)

    print("[5/5] Luu Silver...")
    save_silver(df_all)