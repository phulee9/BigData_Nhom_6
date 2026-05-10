import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    SILVER_KAGGLE_FINAL_CLEAN,
    GOLD_KAGGLE_JOBS_FOR_ENCODING,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet_local_temp,
    list_objects,
)


def parse_skills(value) -> list[str]:
    # Chuyển skills_canonical về list thật
    if value is None:
        return []

    # Xử lý NaN dạng float
    if isinstance(value, float) and pd.isna(value):
        return []

    # Xử lý list Python
    if isinstance(value, list):
        return [
            str(skill).strip()
            for skill in value
            if str(skill).strip()
        ]

    # Xử lý numpy array khi đọc list từ Parquet
    if isinstance(value, np.ndarray):
        return [
            str(skill).strip()
            for skill in value.tolist()
            if str(skill).strip()
        ]

    # Xử lý tuple hoặc set
    if isinstance(value, (tuple, set)):
        return [
            str(skill).strip()
            for skill in list(value)
            if str(skill).strip()
        ]

    # Xử lý pandas Series
    if isinstance(value, pd.Series):
        return [
            str(skill).strip()
            for skill in value.tolist()
            if str(skill).strip()
        ]

    # Xử lý string
    if isinstance(value, str):
        text = value.strip()

        # String rỗng hoặc biểu diễn rỗng
        if text in ["", "[]", "nan", "None", "null"]:
            return []

        # String dạng "['SQL', 'Power BI']"
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

        # String thường thì coi là một skill
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
    # Chọn các cột cần giữ lại cho recommendation
    selected_cols = [
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
    ]

    # Chỉ lấy các cột đang tồn tại
    existing_cols = [
        col for col in selected_cols
        if col in df.columns
    ]

    gold_df = df[existing_cols].copy()

    # Nếu thiếu cột nào thì tạo cột rỗng
    for col in selected_cols:
        if col not in gold_df.columns:
            gold_df[col] = ""

    # Chuẩn hóa title sạch
    gold_df["job_title_canonical"] = (
        gold_df["job_title_canonical"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Loại các dòng không có title sạch
    before_title_filter = len(gold_df)

    gold_df = gold_df[
        gold_df["job_title_canonical"] != ""
    ].copy()

    after_title_filter = len(gold_df)

    # Chuẩn hóa location_final
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

    # Tạo skills_count_final để lọc dòng không có skill
    gold_df["skills_count_final"] = gold_df["skills_canonical"].apply(
        lambda x: len(parse_skills(x))
    )

    # Loại các dòng không có skill vì không phục vụ bài toán gợi ý missing skills
    before_skill_filter = len(gold_df)

    gold_df = gold_df[
        gold_df["skills_count_final"] > 0
    ].copy()

    after_skill_filter = len(gold_df)

    # Tạo title_text để encode title index
    gold_df["title_text"] = gold_df.apply(
        build_title_text,
        axis=1,
    )

    # Tạo skills_text để encode skills index
    gold_df["skills_text"] = gold_df.apply(
        build_skills_text,
        axis=1,
    )

    # Tạo full_text để encode full index
    gold_df["full_text"] = gold_df.apply(
        build_full_text,
        axis=1,
    )

    # In thống kê số dòng bị loại
    print("\nThống kê lọc Gold:")
    print(f"Số dòng ban đầu: {before_title_filter}")
    print(f"Số dòng bị loại do thiếu title: {before_title_filter - after_title_filter}")
    print(f"Số dòng bị loại do thiếu skill: {before_skill_filter - after_skill_filter}")
    print(f"Số dòng còn lại cho Gold Encode: {after_skill_filter}")

    return gold_df


def main() -> None:
    print("Bắt đầu build Gold Encode cho Kaggle")

    # Kết nối MinIO
    client = get_minio_client()

    # Đọc Silver 05 Final Clean
    print("\nBước 1: Đọc Silver 05 Final Clean")
    final_df = read_parquet_from_minio(
        client=client,
        object_name=SILVER_KAGGLE_FINAL_CLEAN,
    )

    # Kiểm tra nhanh kiểu dữ liệu của skills_canonical
    print("\nKiểu dữ liệu của skills_canonical:")
    print(
        final_df["skills_canonical"]
        .apply(type)
        .value_counts()
        .head(10)
    )

    # Tạo Gold Encode
    print("\nBước 2: Tạo Gold Encode dataset")
    gold_df = build_gold_encode_df(final_df)

    # Kiểm tra nhanh dữ liệu Gold
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

    # Thống kê số lượng skill
    print("\nThống kê skills_count_final:")
    print(gold_df["skills_count_final"].describe())

    # Kiểm tra số dòng không có skill sau khi lọc
    no_skill_count = (
        gold_df["skills_count_final"] == 0
    ).sum()

    print("\nSố dòng không có skill trong Gold:")
    print(no_skill_count)

    print("\nTỷ lệ dòng không có skill trong Gold:")
    print(round(no_skill_count / len(gold_df) * 100, 2), "%")

    # In sample dòng có skill để kiểm tra
    print("\nSample dòng có skill:")
    print(
        gold_df[
            [
                "job_title_canonical",
                "location_final",
                "skills_canonical",
                "skills_text",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    # Lưu Gold Encode lên MinIO bằng file tạm local để tránh hết RAM
    print("\nBước 3: Lưu Gold Encode lên MinIO")
    upload_df_parquet_local_temp(
        client=client,
        df=gold_df,
        object_name=GOLD_KAGGLE_JOBS_FOR_ENCODING,
        local_temp_path="data/temp/jobs_for_encoding.parquet",
    )

    # Kiểm tra vùng Gold
    print("\nBước 4: Kiểm tra vùng Gold Kaggle Encode")
    list_objects(
        client=client,
        prefix="gold/kaggle/encode/",
    )

    print("\nHoàn thành build Gold Encode cho Kaggle.")


if __name__ == "__main__":
    main()