import os
import sys

import pandas as pd

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)


SILVER_INPUT_PATH = "silver/kaggle/jobs_silver.parquet"
GOLD_OUTPUT_PATH = "gold/kaggle/jobs_for_encoding.parquet"

LOCAL_TEMP_DIR = "data/temp"
LOCAL_SILVER_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver.parquet"
LOCAL_GOLD_OUTPUT_PATH = f"{LOCAL_TEMP_DIR}/jobs_for_encoding.parquet"


def download_silver_file(client):
    # Tải Silver final từ MinIO
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=SILVER_INPUT_PATH,
        file_path=LOCAL_SILVER_PATH,
    )


def read_silver_file():
    # Đọc Silver final
    return pd.read_parquet(LOCAL_SILVER_PATH)


def clean_text_value(value):
    # Chuẩn hóa giá trị text
    if pd.isna(value):
        return ""

    return str(value).strip()


def build_encoding_dataframe(jobs):
    # Tạo dữ liệu phục vụ encode title và skills
    jobs = jobs.copy()

    jobs["title_core"] = jobs["title_core"].apply(clean_text_value)
    jobs["skills_normalized"] = jobs["skills_normalized"].apply(clean_text_value)

    before_rows = len(jobs)

    jobs = jobs[
        (jobs["title_core"] != "")
        & (jobs["skills_normalized"] != "")
    ].copy()

    after_rows = len(jobs)

    print(f"Rows before removing empty title/skills: {before_rows:,}")
    print(f"Rows after removing empty title/skills: {after_rows:,}")
    print(f"Removed rows: {before_rows - after_rows:,}")

    jobs = jobs.reset_index(drop=True)
    jobs.insert(0, "doc_id", range(len(jobs)))

    jobs["title_text"] = jobs["title_core"].apply(
        lambda value: f"Job title: {value}."
    )

    jobs["skills_text"] = jobs["skills_normalized"].apply(
        lambda value: f"Skills: {value}."
    )

    output_columns = [
        "doc_id",
        "job_id",
        "job_link",
        "title_core",
        "skills_normalized",
        "title_text",
        "skills_text",
    ]

    return jobs[output_columns].copy()


def save_gold_file(jobs_for_encoding):
    # Lưu Gold local
    jobs_for_encoding.to_parquet(
        LOCAL_GOLD_OUTPUT_PATH,
        index=False,
    )


def upload_gold_file(client):
    # Upload Gold lên MinIO
    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=GOLD_OUTPUT_PATH,
        file_path=LOCAL_GOLD_OUTPUT_PATH,
    )


def main():
    client = get_minio_client()

    print("Downloading Silver final file...")
    download_silver_file(client)

    print("Reading Silver final file...")
    jobs = read_silver_file()

    print(f"Silver rows: {len(jobs):,}")

    print("Building encoding dataframe...")
    jobs_for_encoding = build_encoding_dataframe(jobs)

    print(f"Encoding rows: {len(jobs_for_encoding):,}")

    print("Saving Gold file...")
    save_gold_file(jobs_for_encoding)

    print("Uploading Gold file...")
    upload_gold_file(client)

    print(f"Uploaded: {GOLD_OUTPUT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()