import sys
from pathlib import Path

import pandas as pd

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    BRONZE_KAGGLE_JOB_POSTINGS,
    BRONZE_KAGGLE_JOB_SKILLS,
    SILVER_KAGGLE_NORMALIZED,
)
from src.storage.minio_client import (
    get_minio_client,
    read_csv_from_minio,
    upload_df_parquet,
    list_objects,
)


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    # Tìm cột đầu tiên tồn tại trong DataFrame
    for col in candidates:
        if col in df.columns:
            return col

    return None


def normalize_kaggle_schema(
    jobs_df: pd.DataFrame,
    skills_df: pd.DataFrame,
) -> pd.DataFrame:
    # Kiểm tra khóa merge
    if "job_link" not in jobs_df.columns:
        raise ValueError("Không tìm thấy cột job_link trong linkedin_job_postings.csv")

    if "job_link" not in skills_df.columns:
        raise ValueError("Không tìm thấy cột job_link trong job_skills.csv")

    # Merge job postings và job skills
    merged_df = jobs_df.merge(
        skills_df,
        on="job_link",
        how="left",
    )

    # Tìm các cột quan trọng theo nhiều tên khả dĩ
    title_col = find_column(
        merged_df,
        ["job_title", "title"],
    )

    company_col = find_column(
        merged_df,
        ["company", "company_name"],
    )

    skills_col = find_column(
        merged_df,
        ["job_skills", "skills"],
    )

    location_col = find_column(
        merged_df,
        ["job_location", "location", "search_city", "search_country"],
    )

    description_col = find_column(
        merged_df,
        ["job_summary", "description", "job_description"],
    )

    posted_date_col = find_column(
        merged_df,
        ["first_seen", "posted_date", "date_posted"],
    )

    # Tạo schema chuẩn dùng chung cho Kaggle và Crawler sau này
    normalized_df = pd.DataFrame()

    normalized_df["source"] = "kaggle"
    normalized_df["source_job_id"] = merged_df["job_link"].astype(str)
    normalized_df["job_link"] = merged_df["job_link"].astype(str)
    normalized_df["job_url"] = merged_df["job_link"].astype(str)

    normalized_df["company"] = (
        merged_df[company_col].astype(str) if company_col else ""
    )

    normalized_df["job_title_raw"] = (
        merged_df[title_col].astype(str) if title_col else ""
    )

    normalized_df["skills_raw"] = (
        merged_df[skills_col].astype(str) if skills_col else ""
    )

    normalized_df["location_raw"] = (
        merged_df[location_col].astype(str) if location_col else ""
    )

    normalized_df["description_raw"] = (
        merged_df[description_col].astype(str) if description_col else ""
    )

    normalized_df["posted_date"] = (
        merged_df[posted_date_col].astype(str) if posted_date_col else ""
    )

    normalized_df["crawl_date"] = ""

    # Xóa trùng theo job_link nếu có
    normalized_df = normalized_df.drop_duplicates(
        subset=["job_link"],
        keep="first",
    )

    return normalized_df


def main() -> None:
    # Kết nối MinIO
    client = get_minio_client()

    print("Bắt đầu build Silver 01 Normalized cho Kaggle")

    # Đọc 2 file raw từ Bronze
    print("\nBước 1: Đọc linkedin_job_postings.csv từ Bronze")
    jobs_df = read_csv_from_minio(
        client=client,
        object_name=BRONZE_KAGGLE_JOB_POSTINGS,
    )

    print("\nBước 2: Đọc job_skills.csv từ Bronze")
    skills_df = read_csv_from_minio(
        client=client,
        object_name=BRONZE_KAGGLE_JOB_SKILLS,
    )

    # In danh sách cột để kiểm tra nhanh
    print("\nCột trong jobs_df:")
    print(list(jobs_df.columns))

    print("\nCột trong skills_df:")
    print(list(skills_df.columns))

    # Merge và chuẩn hóa schema
    print("\nBước 3: Merge và chuẩn hóa schema")
    normalized_df = normalize_kaggle_schema(
        jobs_df=jobs_df,
        skills_df=skills_df,
    )

    print("\nKết quả normalized:")
    print(normalized_df.head())
    print(f"Số dòng, số cột: {normalized_df.shape}")

    # Lưu sang Silver 01 Normalized
    print("\nBước 4: Lưu dữ liệu sang Silver 01 Normalized")
    upload_df_parquet(
        client=client,
        df=normalized_df,
        object_name=SILVER_KAGGLE_NORMALIZED,
    )

    # Kiểm tra file đã lưu
    print("\nBước 5: Kiểm tra vùng Silver 01 Normalized")
    list_objects(
        client=client,
        prefix="silver/kaggle/01_normalized/",
    )

    print("\nHoàn thành build Silver 01 Normalized.")


if __name__ == "__main__":
    main()