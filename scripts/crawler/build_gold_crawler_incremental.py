import argparse
import os
import sys

import pandas as pd
from minio.error import S3Error

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)


SILVER_WEEKLY_TEMPLATE = "silver/crawler/weekly/{week}.parquet"

GOLD_WEEKLY_TEMPLATE = "gold/crawler/weekly/{week}.parquet"
GOLD_TOTAL_PATH = "gold/crawler/jobs_for_encoding.parquet"

LOCAL_TEMP_DIR = "data/temp/crawler"
LOCAL_SILVER_WEEKLY_PATH = f"{LOCAL_TEMP_DIR}/jobs_silver_weekly.parquet"
LOCAL_GOLD_WEEKLY_PATH = f"{LOCAL_TEMP_DIR}/jobs_for_encoding_weekly.parquet"
LOCAL_GOLD_TOTAL_PATH = f"{LOCAL_TEMP_DIR}/jobs_for_encoding.parquet"


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


def download_silver_week(client, week):
    # Tải Silver weekly của tuần mới
    object_path = SILVER_WEEKLY_TEMPLATE.format(week=week)

    exists = download_file_if_exists(
        client=client,
        object_path=object_path,
        local_path=LOCAL_SILVER_WEEKLY_PATH,
    )

    if not exists:
        raise FileNotFoundError(f"Silver weekly file not found: {object_path}")

    print(f"Downloaded: {object_path}")


def read_silver_week():
    # Đọc Silver weekly
    return pd.read_parquet(LOCAL_SILVER_WEEKLY_PATH)


def read_existing_gold(client):
    # Đọc Gold tổng nếu đã tồn tại
    exists = download_file_if_exists(
        client=client,
        object_path=GOLD_TOTAL_PATH,
        local_path=LOCAL_GOLD_TOTAL_PATH,
    )

    if not exists:
        return pd.DataFrame()

    return pd.read_parquet(LOCAL_GOLD_TOTAL_PATH)


def clean_text(value):
    # Chuẩn hóa text rỗng
    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_link_series(series):
    # Chuẩn hóa link để so sánh trùng
    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


def build_gold_week(silver_week):
    # Tạo dữ liệu Gold weekly để encode title và skills
    jobs = silver_week.copy()

    jobs["title_core"] = jobs["title_core"].apply(clean_text)
    jobs["skills_clean"] = jobs["skills_clean"].apply(clean_text)

    before_rows = len(jobs)

    jobs = jobs[
        (jobs["title_core"] != "")
        & (jobs["skills_clean"] != "")
    ].copy()

    after_rows = len(jobs)

    print(f"Rows before removing empty title/skills: {before_rows:,}")
    print(f"Rows after removing empty title/skills: {after_rows:,}")
    print(f"Removed rows: {before_rows - after_rows:,}")

    jobs["title_text"] = jobs["title_core"].apply(
        lambda value: f"Job title: {value}."
    )

    jobs["skills_text"] = jobs["skills_clean"].apply(
        lambda value: f"Skills: {value}."
    )

    output_columns = [
        "job_id",
        "link",

        "title_core",
        "skills_clean",
        "title_text",
        "skills_text",

        "company",
        "location_raw",
        "city",
        "country",

        "source",
        "crawl_week",
    ]

    return jobs[output_columns].copy()


def filter_new_gold_jobs(gold_week, existing_gold):
    # Chỉ giữ job chưa có trong Gold tổng
    if existing_gold.empty:
        return gold_week.copy()

    existing_links = set(
        normalize_link_series(existing_gold["link"])
    )

    gold_week = gold_week.copy()
    gold_week["link"] = normalize_link_series(gold_week["link"])

    gold_week_new = gold_week[
        ~gold_week["link"].isin(existing_links)
    ].copy()

    return gold_week_new


def assign_doc_id(gold_week_new, existing_gold):
    # Gán doc_id tăng dần cho job mới
    gold_week_new = gold_week_new.copy()

    if existing_gold.empty:
        start_id = 0
    else:
        start_id = int(existing_gold["doc_id"].max()) + 1

    gold_week_new.insert(
        0,
        "doc_id",
        range(start_id, start_id + len(gold_week_new)),
    )

    return gold_week_new


def build_gold_total(existing_gold, gold_week_new):
    # Append Gold weekly mới vào Gold tổng
    if existing_gold.empty:
        gold_total = gold_week_new.copy()
    else:
        gold_total = pd.concat(
            [
                existing_gold,
                gold_week_new,
            ],
            ignore_index=True,
        )

    gold_total["link"] = normalize_link_series(gold_total["link"])

    gold_total = gold_total.drop_duplicates(
        subset=["link"],
        keep="first",
    ).reset_index(drop=True)

    return gold_total


def save_local_files(gold_week_new, gold_total):
    # Lưu local parquet
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    gold_week_new.to_parquet(
        LOCAL_GOLD_WEEKLY_PATH,
        index=False,
    )

    gold_total.to_parquet(
        LOCAL_GOLD_TOTAL_PATH,
        index=False,
    )


def upload_outputs(client, week):
    # Upload Gold weekly và Gold tổng
    weekly_path = GOLD_WEEKLY_TEMPLATE.format(week=week)

    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=weekly_path,
        file_path=LOCAL_GOLD_WEEKLY_PATH,
    )

    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=GOLD_TOTAL_PATH,
        file_path=LOCAL_GOLD_TOTAL_PATH,
    )

    print(f"Uploaded: {weekly_path}")
    print(f"Uploaded: {GOLD_TOTAL_PATH}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--week",
        required=True,
        help="Tên tuần, ví dụ: week_2026_05_09",
    )

    args = parser.parse_args()

    client = get_minio_client()

    print("Downloading Silver weekly...")
    download_silver_week(client, args.week)

    print("Reading Silver weekly...")
    silver_week = read_silver_week()

    print(f"Silver weekly rows: {len(silver_week):,}")

    print("Building Gold weekly...")
    gold_week = build_gold_week(silver_week)

    print(f"Gold weekly rows before total dedupe: {len(gold_week):,}")

    print("Reading existing Gold total...")
    existing_gold = read_existing_gold(client)

    print(f"Existing Gold rows: {len(existing_gold):,}")

    print("Filtering new Gold jobs...")
    gold_week_new = filter_new_gold_jobs(
        gold_week=gold_week,
        existing_gold=existing_gold,
    )

    print(f"New Gold jobs: {len(gold_week_new):,}")

    print("Assigning doc_id...")
    gold_week_new = assign_doc_id(
        gold_week_new=gold_week_new,
        existing_gold=existing_gold,
    )

    print("Building Gold total...")
    gold_total = build_gold_total(
        existing_gold=existing_gold,
        gold_week_new=gold_week_new,
    )

    print(f"Gold total rows after append: {len(gold_total):,}")

    print("Saving local files...")
    save_local_files(
        gold_week_new=gold_week_new,
        gold_total=gold_total,
    )

    print("Uploading outputs...")
    upload_outputs(
        client=client,
        week=args.week,
    )

    print("Done.")


if __name__ == "__main__":
    main()