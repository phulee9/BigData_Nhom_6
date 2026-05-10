import sys
from pathlib import Path

from minio.error import S3Error

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    LOCAL_CRAWLER_RAW_DIR,
    get_batch_name_from_file,
    bronze_crawler_raw,
)
from src.storage.minio_client import (
    get_minio_client,
    ensure_bucket,
    create_zones,
    upload_file,
    list_objects,
)


CRAWLER_ZONES = [
    "bronze/crawler/raw/",
    "silver/crawler/",
    "gold/crawler/batches/",
    "gold/crawler/encode/",
    "audit/crawler/",
]


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


def get_local_json_files() -> list[Path]:
    # Lấy danh sách file json local, sắp xếp mới nhất trước
    json_files = sorted(
        LOCAL_CRAWLER_RAW_DIR.glob("*.json"),
        key=lambda file_path: file_path.stat().st_mtime,
        reverse=True,
    )

    return json_files


def find_new_crawler_file(client) -> tuple[Path, str, str] | None:
    # Tìm file crawler local chưa từng upload lên MinIO
    json_files = get_local_json_files()

    if not json_files:
        raise FileNotFoundError(
            f"Không tìm thấy file .json trong {LOCAL_CRAWLER_RAW_DIR}"
        )

    for file_path in json_files:
        batch_name = get_batch_name_from_file(file_path)
        bronze_object_name = bronze_crawler_raw(batch_name)

        if object_exists(client, bronze_object_name):
            print(f"Bỏ qua file cũ đã có trên MinIO: {file_path}")
            continue

        return file_path, batch_name, bronze_object_name

    return None


def main() -> None:
    print("Bắt đầu upload crawler raw mới lên MinIO")

    # Kết nối MinIO
    client = get_minio_client()

    # Tạo bucket nếu chưa có
    print("\nBước 1: Kiểm tra bucket")
    ensure_bucket(client)

    # Chỉ tạo các vùng cần cho crawler
    print("\nBước 2: Tạo các vùng crawler trên MinIO")
    create_zones(
        client=client,
        zones=CRAWLER_ZONES,
    )

    # Tìm file crawler mới chưa upload
    print("\nBước 3: Tìm file crawler mới")
    result = find_new_crawler_file(client)

    if result is None:
        print("\nKhông tìm thấy file crawler mới cần upload.")
        print("Tất cả file local trong data/raw/crawler đã tồn tại trên MinIO.")
        print("Dừng bước upload.")
        return

    latest_file, batch_name, bronze_object_name = result

    print(f"File crawler mới: {latest_file}")
    print(f"Batch name: {batch_name}")
    print(f"Đường dẫn MinIO: s3://{MINIO_BUCKET}/{bronze_object_name}")

    # Upload raw crawler lên Bronze
    print("\nBước 4: Upload crawler raw")
    upload_file(
        client=client,
        local_path=str(latest_file),
        object_name=bronze_object_name,
    )

    # Kiểm tra vùng Bronze Crawler
    print("\nBước 5: Kiểm tra bronze/crawler/raw/")
    list_objects(
        client=client,
        prefix="bronze/crawler/raw/",
    )

    print("\nHoàn thành upload crawler raw mới lên Bronze.")


if __name__ == "__main__":
    main()