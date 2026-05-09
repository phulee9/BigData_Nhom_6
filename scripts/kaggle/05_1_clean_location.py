import re
import sys
from pathlib import Path

import pandas as pd

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import SILVER_KAGGLE_INDUSTRY_CLEAN
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_df_parquet,
)


COUNTRY_ALIASES = {
    "us": "United States",
    "usa": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "united states": "United States",
    "united states of america": "United States",

    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united kingdom": "United Kingdom",
    "england": "United Kingdom",

    "canada": "Canada",
    "india": "India",
    "vietnam": "Vietnam",
    "viet nam": "Vietnam",
    "singapore": "Singapore",
    "australia": "Australia",
    "germany": "Germany",
    "france": "France",
    "netherlands": "Netherlands",
    "ireland": "Ireland",
    "philippines": "Philippines",
    "mexico": "Mexico",
    "brazil": "Brazil",
    "japan": "Japan",
    "china": "China",
    "malaysia": "Malaysia",
    "thailand": "Thailand",
    "indonesia": "Indonesia",
}


US_STATE_CODES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
    "dc",
}


US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
}


LOCATION_NOISE = [
    "remote",
    "hybrid",
    "onsite",
    "on-site",
    "on site",
    "work from home",
    "wfh",
    "home based",
    "anywhere",
]


def normalize_location(value) -> str:
    # Chuẩn hóa location về chữ thường và format dấu phẩy
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = text.replace("|", ",")
    text = text.replace(";", ",")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)

    return text.strip()


def remove_location_noise(location: str) -> str:
    # Xóa các từ như remote, hybrid để còn lại địa điểm
    text = location

    for noise in LOCATION_NOISE:
        text = text.replace(noise, " ")

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = text.strip(" ,-/")

    return text


def detect_country(parts: list[str]) -> str:
    # Tìm country từ cuối chuỗi location
    for part in reversed(parts):
        key = part.strip().lower().replace(".", "")

        if key in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[key]

        if key in US_STATE_CODES:
            return "United States"

        if key in US_STATE_NAMES:
            return "United States"

    return ""


def detect_city(parts: list[str]) -> str:
    # Lấy thành phố từ phần đầu tiên hợp lệ
    for part in parts:
        value = part.strip().lower().replace(".", "")

        if not value:
            continue

        if value in ["nan", "none", "null"]:
            continue

        if value in COUNTRY_ALIASES:
            continue

        if value in US_STATE_CODES:
            continue

        if value in US_STATE_NAMES:
            continue

        return part.strip().title()

    return ""


def build_location_final(city: str, country: str) -> str:
    # Tạo location cuối cùng để đưa vào Gold
    if city and country:
        return f"{city}, {country}"

    if city:
        return city

    if country:
        return country

    return "Unknown"


def clean_city_country(value) -> dict:
    # Tách city và country từ location
    location = normalize_location(value)
    location = remove_location_noise(location)

    parts = [
        part.strip()
        for part in location.split(",")
        if part.strip()
    ]

    city = detect_city(parts)
    country = detect_country(parts)
    location_final = build_location_final(city, country)

    return {
        "city_clean": city,
        "country_clean": country,
        "location_final": location_final,
    }


def main() -> None:
    print("Bắt đầu tách city_clean và country_clean")

    # Kết nối MinIO
    client = get_minio_client()

    # Đọc Silver 04 Industry Clean
    print("\nBước 1: Đọc Silver 04 Industry Clean")
    df = read_parquet_from_minio(
        client=client,
        object_name=SILVER_KAGGLE_INDUSTRY_CLEAN,
    )

    # Tách thành phố và quốc gia
    print("\nBước 2: Tách city_clean và country_clean")
    location_result = df["location_clean"].apply(clean_city_country)

    location_df = pd.DataFrame(
        location_result.tolist(),
        index=df.index,
    )

    # Xóa cột cũ nếu đã từng chạy trước đó
    for col in ["city_clean", "country_clean", "location_final"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Ghép cột location mới
    df = pd.concat(
        [df, location_df],
        axis=1,
    )

    # Kiểm tra nhanh kết quả
    print("\nSample location sau khi tách:")
    print(
        df[
            [
                "location_raw",
                "location_clean",
                "city_clean",
                "country_clean",
                "location_final",
            ]
        ]
        .sample(30, random_state=42)
        .to_string(index=False)
    )

    print("\nTop 30 city_clean:")
    print(
        df["city_clean"]
        .replace("", "Unknown")
        .value_counts()
        .head(30)
    )

    print("\nTop 30 country_clean:")
    print(
        df["country_clean"]
        .replace("", "Unknown")
        .value_counts()
        .head(30)
    )

    print(f"\nSố dòng, số cột: {df.shape}")

    # Ghi đè lại Silver 04 để bước sau dùng location mới
    print("\nBước 3: Lưu lại Silver 04 Industry Clean")
    upload_df_parquet(
        client=client,
        df=df,
        object_name=SILVER_KAGGLE_INDUSTRY_CLEAN,
    )

    print("\nHoàn thành tách city_clean và country_clean.")


if __name__ == "__main__":
    main()