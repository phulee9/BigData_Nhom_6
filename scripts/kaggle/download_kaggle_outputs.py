import os
import sys

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)


DOWNLOAD_FILES = {
    "silver/kaggle/jobs_silver.parquet": "data/downloads/kaggle/silver/jobs_silver.parquet",

    "gold/kaggle/jobs_for_encoding.parquet": "data/downloads/kaggle/gold/jobs_for_encoding.parquet",

    "gold/kaggle/metadata/jobs_metadata.parquet": "data/downloads/kaggle/gold/metadata/jobs_metadata.parquet",

    "gold/kaggle/embeddings/title_embeddings.npy": "data/downloads/kaggle/gold/embeddings/title_embeddings.npy",
    "gold/kaggle/embeddings/skills_embeddings.npy": "data/downloads/kaggle/gold/embeddings/skills_embeddings.npy",

    "gold/kaggle/index/title_faiss.index": "data/downloads/kaggle/gold/index/title_faiss.index",
    "gold/kaggle/index/skills_faiss.index": "data/downloads/kaggle/gold/index/skills_faiss.index",
}


def download_file(client, object_path, local_path):
    # Tải file từ MinIO về local
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_path,
        file_path=local_path,
    )

    print(f"Downloaded: {object_path}")
    print(f"Local: {local_path}")


def main():
    client = get_minio_client()

    for object_path, local_path in DOWNLOAD_FILES.items():
        download_file(
            client=client,
            object_path=object_path,
            local_path=local_path,
        )

    print("Done.")


if __name__ == "__main__":
    main()