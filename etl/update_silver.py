import io
import json
import os
import sys
import pickle
import numpy as np
import pandas as pd
import faiss
from minio import Minio
from multiprocessing import Pool, cpu_count
from sentence_transformers import SentenceTransformer
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from nlp_utils import process_row, get_whitelist

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DATA_DIR = Path(__file__).parent.parent / "recommendation" / "data"
TODAY    = datetime.now().strftime("%Y-%m-%d")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")


def read_new_crawl() -> pd.DataFrame:
    # Đọc file crawl mới nhất từ Bronze
    print(f"[2/5] Doc {TODAY} tu Bronze...")
    objs = list(client.list_objects(BUCKET, prefix=f"bronze/crawled/{TODAY}/", recursive=True))

    monster_list = []
    for o in objs:
        if o.object_name.endswith(".json"):
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

    df = pd.DataFrame(rows).dropna() if rows else pd.DataFrame()
    if not df.empty:
        print(f"Crawl moi: {len(df):,} jobs")
    return df


def remove_duplicates(df_new: pd.DataFrame, df_existing: pd.DataFrame) -> pd.DataFrame:
    # Loại bỏ jobs đã tồn tại trong Silver
    existing_pairs = set(zip(df_existing["job_title"], df_existing["job_skills"]))
    df_new = df_new[
        ~df_new.apply(lambda r: (r["job_title"], r["job_skills"]) in existing_pairs, axis=1)
    ].reset_index(drop=True)
    return df_new


def clean_new_jobs(df_new: pd.DataFrame) -> pd.DataFrame:
    # Clean job_title và job_skills bằng multiprocessing
    print(f"[4/5] Clean {len(df_new):,} jobs moi...")
    rows = df_new[["job_title", "job_skills"]].to_dict("records")
    with Pool(cpu_count()) as p:
        results = p.map(process_row, rows)

    df_new["job_title"], df_new["job_skills"] = zip(*results)
    df_new["title_skills"] = df_new["job_title"] + " " + df_new["job_skills"]

    df_new = df_new[
        (df_new["job_title"]  != "") &
        (df_new["job_skills"] != "")
    ].reset_index(drop=True)

    return df_new


def update_faiss(df_new: pd.DataFrame, df_updated: pd.DataFrame):
    # Encode jobs mới và append vào FAISS index hiện có
    print("[5/5] Encode + update FAISS...")
    model   = SentenceTransformer("all-MiniLM-L6-v2")
    new_emb = model.encode(
        df_new["title_skills"].tolist(),
        batch_size           = 256,
        normalize_embeddings = True,
        show_progress_bar    = True
    ).astype("float32")

    index = faiss.read_index(str(DATA_DIR / "faiss_index.bin"))
    old   = index.ntotal
    index.add(new_emb)

    faiss.write_index(index, str(DATA_DIR / "faiss_index.bin"))
    with open(DATA_DIR / "job_metadata.pkl", "wb") as f:
        pickle.dump(df_updated, f)

    print(f"FAISS: {old:,} → {index.ntotal:,} vectors")


def save_silver(df_updated: pd.DataFrame):
    # Lưu Silver đã update lên MinIO
    csv_bytes = df_updated.to_csv(index=False).encode("utf-8")
    client.put_object(
        bucket_name  = BUCKET,
        object_name  = "silver/Silver_Jobs_Cleaned.csv",
        data         = io.BytesIO(csv_bytes),
        length       = len(csv_bytes),
        content_type = "application/csv"
    )


if __name__ == "__main__":
    # Kiểm tra whitelist
    if not get_whitelist():
        print("[LOI] Chua co whitelist!")
        print("  Chay: python etl/build_skill_whitelist.py")
        sys.exit(1)

    # Kiểm tra có crawl mới không
    print(f"[1/5] Kiem tra crawl {TODAY}...")
    objs = list(client.list_objects(BUCKET, prefix=f"bronze/crawled/{TODAY}/", recursive=True))
    if not objs:
        print(f"Khong co crawl moi ngay {TODAY}")
        sys.exit(0)

    # Đọc crawl mới
    df_new = read_new_crawl()
    if df_new.empty:
        print("Khong co job hop le")
        sys.exit(0)

    # Đọc Silver hiện có và kiểm tra duplicate
    print("[3/5] Kiem tra duplicate voi Silver...")
    df_existing = pd.read_csv(client.get_object(BUCKET, "silver/Silver_Jobs_Cleaned.csv"))
    print(f"Silver hien co: {len(df_existing):,} rows")

    # Clean jobs mới
    df_new = clean_new_jobs(df_new)
    df_new = remove_duplicates(df_new, df_existing)

    if df_new.empty:
        print("Tat ca job moi da co trong Silver!")
        sys.exit(0)

    print(f"Jobs moi thuc su: {len(df_new):,}")

    # Update Silver + FAISS
    df_updated = pd.concat([df_existing, df_new], ignore_index=True)
    save_silver(df_updated)
    update_faiss(df_new, df_updated)

    print("Update xong!")
    print(f"  Them moi : {len(df_new):,} jobs")
    print(f"  Tong     : {len(df_updated):,} jobs")