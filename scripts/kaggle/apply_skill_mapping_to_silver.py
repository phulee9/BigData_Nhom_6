import os
import sys

import pandas as pd

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)
from src.processing.skill_mapping_applier import apply_skill_mapping


SILVER_INPUT_PATH = "silver/kaggle/jobs_silver.parquet"
SILVER_OUTPUT_PATH = "silver/kaggle/jobs_silver.parquet"

LOCAL_TEMP_DIR = "data/temp"
LOCAL_SILVER_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver.parquet"
LOCAL_SILVER_FINAL_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver_final.parquet"

SKILL_MAPPING_PATH = "data/mapping/skill_alias_mapping.csv"


def download_silver_file(client):
    # Tải Silver từ MinIO
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=SILVER_INPUT_PATH,
        file_path=LOCAL_SILVER_PATH,
    )


def read_silver_file():
    # Đọc Silver local
    return pd.read_parquet(LOCAL_SILVER_PATH)


def save_silver_file(jobs):
    # Lưu Silver final local
    jobs.to_parquet(
        LOCAL_SILVER_FINAL_PATH,
        index=False,
    )


def upload_silver_file(client):
    # Upload Silver final lên MinIO
    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=SILVER_OUTPUT_PATH,
        file_path=LOCAL_SILVER_FINAL_PATH,
    )


def main():
    if not os.path.exists(SKILL_MAPPING_PATH):
        raise FileNotFoundError(
            f"Skill mapping file not found: {SKILL_MAPPING_PATH}"
        )

    client = get_minio_client()

    print("Downloading Silver file...")
    download_silver_file(client)

    print("Reading Silver file...")
    jobs = read_silver_file()

    print(f"Silver rows: {len(jobs):,}")

    print("Applying skill mapping...")
    jobs = apply_skill_mapping(
        jobs=jobs,
        mapping_path=SKILL_MAPPING_PATH,
    )

    print("Saving Silver final file...")
    save_silver_file(jobs)

    print("Uploading Silver final file...")
    upload_silver_file(client)

    print(f"Uploaded: {SILVER_OUTPUT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()