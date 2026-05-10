import re
import sys
from pathlib import Path

import pandas as pd

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    SILVER_KAGGLE_NORMALIZED,
    SILVER_KAGGLE_BASIC_CLEAN,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet,
    list_objects,
)


def clean_text_basic(value: object) -> str:
    # Chuẩn hóa text cơ bản
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def basic_clean_title(title: object) -> str:
    # Clean nhẹ job title, chưa chuẩn hóa sâu theo ngành
    text = clean_text_basic(title)

    # Xóa các cụm gây nhiễu thường gặp trong title
    noise_patterns = [
        r"\bremote\b",
        r"\bhybrid\b",
        r"\bonsite\b",
        r"\bon site\b",
        r"\bwork from home\b",
        r"\bwfh\b",
        r"\bfull time\b",
        r"\bfull-time\b",
        r"\bpart time\b",
        r"\bpart-time\b",
        r"\bcontract\b",
        r"\btemporary\b",
        r"\bfreelance\b",
        r"\binternship\b",
        r"\burgent\b",
        r"\bimmediate\b",
        r"\bhiring\b",
        r"\bapply now\b",
        r"\bm/f/d\b",
        r"\bf/m/d\b",
        r"\bw/m/d\b",
    ]

    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text)

    # Chuẩn hóa một số viết tắt phổ biến trong title
    title_alias = {
        "sr": "senior",
        "jr": "junior",
        "dev": "developer",
        "eng": "engineer",
        "mgr": "manager",
        "swe": "software engineer",
        "bi": "business intelligence",
        "ba": "business analyst",
        "ml": "machine learning",
    }

    # Giữ lại các ký tự có ích cho title kỹ thuật như C++, C#, .NET
    text = re.sub(r"[^a-z0-9\+\#\./\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    tokens = [
        title_alias.get(token, token)
        for token in text.split()
    ]

    return " ".join(tokens)


def split_basic_skills(skills: object) -> list[str]:
    # Split skills an toàn, không split bằng dấu chấm để tránh phá Node.js, .NET
    if pd.isna(skills):
        return []

    text = str(skills).strip()

    if not text:
        return []

    # Chỉ split bằng dấu phẩy, chấm phẩy, hoặc dấu |
    raw_items = re.split(r"[,;|]\s*", text)

    cleaned_items = []

    for item in raw_items:
        skill = item.strip().lower()

        # Giữ lại ký tự quan trọng trong skill: + # . / -
        skill = re.sub(r"[^a-z0-9\+\#\./\-\s]", " ", skill)
        skill = re.sub(r"\s+", " ", skill).strip()

        if skill:
            cleaned_items.append(skill)

    # Xóa trùng nhưng giữ thứ tự ban đầu
    return list(dict.fromkeys(cleaned_items))


def basic_clean_location(location: object) -> str:
    # Clean nhẹ location
    text = clean_text_basic(location)

    # Chuẩn hóa một số dấu phân tách
    text = text.replace("|", ",")
    text = re.sub(r"\s+", " ", text).strip()

    return text


def build_basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    clean_df = df.copy()

    # Clean nhẹ job title
    clean_df["job_title_basic_clean"] = clean_df["job_title_raw"].apply(
        basic_clean_title
    )

    # Clean nhẹ skills
    clean_df["skills_basic_clean"] = clean_df["skills_raw"].apply(
        split_basic_skills
    )

    # Clean nhẹ location
    clean_df["location_clean"] = clean_df["location_raw"].apply(
        basic_clean_location
    )

    # Đếm số skill sau split
    clean_df["skills_count"] = clean_df["skills_basic_clean"].apply(len)

    return clean_df


def main() -> None:
    print("Bắt đầu build Silver 02 Basic Clean cho Kaggle")

    # Kết nối MinIO
    client = get_minio_client()

    # Đọc dữ liệu Silver 01 Normalized
    print("\nBước 1: Đọc dữ liệu Silver 01 Normalized")
    normalized_df = read_parquet_from_minio(
        client=client,
        object_name=SILVER_KAGGLE_NORMALIZED,
    )

    # Clean nhẹ title, skills, location
    print("\nBước 2: Clean nhẹ job_title, skills, location")
    basic_clean_df = build_basic_clean(normalized_df)

    print("\nKết quả Basic Clean:")
    print(
        basic_clean_df[
            [
                "job_title_raw",
                "job_title_basic_clean",
                "skills_raw",
                "skills_basic_clean",
                "location_clean",
            ]
        ].head()
    )

    print(f"Số dòng, số cột: {basic_clean_df.shape}")

    # Lưu sang Silver 02 Basic Clean
    print("\nBước 3: Lưu dữ liệu sang Silver 02 Basic Clean")
    upload_df_parquet(
        client=client,
        df=basic_clean_df,
        object_name=SILVER_KAGGLE_BASIC_CLEAN,
    )

    # Kiểm tra vùng Silver 02
    print("\nBước 4: Kiểm tra vùng Silver 02 Basic Clean")
    list_objects(
        client=client,
        prefix="silver/kaggle/02_basic_clean/",
    )

    print("\nHoàn thành build Silver 02 Basic Clean.")


if __name__ == "__main__":
    main()