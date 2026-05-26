import os
import sys

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
    ensure_bucket_exists,
)


def upload_file(client, local_file_path, object_name):
    # Upload file local lên MinIO
    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        file_path=local_file_path,
    )

    print(f"Uploaded: {local_file_path} -> {object_name}")


def main():
    client = get_minio_client()
    ensure_bucket_exists(client)

    # Thư mục local chứa dữ liệu Kaggle raw
    local_folder = "data/raw/kaggle"

    # Vùng Bronze trên MinIO
    bronze_prefix = "bronze/kaggle"

    # Danh sách file Kaggle raw cần upload
    files = [
        "linkedin_job_postings.csv",
        "job_skills.csv",
        "job_summary.csv",
    ]

    for file_name in files:
        local_file_path = os.path.join(local_folder, file_name)
        object_name = f"{bronze_prefix}/{file_name}"

        if not os.path.exists(local_file_path):
            print(f"File not found: {local_file_path}")
            continue

        upload_file(client, local_file_path, object_name)

    print("Done.")


if __name__ == "__main__":
    main()