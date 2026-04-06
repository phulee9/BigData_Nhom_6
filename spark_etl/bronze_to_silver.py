import io, json, os
import pandas as pd
from minio import Minio
from multiprocessing import Pool, cpu_count
from dotenv import load_dotenv
from pathlib import Path
import sys
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

if __name__ == "__main__":

    # Kiểm tra whitelist
    whitelist = get_whitelist()
    if not whitelist:
        print("Chưa có whitelist!")
        print("  Chạy trước: python spark_etl/build_skill_whitelist.py")
        exit(1)

    # ── Đọc Kaggle ────────────────────────────────────
    print("[1/5] Đọc Kaggle từ Bronze...")
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

    # ── Đọc Monster ───────────────────────────────────
    print("[2/5] Đọc Monster từ Bronze...")
    objs  = list(client.list_objects(
        BUCKET, prefix="bronze/crawled/", recursive=True
    ))
    dates = sorted(
        {o.object_name.split("/")[2]
         for o in objs if len(o.object_name.split("/")) >= 3},
        reverse=True
    )

    monster_list = []
    if dates:
        latest = dates[0]
        for o in objs:
            if o.object_name.startswith(
                f"bronze/crawled/{latest}/"
            ) and o.object_name.endswith(".json"):
                data = json.loads(
                    client.get_object(
                        BUCKET, o.object_name
                    ).read().decode()
                )
                monster_list.extend(
                    data if isinstance(data, list) else [data]
                )

    rows_monster = []
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
        rows_monster.append({
            "job_title":  row.get("title", ""),
            "job_skills": job_skills
        })

    df_monster = pd.DataFrame(rows_monster).dropna() \
                   if rows_monster else \
                   pd.DataFrame(columns=["job_title", "job_skills"])
    print(f"✓ Monster: {len(df_monster):,} rows")

    # ── Gộp 2 nguồn ───────────────────────────────────
    print("[3/5] Gộp 2 nguồn...")
    df_all = pd.concat(
        [df_kaggle, df_monster], ignore_index=True
    ).dropna(subset=["job_title", "job_skills"])
    print(f"✓ Tổng: {len(df_all):,} rows")

    # ── Clean text ────────────────────────────────────
    print(f" [4/5] Clean text ({cpu_count()} cores)...")
    print("  job_title  → spaCy NER + synonym + lemmatize")
    print("  job_skills → whitelist filter + lemmatize")

    rows = df_all[["job_title", "job_skills"]].to_dict("records")
    with Pool(cpu_count()) as p:
        results = p.map(process_row, rows)

    df_all["job_title"],  \
    df_all["job_skills"] = zip(*results)

    df_all["title_skills"] = (
        df_all["job_title"] + " " + df_all["job_skills"]
    )

    df_all = df_all[
        (df_all["job_title"]  != "") &
        (df_all["job_skills"] != "")
    ].drop_duplicates(
        subset=["job_title", "job_skills"]
    ).reset_index(drop=True)

    print(f"Sau clean        : {len(df_all):,} rows")
    print(f"Unique job_title : {df_all['job_title'].nunique():,}")

    # ── Lưu Silver ────────────────────────────────────
    print("[5/5] Lưu Silver lên MinIO...")
    csv_bytes = df_all.to_csv(index=False).encode("utf-8")
    client.put_object(
        bucket_name=BUCKET,
        object_name="silver/Silver_Jobs_Cleaned.csv",
        data=io.BytesIO(csv_bytes),
        length=len(csv_bytes),
        content_type="application/csv"
    )
    print("Silver xong!")
    print(f"  Shape  : {df_all.shape}")
    print(f"  Columns: {df_all.columns.tolist()}")
    print("  Tiep theo: python spark_etl/silver_to_gold.py")