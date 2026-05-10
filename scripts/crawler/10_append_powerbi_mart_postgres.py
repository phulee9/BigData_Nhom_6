import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    POSTGRES_URL,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
)


def gold_batch_object(batch_name: str) -> str:
    return f"gold/crawler/batches/{batch_name}/jobs_for_encoding.parquet"


def list_gold_batches(client) -> list[str]:
    # Lấy danh sách batch đã có Gold Encode trên MinIO
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="gold/crawler/batches/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/jobs_for_encoding.parquet"):
            continue

        # gold/crawler/batches/week_2026_05_09/jobs_for_encoding.parquet
        parts = object_name.split("/")

        if len(parts) >= 4:
            batch_names.add(parts[3])

    return sorted(batch_names)


def parse_skills(value) -> list[str]:
    # Chuyển skills_canonical về list Python
    if value is None:
        return []

    if isinstance(value, float) and pd.isna(value):
        return []

    if isinstance(value, list):
        return [
            str(skill).strip()
            for skill in value
            if str(skill).strip()
        ]

    if isinstance(value, np.ndarray):
        return [
            str(skill).strip()
            for skill in value.tolist()
            if str(skill).strip()
        ]

    if isinstance(value, (tuple, set)):
        return [
            str(skill).strip()
            for skill in list(value)
            if str(skill).strip()
        ]

    if isinstance(value, str):
        text_value = value.strip()

        if text_value.lower() in ["", "[]", "nan", "none", "null"]:
            return []

        try:
            parsed = ast.literal_eval(text_value)

            if isinstance(parsed, list):
                return [
                    str(skill).strip()
                    for skill in parsed
                    if str(skill).strip()
                ]

            if isinstance(parsed, (tuple, set)):
                return [
                    str(skill).strip()
                    for skill in list(parsed)
                    if str(skill).strip()
                ]

        except Exception:
            pass

        return [text_value]

    return []


