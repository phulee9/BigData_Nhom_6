import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from minio.error import S3Error

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    silver_crawler_final_clean,
    gold_crawler_jobs_for_encoding_batch,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
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


def list_final_clean_batches(client) -> list[str]:
    # Lấy danh sách batch đã có Silver 05 Final Clean
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="silver/crawler/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/05_final_clean/jobs_final_clean.parquet"):
            continue

        # silver/crawler/week_2026_05_09/05_final_clean/jobs_final_clean.parquet
        parts = object_name.split("/")

        if len(parts) >= 3:
            batch_names.add(parts[2])

    return sorted(batch_names)


def find_unprocessed_batch(client) -> str | None:
    # Tìm batch đã final clean nhưng chưa build Gold Encode
    batch_names = list_final_clean_batches(client)

    if not batch_names:
        print("Không tìm thấy batch nào đã final clean.")
        return None

    for batch_name in batch_names:
        gold_object = gold_crawler_jobs_for_encoding_batch(batch_name)

        if object_exists(client, gold_object):
            print(f"Bỏ qua batch đã build Gold Encode: {batch_name}")
            continue

        return batch_name

    return None


def parse_skills(value) -> list[str]:
    # Chuyển skills_canonical về list thật
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
        text = value.strip()

        if text.lower() in ["", "[]", "nan", "none", "null"]:
            return []

        try:
            parsed = ast.literal_eval(text)

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

        return [text]

    return []


def skills_to_text(skills: list[str]) -> str:
    # Chuyển list skills thành chuỗi text
    clean_skills = [
        str(skill).strip()
        for skill in skills
        if str(skill).strip()
    ]

    if not clean_skills:
        return "Not specified"

    return ", ".join(clean_skills)


def build_title_text(row: pd.Series) -> str:
    # Tạo text riêng cho title index
    title = row.get("job_title_canonical", "")

    if pd.isna(title) or str(title).strip() == "":
        title = "Not specified"

    return f"Job title: {str(title).strip()}."


def build_skills_text(row: pd.Series) -> str:
    # Tạo text riêng cho skills index
    skills = parse_skills(row.get("skills_canonical", []))
    skills_text = skills_to_text(skills)

    return f"Required skills: {skills_text}."


def build_full_text(row: pd.Series) -> str:
    # Tạo text tổng hợp theo đúng input: title + location + skills
    title = row.get("job_title_canonical", "")
    location = row.get("location_final", "")

    if pd.isna(title) or str(title).strip() == "":
        title = "Not specified"

    if pd.isna(location) or str(location).strip() == "":
        location = "Unknown"

    skills = parse_skills(row.get("skills_canonical", []))
    skills_text = skills_to_text(skills)

    return (
        f"Job title: {str(title).strip()}. "
        f"Location: {str(location).strip()}. "
        f"Required skills: {skills_text}."
    )


