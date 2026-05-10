import ast
import re
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
    silver_crawler_normalized,
    silver_crawler_basic_clean,
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


def list_normalized_batches(client) -> list[str]:
    # Lấy danh sách batch đã có Silver 01 Normalized
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="silver/crawler/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/01_normalized/jobs_normalized.parquet"):
            continue

        # silver/crawler/week_2026_05_09/01_normalized/jobs_normalized.parquet
        parts = object_name.split("/")

        if len(parts) >= 3:
            batch_names.add(parts[2])

    return sorted(batch_names)


def find_unprocessed_batch(client) -> str | None:
    # Tìm batch đã normalized nhưng chưa basic clean
    batch_names = list_normalized_batches(client)

    if not batch_names:
        print("Không tìm thấy batch nào đã normalized.")
        return None

    for batch_name in batch_names:
        basic_clean_object = silver_crawler_basic_clean(batch_name)

        if object_exists(client, basic_clean_object):
            print(f"Bỏ qua batch đã basic clean: {batch_name}")
            continue

        return batch_name

    return None


def normalize_text(value) -> str:
    # Chuẩn hóa text cơ bản
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    text = str(value).strip()

    if text.lower() in ["nan", "none", "null"]:
        return ""

    return text


def clean_job_title(title: str) -> str:
    # Clean cơ bản job title
    text = normalize_text(title)

    # Chuẩn hóa dấu gạch và ký tự phân cách
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("|", " ")
    text = text.replace("/", " / ")

    # Xóa xuống dòng, tab và khoảng trắng thừa
    text = re.sub(r"[\n\r\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Xóa một số keyword tuyển dụng gây nhiễu
    noise_patterns = [
        r"\bhiring week\b",
        r"\bhot job\b",
        r"\burgent hiring\b",
        r"\bimmediate hiring\b",
        r"\btalent pool\b",
        r"\bvietnamese only\b",
        r"\boutsourcing\b",
    ]

    for pattern in noise_patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    # Xóa location hoặc office trong title
    location_patterns = [
        r"\bin hcmc office\b",
        r"\bin hanoi office\b",
        r"\bhcmc office\b",
        r"\bhanoi office\b",
        r"\bhcm office\b",
        r"\bhcm\b",
        r"\bhn\b",
    ]

    for pattern in location_patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    # Xóa nội dung ngoặc có tính chất mô tả phụ quá cụ thể
    removable_parentheses = [
        r"\(vietnamese only\)",
        r"\(outsourcing\)",
        r"\(contract\)",
        r"\(talent pool\)",
        r"\(non-technical background required\)",
        r"\(based in cambodia\)",
    ]

    for pattern in removable_parentheses:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    # Xóa khoảng trắng thừa lần cuối
    text = re.sub(r"\s+", " ", text).strip()

    # Xóa ký tự thừa ở đầu/cuối
    text = text.strip(" -_|/.,;:")

    return text


def clean_company(company: str) -> str:
    # Clean cơ bản company
    text = normalize_text(company)

    text = re.sub(r"[\n\r\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_location(location: str) -> str:
    # Clean cơ bản location
    text = normalize_text(location)

    text = re.sub(r"[\n\r\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def parse_skills(value) -> list[str]:
    # Chuyển skills_raw về list thật
    if value is None:
        return []

    if isinstance(value, float) and pd.isna(value):
        return []

    if isinstance(value, list):
        return [
            str(skill).strip()
            for skill in value
            if str(skill).strip()
            and str(skill).strip().lower() not in ["null", "none", "nan"]
        ]

    if isinstance(value, np.ndarray):
        return [
            str(skill).strip()
            for skill in value.tolist()
            if str(skill).strip()
            and str(skill).strip().lower() not in ["null", "none", "nan"]
        ]

    if isinstance(value, (tuple, set)):
        return [
            str(skill).strip()
            for skill in list(value)
            if str(skill).strip()
            and str(skill).strip().lower() not in ["null", "none", "nan"]
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
                    and str(skill).strip().lower() not in ["null", "none", "nan"]
                ]

            if isinstance(parsed, (tuple, set)):
                return [
                    str(skill).strip()
                    for skill in list(parsed)
                    if str(skill).strip()
                    and str(skill).strip().lower() not in ["null", "none", "nan"]
                ]
        except Exception:
            pass

        return [text]

    return []


def clean_skill(skill: str) -> str:
    # Clean cơ bản từng skill
    text = normalize_text(skill)

    text = re.sub(r"[\n\r\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Chuẩn hóa một số skill phổ biến
    replacements = {
        "Ai": "AI",
        "ai": "AI",
        "Power Bi": "Power BI",
        "power bi": "Power BI",
        "Ms Excel": "Microsoft Excel",
        "MS Excel": "Microsoft Excel",
        "Excel": "Microsoft Excel",
        "Sql": "SQL",
        "sql": "SQL",
        "Javascript": "JavaScript",
        "javascript": "JavaScript",
        "Typescript": "TypeScript",
        "typescript": "TypeScript",
        "Nodejs": "Node.js",
        "NodeJS": "Node.js",
        "nodejs": "Node.js",
        "Reactjs": "React",
        "ReactJS": "React",
        "reactjs": "React",
        "Vuejs": "Vue.js",
        "VueJS": "Vue.js",
        "Devops": "DevOps",
        "devops": "DevOps",
        "Apis": "APIs",
        "Restful Apis": "RESTful APIs",
        "Aws": "AWS",
        "Aws Cloud": "AWS Cloud",
        "Pytorch": "PyTorch",
        "Tensorflow": "TensorFlow",
        "Nlp": "NLP",
        "LlM": "LLM",
        "LLM": "LLM",
        "Crm": "CRM",
        "CRM": "CRM",
        "Jira": "JIRA",
        "jira": "JIRA",
    }

    if text in replacements:
        return replacements[text]

    return text


def clean_skills_list(value) -> list[str]:
    # Clean danh sách skills
    skills = parse_skills(value)

    cleaned_skills = []

    for skill in skills:
        clean_value = clean_skill(skill)

        if clean_value:
            cleaned_skills.append(clean_value)

    # Xóa trùng nhưng giữ thứ tự
    return list(dict.fromkeys(cleaned_skills))


def build_basic_clean_df(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    result_df = df.copy()

    # Clean title
    result_df["job_title_basic_clean"] = result_df["job_title_raw"].apply(
        clean_job_title
    )

    # Clean company
    result_df["company_clean"] = result_df["company"].apply(
        clean_company
    )

    # Clean location
    result_df["location_basic_clean"] = result_df["location_raw"].apply(
        clean_location
    )

    # Clean skills
    result_df["skills_basic_clean"] = result_df["skills_raw"].apply(
        clean_skills_list
    )

    # Đếm số skill sau basic clean
    result_df["skills_count_basic"] = result_df["skills_basic_clean"].apply(
        len
    )

    # Đánh dấu dữ liệu tối thiểu
    result_df["has_title"] = result_df["job_title_basic_clean"].apply(
        lambda value: str(value).strip() != ""
    )

    result_df["has_skills"] = result_df["skills_count_basic"] > 0

    result_df["has_location"] = result_df["location_basic_clean"].apply(
        lambda value: str(value).strip() != ""
    )

    return result_df


def main() -> None:
    print("Bắt đầu build Silver 02 Basic Clean cho Crawler")

    # Kết nối MinIO
    client = get_minio_client()

    # Tìm batch chưa basic clean
    print("\nBước 1: Tìm batch crawler chưa basic clean")
    batch_name = find_unprocessed_batch(client)

    if batch_name is None:
        print("\nKhông có batch crawler mới cần basic clean.")
        print("Dừng bước 03.")
        return

    normalized_object = silver_crawler_normalized(batch_name)
    basic_clean_object = silver_crawler_basic_clean(batch_name)

    print(f"Batch cần xử lý: {batch_name}")
    print(f"Input Silver 01: s3://{MINIO_BUCKET}/{normalized_object}")
    print(f"Output Silver 02: s3://{MINIO_BUCKET}/{basic_clean_object}")

    # Đọc Silver 01 Normalized
    print("\nBước 2: Đọc dữ liệu Silver 01 Normalized")
    normalized_df = read_parquet_from_minio(
        client=client,
        object_name=normalized_object,
    )

    # Basic clean
    print("\nBước 3: Clean cơ bản title, company, location, skills")
    basic_clean_df = build_basic_clean_df(normalized_df)

    # Kiểm tra nhanh kết quả
    print("\nSample Basic Clean:")
    print(
        basic_clean_df[
            [
                "job_title_raw",
                "job_title_basic_clean",
                "company",
                "company_clean",
                "location_raw",
                "location_basic_clean",
                "skills_raw",
                "skills_basic_clean",
                "skills_count_basic",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(f"\nSố dòng, số cột: {basic_clean_df.shape}")

    print("\nThống kê dữ liệu thiếu:")
    print("Thiếu title:", (~basic_clean_df["has_title"]).sum())
    print("Thiếu skills:", (~basic_clean_df["has_skills"]).sum())
    print("Thiếu location:", (~basic_clean_df["has_location"]).sum())

    print("\nThống kê skills_count_basic:")
    print(basic_clean_df["skills_count_basic"].describe())

    # Lưu Silver 02 Basic Clean
    print("\nBước 4: Lưu Silver 02 Basic Clean lên MinIO")
    upload_df_parquet(
        client=client,
        df=basic_clean_df,
        object_name=basic_clean_object,
    )

    # Kiểm tra vùng Silver Crawler Basic Clean
    print("\nBước 5: Kiểm tra vùng Silver Crawler Basic Clean")
    list_objects(
        client=client,
        prefix=f"silver/crawler/{batch_name}/02_basic_clean/",
    )

    print("\nHoàn thành build Silver 02 Basic Clean cho Crawler.")


if __name__ == "__main__":
    main()