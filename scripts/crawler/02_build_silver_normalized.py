import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
from minio.error import S3Error

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    bronze_crawler_raw,
    silver_crawler_normalized,
)
from src.storage.minio_client import (
    get_minio_client,
    upload_df_parquet,
    list_objects,
)


def object_exists(client, object_name: str) -> bool:
    # Kiểm tra object đã tồn tại trên MinIO chưa
    try:
        client.stat_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
        )

        return True

    except S3Error as error:
        if error.code == "NoSuchKey":
            return False

        raise error


def list_crawler_raw_batches(client) -> list[str]:
    # Lấy danh sách batch đã có trong bronze/crawler/raw/
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="bronze/crawler/raw/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/jobs_raw.json"):
            continue

        # bronze/crawler/raw/week_2026_05_09/jobs_raw.json
        parts = object_name.split("/")

        if len(parts) >= 4:
            batch_names.add(parts[3])

    return sorted(batch_names)


def find_unprocessed_batch(client) -> str | None:
    # Tìm batch raw chưa được build Silver Normalized
    batch_names = list_crawler_raw_batches(client)

    if not batch_names:
        print("Không tìm thấy batch raw nào trong bronze/crawler/raw/")
        return None

    for batch_name in batch_names:
        silver_object_name = silver_crawler_normalized(batch_name)

        if object_exists(client, silver_object_name):
            print(f"Bỏ qua batch đã normalized: {batch_name}")
            continue

        return batch_name

    return None


def read_json_from_minio(client, object_name: str) -> list[dict]:
    # Đọc file JSON crawler raw từ MinIO
    response = client.get_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
    )

    try:
        data = response.read()
        records = json.loads(data.decode("utf-8"))
    finally:
        response.close()
        response.release_conn()

    if not isinstance(records, list):
        raise ValueError("File JSON raw phải có dạng list các job object.")

    return records


def make_source_job_id(link: str, title: str, company: str) -> str:
    # Tạo mã job ổn định từ link, title và company
    raw_key = f"{link}|{title}|{company}".lower().strip()

    return hashlib.md5(
        raw_key.encode("utf-8")
    ).hexdigest()


def normalize_text(value) -> str:
    # Chuẩn hóa text cơ bản
    if value is None:
        return ""

    return str(value).strip()


def normalize_skills(value) -> list[str]:
    # Đảm bảo skills_raw luôn là list
    if value is None:
        return []

    if isinstance(value, list):
        return [
            str(skill).strip()
            for skill in value
            if str(skill).strip()
        ]

    if isinstance(value, str):
        text = value.strip()

        if not text:
            return []

        if text.lower() in ["null", "none", "nan"]:
            return []

        return [text]

    return []


def build_normalized_df(
    records: list[dict],
    batch_name: str,
) -> pd.DataFrame:
    # Chuyển JSON raw về schema chuẩn
    rows = []

    for item in records:
        title = normalize_text(item.get("title", ""))
        company = normalize_text(item.get("company", ""))
        location = normalize_text(item.get("location", ""))
        experience = normalize_text(item.get("experience", ""))
        link = normalize_text(item.get("link", ""))
        skills = normalize_skills(item.get("skills", []))

        source_job_id = make_source_job_id(
            link=link,
            title=title,
            company=company,
        )

        rows.append(
            {
                "source": "crawler",
                "source_job_id": source_job_id,
                "job_url": link,
                "job_link": link,
                "company": company,
                "job_title_raw": title,
                "location_raw": location,
                "experience_raw": experience,
                "skills_raw": skills,
                "crawl_batch": batch_name,
            }
        )

    df = pd.DataFrame(rows)

    # Loại trùng trong chính batch hiện tại
    before_dedup = len(df)

    df = df.drop_duplicates(
        subset=["source_job_id"],
        keep="first",
    ).copy()

    after_dedup = len(df)

    print("\nThống kê normalized:")
    print(f"Số dòng trước khi dedup: {before_dedup}")
    print(f"Số dòng sau khi dedup: {after_dedup}")
    print(f"Số dòng bị loại do trùng trong batch: {before_dedup - after_dedup}")

    return df


def main() -> None:
    print("Bắt đầu build Silver 01 Normalized cho Crawler")

    # Kết nối MinIO
    client = get_minio_client()

    # Tìm batch raw chưa xử lý normalized
    print("\nBước 1: Tìm batch crawler chưa normalized")
    batch_name = find_unprocessed_batch(client)

    if batch_name is None:
        print("\nKhông có batch crawler mới cần normalized.")
        print("Dừng bước 02.")
        return

    bronze_object_name = bronze_crawler_raw(batch_name)
    silver_object_name = silver_crawler_normalized(batch_name)

    print(f"Batch cần xử lý: {batch_name}")
    print(f"Input Bronze: s3://{MINIO_BUCKET}/{bronze_object_name}")
    print(f"Output Silver: s3://{MINIO_BUCKET}/{silver_object_name}")

    # Đọc JSON raw từ Bronze
    print("\nBước 2: Đọc dữ liệu Bronze Crawler Raw")
    records = read_json_from_minio(
        client=client,
        object_name=bronze_object_name,
    )

    print(f"Số record raw đọc được: {len(records)}")

    # Chuẩn hóa schema
    print("\nBước 3: Chuẩn hóa schema crawler")
    normalized_df = build_normalized_df(
        records=records,
        batch_name=batch_name,
    )

    print("\nSample normalized:")
    print(
        normalized_df.head(10).to_string(index=False)
    )

    print(f"\nSố dòng, số cột: {normalized_df.shape}")

    # Lưu Silver 01 Normalized
    print("\nBước 4: Lưu Silver 01 Normalized lên MinIO")
    upload_df_parquet(
        client=client,
        df=normalized_df,
        object_name=silver_object_name,
    )

    # Kiểm tra vùng Silver Crawler của batch
    print("\nBước 5: Kiểm tra vùng Silver Crawler Normalized")
    list_objects(
        client=client,
        prefix=f"silver/crawler/{batch_name}/01_normalized/",
    )

    print("\nHoàn thành build Silver 01 Normalized cho Crawler.")


if __name__ == "__main__":
    main()