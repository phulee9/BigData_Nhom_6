import pandas as pd

from src.config.silver_config import (
    JOB_POSTING_COLUMNS,
    JOB_SKILL_COLUMNS,
    SILVER_COLUMNS,
)
from src.utils.text_utils import clean_title, clean_skills
from src.utils.title_utils import process_title_columns


def validate_columns(dataframe, required_columns, dataframe_name):
    # Kiểm tra cột bắt buộc
    missing_columns = [
        column for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(f"{dataframe_name} missing columns: {missing_columns}")


def prepare_base_data(job_postings, job_skills):
    # Chọn cột cần thiết và loại duplicate
    validate_columns(job_postings, JOB_POSTING_COLUMNS, "job_postings")
    validate_columns(job_skills, JOB_SKILL_COLUMNS, "job_skills")

    job_postings = (
        job_postings[JOB_POSTING_COLUMNS]
        .drop_duplicates(subset=["job_link"], keep="first")
        .copy()
    )

    job_skills = (
        job_skills[JOB_SKILL_COLUMNS]
        .drop_duplicates(subset=["job_link"], keep="first")
        .copy()
    )

    return job_postings, job_skills


def merge_jobs_and_skills(job_postings, job_skills):
    # Join job_postings và job_skills
    jobs = job_postings.merge(
        job_skills,
        on="job_link",
        how="left",
    )

    jobs = jobs.rename(
        columns={
            "job_title": "title_raw",
            "job_location": "location_raw",
            "job_skills": "skills_raw",
        }
    )

    return jobs


def remove_invalid_jobs(jobs):
    # Loại job thiếu title hoặc skills
    before_rows = len(jobs)

    jobs = jobs[
        jobs["title_raw"].notna()
        & jobs["skills_raw"].notna()
    ].copy()

    jobs["title_raw"] = jobs["title_raw"].astype(str).str.strip()
    jobs["skills_raw"] = jobs["skills_raw"].astype(str).str.strip()

    jobs = jobs[
        (jobs["title_raw"] != "")
        & (jobs["skills_raw"] != "")
    ].copy()

    print(f"Rows before removing missing title/skills: {before_rows:,}")
    print(f"Rows after removing missing title/skills: {len(jobs):,}")
    print(f"Removed rows: {before_rows - len(jobs):,}")

    return jobs


def clean_basic_fields(jobs):
    # Clean title và skills cơ bản
    jobs = jobs.copy()

    jobs["title_clean"] = jobs["title_raw"].apply(clean_title)
    jobs["skills_clean"] = jobs["skills_raw"].apply(clean_skills)

    # Chưa có whitelist nên tạm dùng skills_clean
    jobs["skills_normalized"] = jobs["skills_clean"]

    return jobs


def finalize_silver(jobs):
    # Tạo job_id và chọn cột output
    jobs = jobs.reset_index(drop=True)

    if "job_id" in jobs.columns:
        jobs = jobs.drop(columns=["job_id"])

    jobs.insert(0, "job_id", range(1, len(jobs) + 1))

    validate_columns(jobs, SILVER_COLUMNS, "jobs_silver")

    return jobs[SILVER_COLUMNS].copy()


def build_silver_dataframe(job_postings, job_skills):
    # Build Silver dataframe
    job_postings, job_skills = prepare_base_data(
        job_postings=job_postings,
        job_skills=job_skills,
    )

    jobs = merge_jobs_and_skills(
        job_postings=job_postings,
        job_skills=job_skills,
    )

    jobs = remove_invalid_jobs(jobs)
    jobs = clean_basic_fields(jobs)
    jobs = process_title_columns(jobs)
    jobs = finalize_silver(jobs)

    return jobs