import os
import sys

import faiss
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)


load_dotenv(override=True)


GOLD_INPUT_PATH = "gold/kaggle/jobs_for_encoding.parquet"

METADATA_OUTPUT_PATH = "gold/kaggle/metadata/jobs_metadata.parquet"

TITLE_EMBEDDINGS_OUTPUT_PATH = "gold/kaggle/embeddings/title_embeddings.npy"
SKILLS_EMBEDDINGS_OUTPUT_PATH = "gold/kaggle/embeddings/skills_embeddings.npy"

TITLE_INDEX_OUTPUT_PATH = "gold/kaggle/index/title_faiss.index"
SKILLS_INDEX_OUTPUT_PATH = "gold/kaggle/index/skills_faiss.index"

LOCAL_TEMP_DIR = "data/temp"
LOCAL_GOLD_PATH = f"{LOCAL_TEMP_DIR}/jobs_for_encoding.parquet"

LOCAL_METADATA_PATH = f"{LOCAL_TEMP_DIR}/jobs_metadata.parquet"

LOCAL_TITLE_EMBEDDINGS_PATH = f"{LOCAL_TEMP_DIR}/title_embeddings.npy"
LOCAL_SKILLS_EMBEDDINGS_PATH = f"{LOCAL_TEMP_DIR}/skills_embeddings.npy"

LOCAL_TITLE_INDEX_PATH = f"{LOCAL_TEMP_DIR}/title_faiss.index"
LOCAL_SKILLS_INDEX_PATH = f"{LOCAL_TEMP_DIR}/skills_faiss.index"

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

EMBEDDING_BATCH_SIZE = int(
    os.getenv("EMBEDDING_BATCH_SIZE", "128")
)

NORMALIZE_EMBEDDINGS = (
    os.getenv("NORMALIZE_EMBEDDINGS", "true").lower() == "true"
)


def download_gold_file(client):
    # Tải file Gold từ MinIO
    os.makedirs(LOCAL_TEMP_DIR, exist_ok=True)

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=GOLD_INPUT_PATH,
        file_path=LOCAL_GOLD_PATH,
    )


def read_gold_file():
    # Đọc dữ liệu encode
    return pd.read_parquet(LOCAL_GOLD_PATH)


def save_metadata(jobs):
    # Lưu metadata dùng chung cho title và skills index
    metadata_columns = [
        "doc_id",
        "job_id",
        "job_link",
        "title_core",
        "skills_normalized",
    ]

    metadata = jobs[metadata_columns].copy()

    metadata.to_parquet(
        LOCAL_METADATA_PATH,
        index=False,
    )


def create_faiss_index(dimension):
    # Tạo FAISS index
    if NORMALIZE_EMBEDDINGS:
        return faiss.IndexFlatIP(dimension)

    return faiss.IndexFlatL2(dimension)


def encode_and_build_index(
    model,
    texts,
    embeddings_path,
    index_path,
):
    # Encode text và build FAISS index
    total_rows = len(texts)

    sample_embedding = model.encode(
        ["sample text"],
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        convert_to_numpy=True,
    ).astype("float32")

    dimension = sample_embedding.shape[1]

    embeddings = np.lib.format.open_memmap(
        embeddings_path,
        mode="w+",
        dtype="float32",
        shape=(total_rows, dimension),
    )

    index = create_faiss_index(dimension)

    for start in range(0, total_rows, EMBEDDING_BATCH_SIZE):
        end = min(start + EMBEDDING_BATCH_SIZE, total_rows)

        batch_texts = texts[start:end]

        batch_embeddings = model.encode(
            batch_texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype("float32")

        embeddings[start:end] = batch_embeddings
        index.add(batch_embeddings)

        print(f"Encoded rows: {end:,}/{total_rows:,}")

    embeddings.flush()

    faiss.write_index(index, index_path)


def upload_file(client, local_path, object_path):
    # Upload file lên MinIO
    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_path,
        file_path=local_path,
    )


def main():
    client = get_minio_client()

    print("Downloading Gold encoding file...")
    download_gold_file(client)

    print("Reading Gold encoding file...")
    jobs = read_gold_file()

    print(f"Encoding rows: {len(jobs):,}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Batch size: {EMBEDDING_BATCH_SIZE}")
    print(f"Normalize embeddings: {NORMALIZE_EMBEDDINGS}")

    print("Saving metadata...")
    save_metadata(jobs)

    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    print("Encoding title_text...")
    encode_and_build_index(
        model=model,
        texts=jobs["title_text"].astype(str).tolist(),
        embeddings_path=LOCAL_TITLE_EMBEDDINGS_PATH,
        index_path=LOCAL_TITLE_INDEX_PATH,
    )

    print("Encoding skills_text...")
    encode_and_build_index(
        model=model,
        texts=jobs["skills_text"].astype(str).tolist(),
        embeddings_path=LOCAL_SKILLS_EMBEDDINGS_PATH,
        index_path=LOCAL_SKILLS_INDEX_PATH,
    )

    print("Uploading metadata...")
    upload_file(
        client,
        LOCAL_METADATA_PATH,
        METADATA_OUTPUT_PATH,
    )

    print("Uploading title embeddings and index...")
    upload_file(
        client,
        LOCAL_TITLE_EMBEDDINGS_PATH,
        TITLE_EMBEDDINGS_OUTPUT_PATH,
    )
    upload_file(
        client,
        LOCAL_TITLE_INDEX_PATH,
        TITLE_INDEX_OUTPUT_PATH,
    )

    print("Uploading skills embeddings and index...")
    upload_file(
        client,
        LOCAL_SKILLS_EMBEDDINGS_PATH,
        SKILLS_EMBEDDINGS_OUTPUT_PATH,
    )
    upload_file(
        client,
        LOCAL_SKILLS_INDEX_PATH,
        SKILLS_INDEX_OUTPUT_PATH,
    )

    print(f"Uploaded: {METADATA_OUTPUT_PATH}")
    print(f"Uploaded: {TITLE_EMBEDDINGS_OUTPUT_PATH}")
    print(f"Uploaded: {SKILLS_EMBEDDINGS_OUTPUT_PATH}")
    print(f"Uploaded: {TITLE_INDEX_OUTPUT_PATH}")
    print(f"Uploaded: {SKILLS_INDEX_OUTPUT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()