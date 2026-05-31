import os
import sys
from pathlib import Path

sys.path.append(os.getcwd())

from src.storage.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)


CRAWLER_OBJECTS = {
    "gold/crawler/metadata/jobs_metadata.parquet":
        "data/downloads/crawler/gold/metadata/jobs_metadata.parquet",

    "gold/crawler/index/title_faiss.index":
        "data/downloads/crawler/gold/index/title_faiss.index",

    "gold/crawler/index/skills_faiss.index":
        "data/downloads/crawler/gold/index/skills_faiss.index",
}


def download_file(client, object_name, local_path):
    # Tạo folder local nếu chưa có
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Tải file từ MinIO về local
    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        file_path=str(local_path),
    )

    print(f"Downloaded: {object_name}")
    print(f"Local: {local_path}")


def main():
    client = get_minio_client()

    for object_name, local_path in CRAWLER_OBJECTS.items():
        download_file(
            client=client,
            object_name=object_name,
            local_path=local_path,
        )

    print("Done.")


if __name__ == "__main__":
    main()