def build_gold_encode_df(df: pd.DataFrame) -> pd.DataFrame:
    # Chọn các cột cần giữ lại để đồng nhất với Gold Kaggle
    selected_cols = [
        "source",
        "source_job_id",
        "job_link",
        "job_url",
        "company_clean",
        "job_title_canonical",
        "occupation_group_final",
        "occupation_family_final",
        "seniority",
        "city_clean",
        "country_clean",
        "location_final",
        "skills_canonical",
        "skills_count_final",
        "crawl_batch",
        "is_valid_for_gold",
    ]

    existing_cols = [
        col for col in selected_cols
        if col in df.columns
    ]

    gold_df = df[existing_cols].copy()

    # Tạo cột thiếu nếu cần
    for col in selected_cols:
        if col not in gold_df.columns:
            gold_df[col] = ""

    # Đổi company_clean về company để giống Gold Kaggle
    gold_df["company"] = (
        gold_df["company_clean"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Chuẩn hóa title
    gold_df["job_title_canonical"] = (
        gold_df["job_title_canonical"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Chuẩn hóa location
    gold_df["location_final"] = (
        gold_df["location_final"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    gold_df.loc[
        gold_df["location_final"] == "",
        "location_final",
    ] = "Unknown"

    # Tính lại skills_count_final để chắc chắn đúng kiểu list
    gold_df["skills_count_final"] = gold_df["skills_canonical"].apply(
        lambda value: len(parse_skills(value))
    )

    before_filter = len(gold_df)

    # Lọc dòng hợp lệ cho Gold
    gold_df = gold_df[
        (gold_df["job_title_canonical"] != "")
        & (gold_df["skills_count_final"] > 0)
    ].copy()

    after_filter = len(gold_df)

    # Tạo text để encode
    gold_df["title_text"] = gold_df.apply(
        build_title_text,
        axis=1,
    )

    gold_df["skills_text"] = gold_df.apply(
        build_skills_text,
        axis=1,
    )

    gold_df["full_text"] = gold_df.apply(
        build_full_text,
        axis=1,
    )

    # Sắp xếp lại cột đúng chuẩn Gold
    final_cols = [
        "source",
        "source_job_id",
        "job_link",
        "job_url",
        "company",
        "job_title_canonical",
        "occupation_group_final",
        "occupation_family_final",
        "seniority",
        "city_clean",
        "country_clean",
        "location_final",
        "skills_canonical",
        "skills_count_final",
        "title_text",
        "skills_text",
        "full_text",
        "crawl_batch",
    ]

    gold_df = gold_df[final_cols].copy()

    print("\nThống kê lọc Gold:")
    print(f"Số dòng trước lọc: {before_filter}")
    print(f"Số dòng sau lọc: {after_filter}")
    print(f"Số dòng bị loại: {before_filter - after_filter}")

    return gold_df


def main() -> None:
    print("Bắt đầu build Gold Encode cho Crawler")

    # Kết nối MinIO
    client = get_minio_client()

    # Tìm batch chưa build Gold
    print("\nBước 1: Tìm batch crawler chưa build Gold Encode")
    batch_name = find_unprocessed_batch(client)

    if batch_name is None:
        print("\nKhông có batch crawler mới cần build Gold Encode.")
        print("Dừng bước 07.")
        return

    final_clean_object = silver_crawler_final_clean(batch_name)
    gold_object = gold_crawler_jobs_for_encoding_batch(batch_name)

    print(f"Batch cần xử lý: {batch_name}")
    print(f"Input Silver 05: s3://{MINIO_BUCKET}/{final_clean_object}")
    print(f"Output Gold: s3://{MINIO_BUCKET}/{gold_object}")

    # Đọc Silver 05 Final Clean
    print("\nBước 2: Đọc Silver 05 Final Clean")
    final_df = read_parquet_from_minio(
        client=client,
        object_name=final_clean_object,
    )

    # Build Gold Encode
    print("\nBước 3: Tạo Gold Encode dataset")
    gold_df = build_gold_encode_df(final_df)

    print("\nSample Gold Encode:")
    print(
        gold_df[
            [
                "job_title_canonical",
                "location_final",
                "skills_canonical",
                "skills_count_final",
                "title_text",
                "skills_text",
                "full_text",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(f"\nSố dòng, số cột: {gold_df.shape}")

    print("\nThống kê skills_count_final:")
    print(gold_df["skills_count_final"].describe())

    # Lưu Gold batch lên MinIO
    print("\nBước 4: Lưu Gold Encode batch lên MinIO")
    upload_df_parquet(
        client=client,
        df=gold_df,
        object_name=gold_object,
    )

    # Kiểm tra vùng Gold Crawler Batch
    print("\nBước 5: Kiểm tra Gold Crawler Batch")
    list_objects(
        client=client,
        prefix=f"gold/crawler/batches/{batch_name}/",
    )

    print("\nHoàn thành build Gold Encode cho Crawler.")


if __name__ == "__main__":
    main()