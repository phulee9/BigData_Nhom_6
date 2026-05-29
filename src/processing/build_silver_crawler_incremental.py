import argparse
import json
import os
import sys

import pandas as pd
from minio.error import S3Error

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)
from src.processing.crawler_silver_builder import clean_crawler_jobs


BRONZE_RAW_TEMPLATE = "bronze/crawler/raw/{week}.json"

SILVER_WEEKLY_TEMPLATE = "silver/crawler/weekly/{week}.parquet"
SILVER_TOTAL_PATH = "silver/crawler/jobs_silver.parquet"

LOCAL_TEMP_DIR = "data/temp/crawler"
LOCAL_RAW_PATH = f"{LOCAL_TEMP_DIR}/raw_week.json"
LOCAL_SILVER_WEEKLY_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver_weekly.parquet"
LOCAL_SILVER_TOTAL_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver.parquet"


def download_file_if_exists(client, object_path, local_path):
    # Download file nếu tồn tại trên MinIO
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        client.fget_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_path,
            file_path=local_path,
        )

        return True

    except S3Error as error:
        if error.code in {"NoSuchKey", "NoSuchBucket"}:
            return False

        raise error


def download_raw_week(client, week):
    # Tải raw tuần mới từ Bronze
    object_path = BRONZE_RAW_TEMPLATE.format(week=week)

    exists = download_file_if_exists(
        client=client,
        object_path=object_path,
        local_path=LOCAL_RAW_PATH,
    )

    if not exists:
        raise FileNotFoundError(f"Bronze raw file not found: {object_path}")

    print(f"Downloaded: {object_path}")


def read_raw_week():
    # Đọc JSON raw tuần mới
    with open(LOCAL_RAW_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def read_existing_silver(client):
    # Đọc Silver tổng nếu đã tồn tại
    exists = download_file_if_exists(
        client=client,
        object_path=SILVER_TOTAL_PATH,
        local_path=LOCAL_SILVER_TOTAL_PATH,
    )

    if not exists:
        return pd.DataFrame()

    return pd.read_parquet(LOCAL_SILVER_TOTAL_PATH)


def normalize_link_series(series):
    # Chuẩn hóa link để so sánh duplicate
    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


def filter_new_jobs(silver_week, existing_silver):
    # Chỉ giữ job mới chưa có trong Silver tổng
    if existing_silver.empty:
        return silver_week.copy()

    existing_links = set(
        normalize_link_series(existing_silver["link"])
    )

    silver_week = silver_week.copy()
    silver_week["link"] = normalize_link_series(silver_week["link"])

    new_jobs = silver_week[
        ~silver_week["link"].isin(existing_links)
    ].copy()

    return new_jobs


def assign_job_id(new_jobs, existing_silver):
    # Gán job_id tăng dần cho job mới
    new_jobs = new_jobs.copy()

    if existing_silver.empty:
        start_id = 1
    else:
        start_id = int(existing_silver["job_id"].max()) + 1

    new_jobs.insert(
        0,
        "job_id",
        range(start_id, start_id + len(new_jobs)),
    )

    return new_jobs


def build_silver_total(existing_silver, silver_week_new):
    # Append job mới vào Silver tổng
    if existing_silver.empty:
        silver_total = silver_week_new.copy()
    else:
        silver_total = pd.concat(
            [
                existing_silver,
                silver_week_new,
            ],
            ignore_index=True,
        )

    silver_total["link"] = normalize_link_series(silver_total["link"])

    silver_total = silver_total.drop_duplicates(
        subset=["link"],
        keep="first",
    ).reset_index(drop=True)

    return silver_total


def save_local_files(silver_week_new, silver_total):
    # Lưu local parquet
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    silver_week_new.to_parquet(
        LOCAL_SILVER_WEEKLY_PATH,
        index=False,
    )

    silver_total.to_parquet(
        LOCAL_SILVER_TOTAL_PATH,
        index=False,
    )


def upload_outputs(client, week):
    # Upload Silver weekly và Silver tổng
    weekly_path = SILVER_WEEKLY_TEMPLATE.format(week=week)

    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=weekly_path,
        file_path=LOCAL_SILVER_WEEKLY_PATH,
    )

    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=SILVER_TOTAL_PATH,
        file_path=LOCAL_SILVER_TOTAL_PATH,
    )

    print(f"Uploaded: {weekly_path}")
    print(f"Uploaded: {SILVER_TOTAL_PATH}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--week",
        required=True,
        help="Tên tuần, ví dụ: week_2026_05_09",
    )

    args = parser.parse_args()

    client = get_minio_client()

    print("Downloading raw week...")
    download_raw_week(client, args.week)

    print("Reading raw week...")
    raw_jobs = read_raw_week()

    print(f"Raw jobs: {len(raw_jobs):,}")

    print("Cleaning crawler jobs...")
    silver_week = clean_crawler_jobs(
        raw_jobs=raw_jobs,
        week=args.week,
    )

    print(f"Silver week rows after duplicate link removal: {len(silver_week):,}")

    print("Reading existing Silver total...")
    existing_silver = read_existing_silver(client)

    print(f"Existing Silver rows: {len(existing_silver):,}")

    print("Filtering new jobs...")
    silver_week_new = filter_new_jobs(
        silver_week=silver_week,
        existing_silver=existing_silver,
    )

    print(f"New jobs: {len(silver_week_new):,}")

    print("Assigning job_id...")
    silver_week_new = assign_job_id(
        new_jobs=silver_week_new,
        existing_silver=existing_silver,
    )

    print("Building Silver total...")
    silver_total = build_silver_total(
        existing_silver=existing_silver,
        silver_week_new=silver_week_new,
    )

    print(f"Silver total rows after append: {len(silver_total):,}")

    print("Saving local files...")
    save_local_files(
        silver_week_new=silver_week_new,
        silver_total=silver_total,
    )

    print("Uploading outputs...")
    upload_outputs(
        client=client,
        week=args.week,
    )

    print("Done.")


if __name__ == "__main__":
    main()