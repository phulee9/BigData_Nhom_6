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
    silver_crawler_industry_clean,
    silver_crawler_final_clean,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet,
    list_objects,
)


OCCUPATION_FAMILY_MAP = {
    "Data & Analytics": "Technology & Analytics",
    "IT / Software": "Technology & Analytics",
    "Engineering": "Engineering",
    "Finance & Accounting": "Business & Finance",
    "Sales": "Commercial",
    "Marketing / Communications": "Commercial",
    "Human Resources": "Professional Services",
    "Legal": "Professional Services",
    "Customer Service": "Operations",
    "Logistics / Supply Chain": "Operations",
    "Manufacturing / Production": "Operations",
    "Retail / Hospitality": "Commercial",
    "Healthcare": "Healthcare",
    "Education / Training": "Education",
    "Other / Unknown": "Other / Unknown",
}


CITY_ALIASES = {
    "hcm": "Ho Chi Minh",
    "hcmc": "Ho Chi Minh",
    "ho chi minh": "Ho Chi Minh",
    "ho chi minh city": "Ho Chi Minh",
    "hồ chí minh": "Ho Chi Minh",

    "hn": "Hanoi",
    "ha noi": "Hanoi",
    "hanoi": "Hanoi",
    "hà nội": "Hanoi",

    "danang": "Da Nang",
    "da nang": "Da Nang",
    "đà nẵng": "Da Nang",

    "haiphong": "Hai Phong",
    "hai phong": "Hai Phong",
    "hải phòng": "Hai Phong",
}


COUNTRY_ALIASES = {
    "vietnam": "Vietnam",
    "viet nam": "Vietnam",
    "việt nam": "Vietnam",

    "united states": "United States",
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "america": "United States",

    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "england": "United Kingdom",

    "canada": "Canada",
    "australia": "Australia",
    "india": "India",
    "france": "France",
    "germany": "Germany",
    "china": "China",
    "japan": "Japan",
    "south korea": "South Korea",
    "korea": "South Korea",

    "singapore": "Singapore",
    "malaysia": "Malaysia",
    "thailand": "Thailand",
    "indonesia": "Indonesia",
    "philippines": "Philippines",
    "mexico": "Mexico",
    "brazil": "Brazil",
    "ireland": "Ireland",
    "netherlands": "Netherlands",
}


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


def list_industry_clean_batches(client) -> list[str]:
    # Lấy danh sách batch đã có Silver 04 Industry Clean
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="silver/crawler/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/04_industry_clean/jobs_industry_clean.parquet"):
            continue

        # silver/crawler/week_2026_05_09/04_industry_clean/jobs_industry_clean.parquet
        parts = object_name.split("/")

        if len(parts) >= 3:
            batch_names.add(parts[2])

    return sorted(batch_names)


def find_unprocessed_batch(client) -> str | None:
    # Tìm batch đã industry clean nhưng chưa final clean
    batch_names = list_industry_clean_batches(client)

    if not batch_names:
        print("Không tìm thấy batch nào đã industry clean.")
        return None

    for batch_name in batch_names:
        final_clean_object = silver_crawler_final_clean(batch_name)

        if object_exists(client, final_clean_object):
            print(f"Bỏ qua batch đã final clean: {batch_name}")
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

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def is_country(value: str) -> bool:
    # Kiểm tra một chuỗi có phải tên quốc gia không
    text = normalize_text(value)
    key = text.lower()

    return key in COUNTRY_ALIASES


def standardize_country(value: str) -> str:
    # Chuẩn hóa tên quốc gia
    text = normalize_text(value)
    key = text.lower()

    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]

    if not text:
        return "Unknown"

    return text.title()


def standardize_city(value: str) -> str:
    # Chuẩn hóa tên thành phố/tỉnh
    text = normalize_text(value)
    key = text.lower()

    if key in CITY_ALIASES:
        return CITY_ALIASES[key]

    if not text:
        return ""

    return text.title()


def clean_location(location: str) -> tuple[str, str, str]:
    # Clean location theo cách giống luồng Kaggle:
    # nhận diện country trước, phần còn lại coi là city
    text = normalize_text(location)

    if not text:
        return "", "Unknown", "Unknown"

    # Chuẩn hóa dấu phân tách
    text = text.replace(" - ", ", ")
    text = text.replace("|", ",")
    text = re.sub(r"\s*,\s*", ",", text)

    parts = [
        part.strip()
        for part in text.split(",")
        if part.strip()
    ]

    if not parts:
        return "", "Unknown", "Unknown"

    # Trường hợp chỉ có 1 phần
    if len(parts) == 1:
        only_value = parts[0]

        # Nếu là country thì chỉ có country
        if is_country(only_value):
            country_clean = standardize_country(only_value)
            return "", country_clean, country_clean

        # Nếu chỉ là city mà không có country thì không đoán bừa
        city_clean = standardize_city(only_value)
        country_clean = "Unknown"

        if city_clean:
            location_final = f"{city_clean}, {country_clean}"
        else:
            location_final = country_clean

        return city_clean, country_clean, location_final

    # Trường hợp có nhiều phần
    country_index = None

    for index, part in enumerate(parts):
        if is_country(part):
            country_index = index
            break

    # Nếu tìm thấy country trong chuỗi
    if country_index is not None:
        country_clean = standardize_country(parts[country_index])

        # City là phần còn lại gần country nhất
        city_candidates = [
            part
            for i, part in enumerate(parts)
            if i != country_index
        ]

        if city_candidates:
            # Ưu tiên phần đứng ngay trước hoặc ngay sau country
            if country_index > 0:
                city_raw = parts[country_index - 1]
            else:
                city_raw = city_candidates[0]

            city_clean = standardize_city(city_raw)
        else:
            city_clean = ""

    # Nếu không tìm thấy country, mặc định phần đầu là city, phần cuối là country dạng text
    else:
        city_clean = standardize_city(parts[0])
        country_clean = standardize_country(parts[-1])

    if city_clean:
        location_final = f"{city_clean}, {country_clean}"
    else:
        location_final = country_clean

    return city_clean, country_clean, location_final


