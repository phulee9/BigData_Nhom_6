import os
import sys
from io import BytesIO

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
    ensure_bucket_exists,
)


def create_folder(client, folder_path):
    # MinIO/S3 không có folder thật, nên tạo object dạng folder path
    client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=folder_path,
        data=BytesIO(b""),
        length=0,
        content_type="application/x-directory",
    )


def main():
    client = get_minio_client()
    ensure_bucket_exists(client)

    # 3 vùng chính: Bronze / Silver / Gold
    folders = [
        "bronze/",
        "silver/",
        "gold/",

        # Vùng Bronze lưu dữ liệu gốc theo từng nguồn
        "bronze/kaggle/",
        "bronze/crawler/",

        # Vùng Silver lưu dữ liệu đã xử lý trung gian
        "silver/kaggle/",
        "silver/crawler/",

        # Vùng Gold lưu dữ liệu sạch cuối cùng
        "gold/kaggle/",
        "gold/crawler/",

        # Vùng lưu FAISS index phục vụ recommendation
        "gold/kaggle/index/",
        "gold/crawler/index/",
    ]

    # Tạo từng folder trên MinIO
    for folder in folders:
        create_folder(client, folder)
        print(f"Created: {folder}")

    print("Done.")


if __name__ == "__main__":
    main()