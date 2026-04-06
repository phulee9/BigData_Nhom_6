import io, json, os, pickle
import numpy as np
import pandas as pd
import faiss
from minio import Minio
from multiprocessing import Pool, cpu_count
from sentence_transformers import SentenceTransformer
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))
from nlp_utils import process_row, get_whitelist

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent / "recomendation_system"
TODAY    = datetime.now().strftime("%Y-%m-%d")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")

if __name__ == "__main__":

    # Kiểm tra whitelist
    whitelist = get_whitelist()
    if not whitelist:
        print("Chưa có whitelist!")
        print("  Chạy: python spark_etl/build_skill_whitelist.py")
        exit(1)

    # ── Kiểm tra crawl mới ────────────────────────────
    print(f"[1/5] Kiểm tra crawl {TODAY}...")
    objs = list(client.list_objects(
        BUCKET,
        prefix=f"bronze/crawled/{TODAY}/",
        recursive=True
    ))
    if not objs:
        print(f"⚠ Không có crawl mới ngày {TODAY}")
        exit(0)

    # ── Đọc crawl mới ────────────────────────────────
    print(f"[2/5] Đọc {len(objs)} file crawl...")
    monster_list = []
    for o in objs:
        if o.object_name.endswith(".json"):
            data = json.loads(
                client.get_object(
                    BUCKET, o.object_name
                ).read().decode()
            )
            monster_list.extend(
                data if isinstance(data, list) else [data]
            )

    rows_new = []
    for row in monster_list:
        skills = row.get("skills", [])
        if not skills:
            continue
        job_skills = ", ".join([
            s.strip() for s in skills
            if isinstance(s, str) and s.strip()
        ])
        if not job_skills:
            continue
        rows_new.append({
            "job_title":  row.get("title", ""),
            "job_skills": job_skills
        })

    df_new = pd.DataFrame(rows_new).dropna() \
               if rows_new else pd.DataFrame()

    if df_new.empty:
        print("Không có job hợp lệ")
        exit(0)

    print(f" Crawl mới: {len(df_new):,} jobs")

    # ── Đọc Silver hiện có ───────────────────────────
    print("[3/5] Kiểm tra duplicate với Silver...")
    df_existing = pd.read_csv(
        client.get_object(BUCKET, "silver/Silver_Jobs_Cleaned.csv")
    )
    existing_pairs = set(
        zip(df_existing["job_title"], df_existing["job_skills"])
    )
    print(f"Silver hiện có: {len(df_existing):,} rows")

    # ── Clean jobs mới ────────────────────────────────
    print(f"[4/5] Clean {len(df_new):,} jobs mới...")
    rows = df_new[["job_title", "job_skills"]].to_dict("records")
    with Pool(cpu_count()) as p:
        results = p.map(process_row, rows)

    df_new["job_title"],  \
    df_new["job_skills"] = zip(*results)

    df_new["title_skills"] = (
        df_new["job_title"] + " " + df_new["job_skills"]
    )
    df_new = df_new[
        (df_new["job_title"]  != "") &
        (df_new["job_skills"] != "")
    ].reset_index(drop=True)

    # Bỏ job đã có
    df_new = df_new[
        ~df_new.apply(
            lambda r: (r["job_title"], r["job_skills"])
            in existing_pairs, axis=1
        )
    ].reset_index(drop=True)

    if df_new.empty:
        print("Tất cả job mới đã có trong Silver!")
        exit(0)

    print(f"Jobs mới thực sự: {len(df_new):,}")

    # ── Encode + update FAISS ─────────────────────────
    print("[5/5] Encode + update FAISS...")
    model   = SentenceTransformer("all-MiniLM-L6-v2")
    new_emb = model.encode(
        df_new["title_skills"].tolist(),
        batch_size=256,
        normalize_embeddings=True,
        show_progress_bar=True
    ).astype("float32")

    index = faiss.read_index(str(BASE_DIR / "faiss_index.bin"))
    old   = index.ntotal
    index.add(new_emb)

    # Lưu Silver
    df_updated = pd.concat(
        [df_existing, df_new], ignore_index=True
    )
    csv_bytes = df_updated.to_csv(index=False).encode("utf-8")
    client.put_object(
        bucket_name=BUCKET,
        object_name="silver/Silver_Jobs_Cleaned.csv",
        data=io.BytesIO(csv_bytes),
        length=len(csv_bytes),
        content_type="application/csv"
    )

    # Lưu FAISS + metadata
    faiss.write_index(index, str(BASE_DIR / "faiss_index.bin"))
    with open(BASE_DIR / "job_metadata.pkl", "wb") as f:
        pickle.dump(df_updated, f)

    print("Update xong!")
    print(f"  Thêm mới : {len(df_new):,} jobs")
    print(f"  Tổng     : {len(df_updated):,} jobs")
    print(f"  FAISS    : {old:,} → {index.ntotal:,} vectors")