def clean_occupation_group(value: str) -> str:
    # Chuẩn hóa occupation group final
    text = normalize_text(value)

    if not text:
        return "Other / Unknown"

    return text


def get_occupation_family(group: str) -> str:
    # Map occupation group sang occupation family
    group = clean_occupation_group(group)

    return OCCUPATION_FAMILY_MAP.get(
        group,
        "Other / Unknown",
    )


def skills_count(value) -> int:
    # Đếm số skill canonical
    if value is None:
        return 0

    if isinstance(value, float) and pd.isna(value):
        return 0

    if isinstance(value, list):
        return len(value)

    if isinstance(value, np.ndarray):
        return len(value.tolist())

    if isinstance(value, (tuple, set)):
        return len(list(value))

    if isinstance(value, str):
        text = value.strip()

        if text.lower() in ["", "[]", "nan", "none", "null"]:
            return 0

        return 1

    return 0


def build_final_clean_df(df: pd.DataFrame) -> pd.DataFrame:
    # Tạo bản copy để không làm thay đổi DataFrame gốc
    result_df = df.copy()

    # Clean location sâu
    location_result = result_df["location_basic_clean"].apply(
        clean_location
    )

    result_df["city_clean"] = location_result.apply(lambda value: value[0])
    result_df["country_clean"] = location_result.apply(lambda value: value[1])
    result_df["location_final"] = location_result.apply(lambda value: value[2])

    # Chuẩn hóa occupation group/family
    result_df["occupation_group_final"] = result_df[
        "occupation_group_preliminary"
    ].apply(clean_occupation_group)

    result_df["occupation_family_final"] = result_df[
        "occupation_group_final"
    ].apply(get_occupation_family)

    # Chuẩn hóa số lượng skill final
    result_df["skills_count_final"] = result_df["skills_canonical"].apply(
        skills_count
    )

    # Đánh dấu dòng đủ điều kiện cho Gold
    result_df["is_valid_for_gold"] = (
        result_df["job_title_canonical"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        & (result_df["skills_count_final"] > 0)
    )

    return result_df


def main() -> None:
    print("Bắt đầu build Silver 05 Final Clean cho Crawler")

    # Kết nối MinIO
    client = get_minio_client()

    # Tìm batch chưa final clean
    print("\nBước 1: Tìm batch crawler chưa final clean")
    batch_name = find_unprocessed_batch(client)

    if batch_name is None:
        print("\nKhông có batch crawler mới cần final clean.")
        print("Dừng bước 06.")
        return

    industry_clean_object = silver_crawler_industry_clean(batch_name)
    final_clean_object = silver_crawler_final_clean(batch_name)

    print(f"Batch cần xử lý: {batch_name}")
    print(f"Input Silver 04: s3://{MINIO_BUCKET}/{industry_clean_object}")
    print(f"Output Silver 05: s3://{MINIO_BUCKET}/{final_clean_object}")

    # Đọc Silver 04 Industry Clean
    print("\nBước 2: Đọc dữ liệu Silver 04 Industry Clean")
    industry_clean_df = read_parquet_from_minio(
        client=client,
        object_name=industry_clean_object,
    )

    # Final clean
    print("\nBước 3: Final clean occupation, location, skills count")
    final_clean_df = build_final_clean_df(industry_clean_df)

    # Kiểm tra kết quả
    print("\nThống kê occupation_group_final:")
    print(
        final_clean_df["occupation_group_final"]
        .value_counts()
    )

    print("\nThống kê country_clean:")
    print(
        final_clean_df["country_clean"]
        .value_counts()
        .head(20)
    )

    print("\nThống kê city_clean:")
    print(
        final_clean_df["city_clean"]
        .value_counts()
        .head(20)
    )

    print("\nSố dòng đủ điều kiện Gold:")
    print(final_clean_df["is_valid_for_gold"].sum())

    print("\nSample Final Clean:")
    print(
        final_clean_df[
            [
                "location_basic_clean",
                "city_clean",
                "country_clean",
                "location_final",
                "job_title_canonical",
                "occupation_group_final",
                "occupation_family_final",
                "seniority",
                "skills_canonical",
                "skills_count_final",
                "is_valid_for_gold",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print(f"\nSố dòng, số cột: {final_clean_df.shape}")

    # Lưu Silver 05 Final Clean
    print("\nBước 4: Lưu Silver 05 Final Clean lên MinIO")
    upload_df_parquet(
        client=client,
        df=final_clean_df,
        object_name=final_clean_object,
    )

    # Kiểm tra vùng Silver Crawler Final Clean
    print("\nBước 5: Kiểm tra vùng Silver Crawler Final Clean")
    list_objects(
        client=client,
        prefix=f"silver/crawler/{batch_name}/05_final_clean/",
    )

    print("\nHoàn thành build Silver 05 Final Clean cho Crawler.")


if __name__ == "__main__":
    main()