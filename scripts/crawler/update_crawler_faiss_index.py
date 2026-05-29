import argparse
import os
import sys

import faiss
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from minio.error import S3Error
from sentence_transformers import SentenceTransformer

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)


load_dotenv(override=True)


GOLD_WEEKLY_TEMPLATE = "gold/crawler/weekly/{week}.parquet"

METADATA_PATH = "gold/crawler/metadata/jobs_metadata.parquet"

TITLE_INDEX_PATH = "gold/crawler/index/title_faiss.index"
SKILLS_INDEX_PATH = "gold/crawler/index/skills_faiss.index"

TITLE_WEEKLY_EMBEDDINGS_TEMPLATE = "gold/crawler/embeddings/weekly/{week}_title_embeddings.npy"
SKILLS_WEEKLY_EMBEDDINGS_TEMPLATE = "gold/crawler/embeddings/weekly/{week}_skills_embeddings.npy"

LOCAL_TEMP_DIR = "data/temp/crawler"

LOCAL_GOLD_WEEKLY_PATH = f"{LOCAL_TEMP_DIR}/jobs_for_encoding_weekly.parquet"
LOCAL_METADATA_PATH = f"{LOCAL_TEMP_DIR}/jobs_metadata.parquet"

LOCAL_TITLE_INDEX_PATH = f"{LOCAL_TEMP_DIR}/title_faiss.index"
LOCAL_SKILLS_INDEX_PATH = f"{LOCAL_TEMP_DIR}/skills_faiss.index"

LOCAL_TITLE_WEEKLY_EMBEDDINGS_PATH = f"{LOCAL_TEMP_DIR}/title_embeddings_weekly.npy"
LOCAL_SKILLS_WEEKLY_EMBEDDINGS_PATH = f"{LOCAL_TEMP_DIR}/skills_embeddings_weekly.npy"

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


def download_file_if_exists(client, object_path, local_path):
    # Download file nếu tồn tại trên MinIO
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        client.fget_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_path,
            file_path=local_path,
        )

        return True

    except S3Error as error:
        if error.code in {"NoSuchKey", "NoSuchBucket"}:
            return False

        raise error


def upload_file(client, local_path, object_path):
    # Upload file lên MinIO
    client.fput_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_path,
        file_path=local_path,
    )

    print(f"Uploaded: {object_path}")


def download_gold_week(client, week):
    # Tải Gold weekly
    object_path = GOLD_WEEKLY_TEMPLATE.format(week=week)

    exists = download_file_if_exists(
        client=client,
        object_path=object_path,
        local_path=LOCAL_GOLD_WEEKLY_PATH,
    )

    if not exists:
        raise FileNotFoundError(f"Gold weekly file not found: {object_path}")

    print(f"Downloaded: {object_path}")


def read_gold_week():
    # Đọc Gold weekly
    return pd.read_parquet(LOCAL_GOLD_WEEKLY_PATH)


def read_existing_metadata(client):
    # Đọc metadata cũ nếu có
    exists = download_file_if_exists(
        client=client,
        object_path=METADATA_PATH,
        local_path=LOCAL_METADATA_PATH,
    )

    if not exists:
        return pd.DataFrame()

    return pd.read_parquet(LOCAL_METADATA_PATH)


def load_or_create_index(client, object_path, local_path, dimension):
    # Load FAISS index cũ nếu có, nếu chưa có thì tạo mới
    exists = download_file_if_exists(
        client=client,
        object_path=object_path,
        local_path=local_path,
    )

    if exists:
        return faiss.read_index(local_path)

    if NORMALIZE_EMBEDDINGS:
        return faiss.IndexFlatIP(dimension)

    return faiss.IndexFlatL2(dimension)


def encode_texts(model, texts):
    # Encode text theo batch
    embeddings = model.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        convert_to_numpy=True,
        show_progress_bar=True,
    )

    return embeddings.astype("float32")


def save_embeddings(embeddings, local_path):
    # Lưu embeddings tuần mới
    np.save(local_path, embeddings)


def update_index(index, embeddings, local_index_path):
    # Add vector mới vào FAISS index
    index.add(embeddings)
    faiss.write_index(index, local_index_path)


def build_metadata_week(gold_week):
    # Tạo metadata cho job tuần mới
    metadata_columns = [
        "doc_id",
        "job_id",
        "link",
        "title_core",
        "skills_clean",
        "company",
        "location_raw",
        "city",
        "country",
        "source",
        "crawl_week",
    ]

    return gold_week[metadata_columns].copy()


