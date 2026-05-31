import os
import sys

import pandas as pd

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    ensure_bucket_exists,
    get_minio_client,
)
from src.processing.silver_builder import build_silver_dataframe


BRONZE_JOB_POSTINGS_PATH = "bronze/kaggle/linkedin_job_postings.csv"
BRONZE_JOB_SKILLS_PATH = "bronze/kaggle/job_skills.csv"

SILVER_OUTPUT_PATH = "silver/kaggle/jobs_silver.parquet"

LOCAL_TEMP_DIR = "data/temp"
LOCAL_JOB_POSTINGS_PATH = f"{LOCAL_TEMP_DIR}/linkedin_job_postings.csv"
LOCAL_JOB_SKILLS_PATH = f"{LOCAL_TEMP_DIR}/job_skills.csv"
LOCAL_SILVER_OUTPUT_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver.parquet"


def download_raw_files(client):
    # Tải dữ liệu raw từ Bronze
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=BRONZE_JOB_POSTINGS_PATH,
        file_path=LOCAL_JOB_POSTINGS_PATH,
    )

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=BRONZE_JOB_SKILLS_PATH,
        file_path=LOCAL_JOB_SKILLS_PATH,
    )


def read_raw_files():
    # Đọc dữ liệu raw
    job_postings = pd.read_csv(
        LOCAL_JOB_POSTINGS_PATH,
        low_memory=False,
    )

    job_skills = pd.read_csv(
        LOCAL_JOB_SKILLS_PATH,
        low_memory=False,
    )

    return job_postings, job_skills


def save_silver_file(jobs_silver):
    # Lưu Silver ra local
    jobs_silver.to_parquet(
        LOCAL_SILVER_OUTPUT_PATH,
        index=False,
    )


def upload_silver_file(client):
    # Upload Silver lên MinIO
    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=SILVER_OUTPUT_PATH,
        file_path=LOCAL_SILVER_OUTPUT_PATH,
    )


def main():
    client = get_minio_client()
    ensure_bucket_exists(client)

    print("Downloading raw files...")
    download_raw_files(client)

    print("Reading raw files...")
    job_postings, job_skills = read_raw_files()

    print(f"Job postings raw rows: {len(job_postings):,}")
    print(f"Job skills raw rows: {len(job_skills):,}")

    print("Building Silver dataframe...")
    jobs_silver = build_silver_dataframe(
        job_postings=job_postings,
        job_skills=job_skills,
    )

    print(f"Silver rows: {len(jobs_silver):,}")

    print("Saving Silver file...")
    save_silver_file(jobs_silver)

    print("Uploading Silver file...")
    upload_silver_file(client)

    print(f"Uploaded: {SILVER_OUTPUT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()