def ensure_tables(engine) -> None:
    # Tạo schema và bảng Mart nếu chưa có
    create_sql = """
    CREATE SCHEMA IF NOT EXISTS mart_powerbi;

    CREATE TABLE IF NOT EXISTS mart_powerbi.crawler_jobs (
        source_job_id TEXT PRIMARY KEY,
        source TEXT,
        company TEXT,
        job_title_canonical TEXT,
        occupation_group_final TEXT,
        occupation_family_final TEXT,
        seniority TEXT,
        city_clean TEXT,
        country_clean TEXT,
        location_final TEXT,
        skills_count_final INTEGER,
        crawl_batch TEXT,
        job_url TEXT,
        job_link TEXT
    );

    CREATE TABLE IF NOT EXISTS mart_powerbi.crawler_job_skills (
        id BIGSERIAL PRIMARY KEY,
        source_job_id TEXT NOT NULL,
        skill TEXT NOT NULL,
        job_title_canonical TEXT,
        company TEXT,
        occupation_group_final TEXT,
        occupation_family_final TEXT,
        seniority TEXT,
        city_clean TEXT,
        country_clean TEXT,
        location_final TEXT,
        crawl_batch TEXT,
        CONSTRAINT uq_crawler_job_skill UNIQUE (source_job_id, skill)
    );

    CREATE TABLE IF NOT EXISTS mart_powerbi.crawler_processed_batches (
        crawl_batch TEXT PRIMARY KEY,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with engine.begin() as conn:
        conn.execute(text(create_sql))


def get_processed_batches(engine) -> set[str]:
    # Lấy danh sách batch đã append vào PostgreSQL
    query = """
    SELECT crawl_batch
    FROM mart_powerbi.crawler_processed_batches;
    """

    with engine.begin() as conn:
        result = conn.execute(text(query))

        return {
            str(row[0])
            for row in result.fetchall()
        }


def find_unprocessed_batch(client, engine) -> str | None:
    # Tìm Gold batch chưa được append vào PostgreSQL
    gold_batches = list_gold_batches(client)
    processed_batches = get_processed_batches(engine)

    if not gold_batches:
        print("Không tìm thấy Gold crawler batch nào trên MinIO.")
        return None

    for batch_name in gold_batches:
        if batch_name in processed_batches:
            print(f"Bỏ qua batch đã append PostgreSQL: {batch_name}")
            continue

        return batch_name

    return None


def build_jobs_table(gold_df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bảng crawler_jobs, mỗi dòng là 1 job
    jobs_cols = [
        "source_job_id",
        "source",
        "company",
        "job_title_canonical",
        "occupation_group_final",
        "occupation_family_final",
        "seniority",
        "city_clean",
        "country_clean",
        "location_final",
        "skills_count_final",
        "crawl_batch",
        "job_url",
        "job_link",
    ]

    jobs_df = gold_df.copy()

    for col in jobs_cols:
        if col not in jobs_df.columns:
            jobs_df[col] = ""

    jobs_df = jobs_df[jobs_cols].copy()

    text_cols = [
        "source_job_id",
        "source",
        "company",
        "job_title_canonical",
        "occupation_group_final",
        "occupation_family_final",
        "seniority",
        "city_clean",
        "country_clean",
        "location_final",
        "crawl_batch",
        "job_url",
        "job_link",
    ]

    for col in text_cols:
        jobs_df[col] = (
            jobs_df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    jobs_df["skills_count_final"] = pd.to_numeric(
        jobs_df["skills_count_final"],
        errors="coerce",
    ).fillna(0).astype(int)

    jobs_df = jobs_df[
        jobs_df["source_job_id"] != ""
    ].copy()

    jobs_df = jobs_df.drop_duplicates(
        subset=["source_job_id"],
        keep="first",
    ).copy()

    return jobs_df


def build_job_skills_table(gold_df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bảng crawler_job_skills, mỗi dòng là 1 skill của 1 job
    rows = []

    for _, row in gold_df.iterrows():
        source_job_id = str(row.get("source_job_id", "") or "").strip()

        if not source_job_id:
            continue

        skills = parse_skills(
            row.get("skills_canonical", [])
        )

        for skill in skills:
            skill = str(skill or "").strip()

            if not skill:
                continue

            rows.append(
                {
                    "source_job_id": source_job_id,
                    "skill": skill,
                    "job_title_canonical": row.get("job_title_canonical", ""),
                    "company": row.get("company", ""),
                    "occupation_group_final": row.get("occupation_group_final", ""),
                    "occupation_family_final": row.get("occupation_family_final", ""),
                    "seniority": row.get("seniority", ""),
                    "city_clean": row.get("city_clean", ""),
                    "country_clean": row.get("country_clean", ""),
                    "location_final": row.get("location_final", ""),
                    "crawl_batch": row.get("crawl_batch", ""),
                }
            )

    cols = [
        "source_job_id",
        "skill",
        "job_title_canonical",
        "company",
        "occupation_group_final",
        "occupation_family_final",
        "seniority",
        "city_clean",
        "country_clean",
        "location_final",
        "crawl_batch",
    ]

    job_skills_df = pd.DataFrame(rows)

    if job_skills_df.empty:
        return pd.DataFrame(columns=cols)

    job_skills_df = job_skills_df[cols].copy()

    for col in cols:
        job_skills_df[col] = (
            job_skills_df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    job_skills_df = job_skills_df[
        (job_skills_df["source_job_id"] != "")
        & (job_skills_df["skill"] != "")
    ].copy()

    job_skills_df = job_skills_df.drop_duplicates(
        subset=["source_job_id", "skill"],
        keep="first",
    ).copy()

    return job_skills_df


def insert_jobs(engine, jobs_df: pd.DataFrame) -> None:
    # Insert crawler_jobs vào PostgreSQL, không insert trùng source_job_id
    if jobs_df.empty:
        print("Không có dòng jobs để insert.")
        return

    sql = """
    INSERT INTO mart_powerbi.crawler_jobs (
        source_job_id,
        source,
        company,
        job_title_canonical,
        occupation_group_final,
        occupation_family_final,
        seniority,
        city_clean,
        country_clean,
        location_final,
        skills_count_final,
        crawl_batch,
        job_url,
        job_link
    )
    VALUES %s
    ON CONFLICT (source_job_id) DO NOTHING;
    """

    values = list(
        jobs_df[
            [
                "source_job_id",
                "source",
                "company",
                "job_title_canonical",
                "occupation_group_final",
                "occupation_family_final",
                "seniority",
                "city_clean",
                "country_clean",
                "location_final",
                "skills_count_final",
                "crawl_batch",
                "job_url",
                "job_link",
            ]
        ].itertuples(index=False, name=None)
    )

    raw_conn = engine.raw_connection()

    try:
        with raw_conn.cursor() as cursor:
            execute_values(
                cursor,
                sql,
                values,
                page_size=1000,
            )

        raw_conn.commit()

    finally:
        raw_conn.close()


def insert_job_skills(engine, job_skills_df: pd.DataFrame) -> None:
    # Insert crawler_job_skills vào PostgreSQL, không insert trùng source_job_id + skill
    if job_skills_df.empty:
        print("Không có dòng job_skills để insert.")
        return

    sql = """
    INSERT INTO mart_powerbi.crawler_job_skills (
        source_job_id,
        skill,
        job_title_canonical,
        company,
        occupation_group_final,
        occupation_family_final,
        seniority,
        city_clean,
        country_clean,
        location_final,
        crawl_batch
    )
    VALUES %s
    ON CONFLICT (source_job_id, skill) DO NOTHING;
    """

    values = list(
        job_skills_df[
            [
                "source_job_id",
                "skill",
                "job_title_canonical",
                "company",
                "occupation_group_final",
                "occupation_family_final",
                "seniority",
                "city_clean",
                "country_clean",
                "location_final",
                "crawl_batch",
            ]
        ].itertuples(index=False, name=None)
    )

    raw_conn = engine.raw_connection()

    try:
        with raw_conn.cursor() as cursor:
            execute_values(
                cursor,
                sql,
                values,
                page_size=5000,
            )

        raw_conn.commit()

    finally:
        raw_conn.close()


def mark_batch_processed(engine, batch_name: str) -> None:
    # Đánh dấu batch đã append vào PostgreSQL
    sql = """
    INSERT INTO mart_powerbi.crawler_processed_batches (crawl_batch)
    VALUES (:crawl_batch)
    ON CONFLICT (crawl_batch) DO NOTHING;
    """

    with engine.begin() as conn:
        conn.execute(
            text(sql),
            {"crawl_batch": batch_name},
        )


def print_counts(engine) -> None:
    # In số dòng hiện tại trong PostgreSQL
    with engine.begin() as conn:
        jobs_count = conn.execute(
            text("SELECT COUNT(*) FROM mart_powerbi.crawler_jobs")
        ).scalar()

        skills_count = conn.execute(
            text("SELECT COUNT(*) FROM mart_powerbi.crawler_job_skills")
        ).scalar()

        batch_count = conn.execute(
            text("SELECT COUNT(*) FROM mart_powerbi.crawler_processed_batches")
        ).scalar()

    print("\nSố dòng hiện tại trong PostgreSQL:")
    print(f"crawler_jobs: {jobs_count}")
    print(f"crawler_job_skills: {skills_count}")
    print(f"crawler_processed_batches: {batch_count}")


def main() -> None:
    print("Bắt đầu append crawler Power BI mart vào PostgreSQL")
    print(f"PostgreSQL URL: {POSTGRES_URL}")

    # Kết nối MinIO
    client = get_minio_client()

    # Kết nối PostgreSQL
    engine = create_engine(POSTGRES_URL)

    # Tạo schema/table nếu chưa có
    print("\nBước 1: Tạo schema/table nếu chưa có")
    ensure_tables(engine)

    # Tìm Gold batch chưa append PostgreSQL
    print("\nBước 2: Tìm Gold batch chưa append PostgreSQL")
    batch_name = find_unprocessed_batch(
        client=client,
        engine=engine,
    )

    if batch_name is None:
        print("\nKhông có batch mới cần append PostgreSQL.")
        print_counts(engine)
        return

    gold_object = gold_batch_object(batch_name)

    print(f"Batch cần append PostgreSQL: {batch_name}")
    print(f"Input Gold batch: s3://{MINIO_BUCKET}/{gold_object}")

    # Đọc Gold batch từ MinIO
    print("\nBước 3: Đọc Gold batch")
    gold_df = read_parquet_from_minio(
        client=client,
        object_name=gold_object,
    )

    print(f"Số dòng Gold batch: {len(gold_df)}")

    if gold_df.empty:
        print("Gold batch rỗng. Dừng.")
        return

    # Tạo bảng jobs
    print("\nBước 4: Tạo jobs table")
    jobs_df = build_jobs_table(gold_df)
    print(f"Số dòng jobs chuẩn bị insert: {len(jobs_df)}")

    # Tạo bảng job_skills
    print("\nBước 5: Tạo job_skills table")
    job_skills_df = build_job_skills_table(gold_df)
    print(f"Số dòng job_skills chuẩn bị insert: {len(job_skills_df)}")

    # Insert jobs
    print("\nBước 6: Insert jobs vào PostgreSQL")
    insert_jobs(
        engine=engine,
        jobs_df=jobs_df,
    )

    # Insert job skills
    print("\nBước 7: Insert job_skills vào PostgreSQL")
    insert_job_skills(
        engine=engine,
        job_skills_df=job_skills_df,
    )

    # Đánh dấu batch đã xử lý
    print("\nBước 8: Đánh dấu batch đã append PostgreSQL")
    mark_batch_processed(
        engine=engine,
        batch_name=batch_name,
    )

    # Kiểm tra count
    print_counts(engine)

    print("\nHoàn thành append crawler Power BI mart vào PostgreSQL.")


if __name__ == "__main__":
    main()