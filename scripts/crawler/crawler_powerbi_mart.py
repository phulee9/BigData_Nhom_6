# scripts/crawler/crawler_powerbi_mart.py

import sys
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import MINIO_BUCKET, POSTGRES_URL
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
)
from src.processing.powerbi_processor import (
    find_unprocessed_week,
    build_jobs_table,
    build_job_skills_table,
)


def silver_weekly_object(week: str) -> str:
    return f"silver/crawler/weekly/{week}.parquet"


def ensure_tables(engine) -> None:
    sql = """
    CREATE SCHEMA IF NOT EXISTS mart_powerbi;

    CREATE TABLE IF NOT EXISTS mart_powerbi.crawler_jobs (
        source_job_id TEXT PRIMARY KEY,
        source TEXT,
        company TEXT,
        job_title TEXT,
        seniority TEXT,
        work_mode TEXT,
        employment_type TEXT,
        city TEXT,
        country TEXT,
        location TEXT,
        skills_count INTEGER,
        crawl_week TEXT,
        job_link TEXT
    );

    CREATE TABLE IF NOT EXISTS mart_powerbi.crawler_job_skills (
        id BIGSERIAL PRIMARY KEY,
        source_job_id TEXT NOT NULL,
        skill TEXT NOT NULL,
        CONSTRAINT uq_crawler_job_skill UNIQUE (source_job_id, skill),
        CONSTRAINT fk_crawler_job_skill_job
            FOREIGN KEY (source_job_id)
            REFERENCES mart_powerbi.crawler_jobs(source_job_id)
            ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS mart_powerbi.crawler_processed_weeks (
        crawl_week TEXT PRIMARY KEY,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with engine.begin() as conn:
        conn.execute(text(sql))


def get_processed_weeks(engine) -> set[str]:
    sql = """
    SELECT crawl_week
    FROM mart_powerbi.crawler_processed_weeks;
    """

    with engine.begin() as conn:
        rows = conn.execute(text(sql)).fetchall()

    return {str(row[0]) for row in rows}


def insert_jobs(engine, jobs_df: pd.DataFrame) -> None:
    if jobs_df.empty:
        print("Không có jobs để insert.")
        return

    sql = """
    INSERT INTO mart_powerbi.crawler_jobs (
        source_job_id,
        source,
        company,
        job_title,
        seniority,
        work_mode,
        employment_type,
        city,
        country,
        location,
        skills_count,
        crawl_week,
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
                "job_title",
                "seniority",
                "work_mode",
                "employment_type",
                "city",
                "country",
                "location",
                "skills_count",
                "crawl_week",
                "job_link",
            ]
        ].itertuples(index=False, name=None)
    )

    raw_conn = engine.raw_connection()

    try:
        with raw_conn.cursor() as cur:
            execute_values(cur, sql, values, page_size=1000)

        raw_conn.commit()

    finally:
        raw_conn.close()


def insert_job_skills(engine, df: pd.DataFrame) -> None:
    if df.empty:
        print("Không có job_skills để insert.")
        return

    sql = """
    INSERT INTO mart_powerbi.crawler_job_skills (
        source_job_id,
        skill
    )
    VALUES %s
    ON CONFLICT (source_job_id, skill) DO NOTHING;
    """

    values = list(
        df[
            [
                "source_job_id",
                "skill",
            ]
        ].itertuples(index=False, name=None)
    )

    raw_conn = engine.raw_connection()

    try:
        with raw_conn.cursor() as cur:
            execute_values(cur, sql, values, page_size=5000)

        raw_conn.commit()

    finally:
        raw_conn.close()


def mark_week_processed(engine, week: str) -> None:
    sql = """
    INSERT INTO mart_powerbi.crawler_processed_weeks (crawl_week)
    VALUES (:crawl_week)
    ON CONFLICT (crawl_week) DO NOTHING;
    """

    with engine.begin() as conn:
        conn.execute(text(sql), {"crawl_week": week})


def print_counts(engine) -> None:
    with engine.begin() as conn:
        jobs_count = conn.execute(
            text("SELECT COUNT(*) FROM mart_powerbi.crawler_jobs")
        ).scalar()

        skills_count = conn.execute(
            text("SELECT COUNT(*) FROM mart_powerbi.crawler_job_skills")
        ).scalar()

        week_count = conn.execute(
            text("SELECT COUNT(*) FROM mart_powerbi.crawler_processed_weeks")
        ).scalar()

    print("\nSố dòng hiện tại trong PostgreSQL:")
    print(f"crawler_jobs: {jobs_count}")
    print(f"crawler_job_skills: {skills_count}")
    print(f"crawler_processed_weeks: {week_count}")


def main() -> None:
    print("Bắt đầu append crawler mart cho Power BI vào PostgreSQL")
    print(f"PostgreSQL URL: {POSTGRES_URL}")

    client = get_minio_client()
    engine = create_engine(POSTGRES_URL)

    print("\nBước 1: Tạo schema/table nếu chưa có")
    ensure_tables(engine)

    print("\nBước 2: Tìm Silver weekly chưa append")
    week = find_unprocessed_week(client, engine)

    if week is None:
        print("\nKhông có tuần mới cần append.")
        print_counts(engine)
        return

    object_name = silver_weekly_object(week)

    print(f"Tuần cần append: {week}")
    print(f"Input: s3://{MINIO_BUCKET}/{object_name}")

    print("\nBước 3: Đọc Silver weekly từ MinIO")
    silver_df = read_parquet_from_minio(
        client=client,
        object_name=object_name,
    )

    print(f"Số dòng Silver weekly: {len(silver_df)}")
    print(f"Các cột Silver: {silver_df.columns.tolist()}")

    if silver_df.empty:
        print("Silver weekly rỗng. Dừng.")
        return

    print("\nBước 4: Build bảng crawler_jobs")
    jobs_df = build_jobs_table(silver_df)
    print(f"Số dòng jobs chuẩn bị insert: {len(jobs_df)}")

    print("\nBước 5: Build bảng crawler_job_skills")
    job_skills_df = build_job_skills_table(silver_df)
    print(f"Số dòng job_skills chuẩn bị insert: {len(job_skills_df)}")

    print("\nBước 6: Insert crawler_jobs")
    insert_jobs(engine, jobs_df)

    print("\nBước 7: Insert crawler_job_skills")
    insert_job_skills(engine, job_skills_df)

    print("\nBước 8: Đánh dấu tuần đã xử lý")
    mark_week_processed(engine, week)

    print_counts(engine)

    print("\nHoàn thành append crawler mart cho Power BI.")


if __name__ == "__main__":
    main()