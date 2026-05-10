import sys
from pathlib import Path

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    MINIO_ZONES,
    LOCAL_KAGGLE_JOB_POSTINGS,
    LOCAL_KAGGLE_JOB_SKILLS,
    BRONZE_KAGGLE_JOB_POSTINGS,
    BRONZE_KAGGLE_JOB_SKILLS,
)
from src.storage.minio_client import (
    get_minio_client,
    ensure_bucket,
    create_zones,
    upload_file,
    list_objects,
)


def main() -> None:
    # Chạy bước upload dữ liệu thô Kaggle lên vùng Bronze
    print("Bắt đầu upload dữ liệu Kaggle raw lên Bronze")
    print(f"Bucket đích: {MINIO_BUCKET}")

    # Kết nối MinIO
    client = get_minio_client()

    # Tạo bucket nếu chưa có
    print("\nBước 1: Kiểm tra bucket")
    ensure_bucket(client)

    # Tạo các vùng logic trên MinIO
    print("\nBước 2: Tạo các vùng trên MinIO")
    create_zones(
        client=client,
        zones=MINIO_ZONES,
    )

    # Upload file linkedin_job_postings.csv lên Bronze
    print("\nBước 3: Upload file linkedin_job_postings.csv")
    upload_file(
        client=client,
        local_path=LOCAL_KAGGLE_JOB_POSTINGS,
        object_name=BRONZE_KAGGLE_JOB_POSTINGS,
    )

    # Upload file job_skills.csv lên Bronze
    print("\nBước 4: Upload file job_skills.csv")
    upload_file(
        client=client,
        local_path=LOCAL_KAGGLE_JOB_SKILLS,
        object_name=BRONZE_KAGGLE_JOB_SKILLS,
    )

    # Kiểm tra lại dữ liệu đã upload trong bronze/kaggle/raw/
    print("\nBước 5: Kiểm tra dữ liệu đã upload")
    list_objects(
        client=client,
        prefix="bronze/kaggle/raw/",
    )

    print("\nHoàn thành upload dữ liệu raw lên Bronze.")


# Chỉ chạy main() khi file này được chạy trực tiếp
if __name__ == "__main__":
    main()