def append_metadata(existing_metadata, metadata_week):
    # Append metadata tuần mới vào metadata tổng
    if existing_metadata.empty:
        metadata = metadata_week.copy()
    else:
        metadata = pd.concat(
            [
                existing_metadata,
                metadata_week,
            ],
            ignore_index=True,
        )

    metadata["link"] = (
        metadata["link"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    metadata = metadata.drop_duplicates(
        subset=["link"],
        keep="first",
    ).reset_index(drop=True)

    metadata = metadata.sort_values("doc_id").reset_index(drop=True)

    return metadata


def validate_doc_id(gold_week, existing_metadata, title_index, skills_index):
    # Kiểm tra doc_id có khớp với số vector hiện tại không
    if len(gold_week) == 0:
        return

    min_doc_id = int(gold_week["doc_id"].min())

    if existing_metadata.empty:
        expected_start = 0
    else:
        expected_start = len(existing_metadata)

    if min_doc_id != expected_start:
        print(f"Warning: min doc_id = {min_doc_id}, expected = {expected_start}")

    if title_index.ntotal != expected_start:
        print(f"Warning: title index ntotal = {title_index.ntotal}, expected = {expected_start}")

    if skills_index.ntotal != expected_start:
        print(f"Warning: skills index ntotal = {skills_index.ntotal}, expected = {expected_start}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--week",
        required=True,
        help="Tên tuần, ví dụ: week_2026_05_09",
    )

    args = parser.parse_args()

    client = get_minio_client()

    print("Downloading Gold weekly...")
    download_gold_week(client, args.week)

    print("Reading Gold weekly...")
    gold_week = read_gold_week()

    print(f"Gold weekly rows: {len(gold_week):,}")

    if len(gold_week) == 0:
        print("No new jobs to encode.")
        return

    print("Reading existing metadata...")
    existing_metadata = read_existing_metadata(client)

    print(f"Existing metadata rows: {len(existing_metadata):,}")

    print("Loading embedding model...")
    print(f"Model: {EMBEDDING_MODEL}")
    print(f"Batch size: {EMBEDDING_BATCH_SIZE}")
    print(f"Normalize embeddings: {NORMALIZE_EMBEDDINGS}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    print("Encoding title_text...")
    title_embeddings = encode_texts(
        model=model,
        texts=gold_week["title_text"].astype(str).tolist(),
    )

    print("Encoding skills_text...")
    skills_embeddings = encode_texts(
        model=model,
        texts=gold_week["skills_text"].astype(str).tolist(),
    )

    dimension = title_embeddings.shape[1]

    print(f"Embedding dimension: {dimension}")

    print("Loading or creating FAISS indexes...")
    title_index = load_or_create_index(
        client=client,
        object_path=TITLE_INDEX_PATH,
        local_path=LOCAL_TITLE_INDEX_PATH,
        dimension=dimension,
    )

    skills_index = load_or_create_index(
        client=client,
        object_path=SKILLS_INDEX_PATH,
        local_path=LOCAL_SKILLS_INDEX_PATH,
        dimension=dimension,
    )

    validate_doc_id(
        gold_week=gold_week,
        existing_metadata=existing_metadata,
        title_index=title_index,
        skills_index=skills_index,
    )

    print("Saving weekly embeddings...")
    save_embeddings(
        embeddings=title_embeddings,
        local_path=LOCAL_TITLE_WEEKLY_EMBEDDINGS_PATH,
    )

    save_embeddings(
        embeddings=skills_embeddings,
        local_path=LOCAL_SKILLS_WEEKLY_EMBEDDINGS_PATH,
    )

    print("Updating FAISS indexes...")
    update_index(
        index=title_index,
        embeddings=title_embeddings,
        local_index_path=LOCAL_TITLE_INDEX_PATH,
    )

    update_index(
        index=skills_index,
        embeddings=skills_embeddings,
        local_index_path=LOCAL_SKILLS_INDEX_PATH,
    )

    print("Updating metadata...")
    metadata_week = build_metadata_week(gold_week)

    metadata = append_metadata(
        existing_metadata=existing_metadata,
        metadata_week=metadata_week,
    )

    metadata.to_parquet(
        LOCAL_METADATA_PATH,
        index=False,
    )

    print(f"Title index total vectors: {title_index.ntotal:,}")
    print(f"Skills index total vectors: {skills_index.ntotal:,}")
    print(f"Metadata rows: {len(metadata):,}")

    print("Uploading outputs...")

    upload_file(
        client=client,
        local_path=LOCAL_METADATA_PATH,
        object_path=METADATA_PATH,
    )

    upload_file(
        client=client,
        local_path=LOCAL_TITLE_INDEX_PATH,
        object_path=TITLE_INDEX_PATH,
    )

    upload_file(
        client=client,
        local_path=LOCAL_SKILLS_INDEX_PATH,
        object_path=SKILLS_INDEX_PATH,
    )

    upload_file(
        client=client,
        local_path=LOCAL_TITLE_WEEKLY_EMBEDDINGS_PATH,
        object_path=TITLE_WEEKLY_EMBEDDINGS_TEMPLATE.format(week=args.week),
    )

    upload_file(
        client=client,
        local_path=LOCAL_SKILLS_WEEKLY_EMBEDDINGS_PATH,
        object_path=SKILLS_WEEKLY_EMBEDDINGS_TEMPLATE.format(week=args.week),
    )

    print("Done.")


if __name__ == "__main__":
    main()