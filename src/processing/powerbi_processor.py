import pandas as pd
from sqlalchemy import text

from src.storage.minio_client import (
    read_parquet_from_minio,
)
from src.utils.dataframe_utils import safe_col, parse_skills


def find_unprocessed_week(client, engine) -> str | None:
    """
    Find the first unprocessed Silver weekly parquet from MinIO.
    
    Args:
        client: MinIO client
        engine: SQLAlchemy engine
        
    Returns:
        Week string or None if no unprocessed weeks found
    """
    # Get all silver weeks from MinIO
    from src.config import MINIO_BUCKET
    from pathlib import Path
    
    SILVER_WEEKLY_PREFIX = "silver/crawler/weekly/"
    
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix=SILVER_WEEKLY_PREFIX,
        recursive=True,
    )

    weeks = set()
    for obj in objects:
        name = obj.object_name
        if not name.endswith(".parquet"):
            continue
        week = Path(name).stem
        weeks.add(week)

    silver_weeks = sorted(weeks)

    # Get processed weeks from PostgreSQL
    sql = """
    SELECT crawl_week
    FROM mart_powerbi.crawler_processed_weeks;
    """

    with engine.begin() as conn:
        rows = conn.execute(text(sql)).fetchall()

    processed_weeks = {str(row[0]) for row in rows}

    if not silver_weeks:
        print("Không tìm thấy Silver weekly parquet trên MinIO.")
        return None

    for week in silver_weeks:
        if week in processed_weeks:
            print(f"Bỏ qua tuần đã append PostgreSQL: {week}")
            continue

        return week

    return None


def build_jobs_table(silver_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build crawler_jobs table from Silver weekly DataFrame.
    
    Args:
        silver_df: Silver weekly DataFrame from MinIO
        
    Returns:
        Jobs DataFrame ready for insertion
    """
    job_id_col = "job_id" if "job_id" in silver_df.columns else "doc_id"

    jobs_df = pd.DataFrame({
        "source_job_id": safe_col(silver_df, job_id_col).astype(str),
        "source": safe_col(silver_df, "source", "monster"),
        "company": safe_col(silver_df, "company"),
        "job_title": safe_col(silver_df, "title_core"),
        "seniority": safe_col(silver_df, "seniority"),
        "work_mode": safe_col(silver_df, "work_mode"),
        "employment_type": safe_col(silver_df, "employment_type"),
        "city": safe_col(silver_df, "city"),
        "country": safe_col(silver_df, "country"),
        "location": safe_col(silver_df, "location_raw"),
        "crawl_week": safe_col(silver_df, "crawl_week"),
        "job_link": safe_col(silver_df, "link"),
    })

    jobs_df["skills_count"] = safe_col(silver_df, "skills_clean").apply(
        lambda x: len(parse_skills(x))
    )

    text_cols = [
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
        "crawl_week",
        "job_link",
    ]

    for col in text_cols:
        jobs_df[col] = jobs_df[col].fillna("").astype(str).str.strip()

    jobs_df["skills_count"] = pd.to_numeric(
        jobs_df["skills_count"],
        errors="coerce",
    ).fillna(0).astype(int)

    jobs_df = jobs_df[jobs_df["source_job_id"] != ""].copy()

    jobs_df = jobs_df.drop_duplicates(
        subset=["source_job_id"],
        keep="first",
    )

    return jobs_df


def build_job_skills_table(silver_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build crawler_job_skills table from Silver weekly DataFrame.
    
    Args:
        silver_df: Silver weekly DataFrame from MinIO
        
    Returns:
        Job skills DataFrame ready for insertion
    """
    rows = []

    job_id_col = "job_id" if "job_id" in silver_df.columns else "doc_id"

    for _, row in silver_df.iterrows():
        source_job_id = str(row.get(job_id_col, "") or "").strip()

        if not source_job_id:
            continue

        skills = parse_skills(row.get("skills_clean", ""))

        for skill in skills:
            skill = str(skill or "").strip()

            if not skill:
                continue

            rows.append({
                "source_job_id": source_job_id,
                "skill": skill,
            })

    cols = ["source_job_id", "skill"]

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=cols)

    df = df[cols].copy()

    for col in cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df[
        (df["source_job_id"] != "")
        & (df["skill"] != "")
    ].copy()

    df = df.drop_duplicates(
        subset=["source_job_id", "skill"],
        keep="first",
    )

    return df
