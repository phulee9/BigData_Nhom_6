import argparse
import gc
import sys
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    NORMALIZE_EMBEDDINGS,
    GOLD_KAGGLE_JOBS_FOR_ENCODING,
    GOLD_KAGGLE_METADATA,
    GOLD_KAGGLE_TITLE_EMBEDDINGS,
    GOLD_KAGGLE_SKILLS_EMBEDDINGS,
    GOLD_KAGGLE_FULL_EMBEDDINGS,
    GOLD_KAGGLE_TITLE_INDEX,
    GOLD_KAGGLE_SKILLS_INDEX,
    GOLD_KAGGLE_FULL_INDEX,
)
from src.storage.minio_client import (
    get_minio_client,
    upload_file,
    upload_df_parquet_local_temp,
    list_objects,
)


LOCAL_TEMP_DIR = Path("data/temp")
LOCAL_GOLD_FILE = LOCAL_TEMP_DIR / "jobs_for_encoding.parquet"

LOCAL_TITLE_EMBEDDINGS = LOCAL_TEMP_DIR / "title_embeddings.npy"
LOCAL_SKILLS_EMBEDDINGS = LOCAL_TEMP_DIR / "skills_embeddings.npy"
LOCAL_FULL_EMBEDDINGS = LOCAL_TEMP_DIR / "full_embeddings.npy"

LOCAL_TITLE_INDEX = LOCAL_TEMP_DIR / "title.faiss.index"
LOCAL_SKILLS_INDEX = LOCAL_TEMP_DIR / "skills.faiss.index"
LOCAL_FULL_INDEX = LOCAL_TEMP_DIR / "full.faiss.index"


def parse_args():
    # Nhận tham số index từ command line
    parser = argparse.ArgumentParser(
        description="Build FAISS index cho Kaggle"
    )

    parser.add_argument(
        "--index",
        choices=["title", "skills", "full", "all"],
        default="all",
        help="Chọn index cần build: title, skills, full hoặc all",
    )

    parser.add_argument(
        "--keep-local-index",
        action="store_true",
        help="Giữ lại file FAISS index local sau khi upload lên MinIO",
    )

    return parser.parse_args()


def download_gold_from_minio(client) -> None:
    # Tạo folder temp nếu chưa có
    LOCAL_TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Download Gold parquet từ MinIO về local temp
    print("\nBước 1: Download jobs_for_encoding.parquet từ MinIO")
    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=GOLD_KAGGLE_JOBS_FOR_ENCODING,
        file_path=str(LOCAL_GOLD_FILE),
    )

    print(f"Đã download về: {LOCAL_GOLD_FILE}")


def load_gold_for_indexing() -> pd.DataFrame:
    # Chỉ đọc các cột cần cho metadata và encode để giảm RAM
    columns = [
        "source",
        "source_job_id",
        "job_link",
        "job_url",
        "company",
        "job_title_canonical",
        "occupation_group_final",
        "occupation_family_final",
        "seniority",
        "city_clean",
        "country_clean",
        "location_final",
        "skills_canonical",
        "skills_count_final",
        "title_text",
        "skills_text",
        "full_text",
    ]

    print("\nBước 2: Đọc Gold parquet từ local temp")
    df = pd.read_parquet(
        LOCAL_GOLD_FILE,
        columns=columns,
    )

    print(f"Số dòng, số cột: {df.shape}")

    return df


def save_metadata(client, df: pd.DataFrame) -> None:
    # Metadata dùng để trả kết quả sau khi FAISS tìm được index dòng
    metadata_cols = [
        "source",
        "source_job_id",
        "job_link",
        "job_url",
        "company",
        "job_title_canonical",
        "occupation_group_final",
        "occupation_family_final",
        "seniority",
        "city_clean",
        "country_clean",
        "location_final",
        "skills_canonical",
        "skills_count_final",
    ]

    metadata_df = df[metadata_cols].copy()

    print("\nBước 3: Lưu metadata.parquet lên MinIO")
    upload_df_parquet_local_temp(
        client=client,
        df=metadata_df,
        object_name=GOLD_KAGGLE_METADATA,
        local_temp_path=str(LOCAL_TEMP_DIR / "metadata.parquet"),
    )


def encode_text_column_to_npy(
    model: SentenceTransformer,
    texts: pd.Series,
    local_embedding_path: Path,
) -> None:
    # Encode text theo batch và ghi trực tiếp vào file .npy dạng memmap để tiết kiệm RAM
    total_rows = len(texts)

    print(f"\nTổng số dòng cần encode: {total_rows}")
    print(f"Batch size: {EMBEDDING_BATCH_SIZE}")

    # Encode thử 1 dòng để lấy số chiều embedding
    sample_embedding = model.encode(
        ["test"],
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    embedding_dim = sample_embedding.shape[1]

    print(f"Embedding dimension: {embedding_dim}")
    print(f"File embedding local: {local_embedding_path}")

    # Tạo file .npy dạng memmap
    embeddings = np.lib.format.open_memmap(
        local_embedding_path,
        mode="w+",
        dtype="float32",
        shape=(total_rows, embedding_dim),
    )

    # Encode từng batch
    for start_idx in range(0, total_rows, EMBEDDING_BATCH_SIZE):
        end_idx = min(
            start_idx + EMBEDDING_BATCH_SIZE,
            total_rows,
        )

        batch_texts = (
            texts.iloc[start_idx:end_idx]
            .fillna("")
            .astype(str)
            .tolist()
        )

        batch_embeddings = model.encode(
            batch_texts,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype("float32")

        embeddings[start_idx:end_idx] = batch_embeddings

        if start_idx % (EMBEDDING_BATCH_SIZE * 100) == 0:
            print(f"Đã encode: {end_idx}/{total_rows}")

    # Flush dữ liệu xuống disk
    embeddings.flush()

    del embeddings
    gc.collect()

    print(f"Hoàn thành encode: {local_embedding_path}")


def build_faiss_index_from_npy(
    local_embedding_path: Path,
    local_index_path: Path,
) -> None:
    # Đọc embedding bằng mmap để không load toàn bộ vào RAM ngay từ đầu
    embeddings = np.load(
        local_embedding_path,
        mmap_mode="r",
    )

    total_rows, embedding_dim = embeddings.shape

    print("\nBắt đầu build FAISS index")
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Index path: {local_index_path}")

    # Vì embeddings đã normalize nên dùng Inner Product tương đương cosine similarity
    index = faiss.IndexFlatIP(embedding_dim)

    batch_size = 50000

    for start_idx in range(0, total_rows, batch_size):
        end_idx = min(
            start_idx + batch_size,
            total_rows,
        )

        batch = np.asarray(
            embeddings[start_idx:end_idx],
            dtype="float32",
        )

        index.add(batch)

        print(f"Đã add vào index: {end_idx}/{total_rows}")

    faiss.write_index(
        index,
        str(local_index_path),
    )

    print(f"Đã lưu FAISS index local: {local_index_path}")

    del index
    del embeddings
    gc.collect()


def upload_artifact(
    client,
    local_path: Path,
    object_name: str,
) -> None:
    # Upload file local lên MinIO
    upload_file(
        client=client,
        local_path=str(local_path),
        object_name=object_name,
    )


def process_one_index(
    client,
    model: SentenceTransformer,
    df: pd.DataFrame,
    text_column: str,
    local_embedding_path: Path,
    minio_embedding_path: str,
    local_index_path: Path,
    minio_index_path: str,
    keep_local_index: bool = False,
) -> None:
    print("\n" + "=" * 80)
    print(f"Xử lý index cho cột: {text_column}")
    print("=" * 80)

    # Encode cột text thành file embeddings.npy
    encode_text_column_to_npy(
        model=model,
        texts=df[text_column],
        local_embedding_path=local_embedding_path,
    )

    # Build FAISS index từ embeddings.npy
    build_faiss_index_from_npy(
        local_embedding_path=local_embedding_path,
        local_index_path=local_index_path,
    )

    # Upload embeddings lên MinIO
    print("\nUpload embeddings lên MinIO")
    upload_artifact(
        client=client,
        local_path=local_embedding_path,
        object_name=minio_embedding_path,
    )

    # Upload FAISS index lên MinIO
    print("\nUpload FAISS index lên MinIO")
    upload_artifact(
        client=client,
        local_path=local_index_path,
        object_name=minio_index_path,
    )

    # Xóa embedding local để tiết kiệm dung lượng
    local_embedding_path.unlink(missing_ok=True)

    # Có thể giữ lại index local nếu muốn dùng runtime
    if keep_local_index:
        print(f"Giữ lại FAISS index local: {local_index_path}")
    else:
        local_index_path.unlink(missing_ok=True)
        print(f"Đã xóa FAISS index local: {local_index_path}")

    gc.collect()


def main() -> None:
    args = parse_args()
    selected_index = args.index

    print("Bắt đầu build FAISS index cho Kaggle")
    print(f"Index được chọn: {selected_index}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Normalize embeddings: {NORMALIZE_EMBEDDINGS}")

    # Kết nối MinIO
    client = get_minio_client()

    # Download Gold parquet về local
    download_gold_from_minio(client)

    # Đọc Gold
    df = load_gold_for_indexing()

    # Metadata chỉ cần tạo một lần
    # Nếu chạy title hoặc all thì tạo metadata
    if selected_index in ["title", "all"]:
        save_metadata(
            client=client,
            df=df,
        )

    # Load model embedding
    print("\nBước 4: Load embedding model")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Build title index nếu được chọn
    if selected_index in ["title", "all"]:
        process_one_index(
            client=client,
            model=model,
            df=df,
            text_column="title_text",
            local_embedding_path=LOCAL_TITLE_EMBEDDINGS,
            minio_embedding_path=GOLD_KAGGLE_TITLE_EMBEDDINGS,
            local_index_path=LOCAL_TITLE_INDEX,
            minio_index_path=GOLD_KAGGLE_TITLE_INDEX,
            keep_local_index=args.keep_local_index,
        )

    # Build skills index nếu được chọn
    if selected_index in ["skills", "all"]:
        process_one_index(
            client=client,
            model=model,
            df=df,
            text_column="skills_text",
            local_embedding_path=LOCAL_SKILLS_EMBEDDINGS,
            minio_embedding_path=GOLD_KAGGLE_SKILLS_EMBEDDINGS,
            local_index_path=LOCAL_SKILLS_INDEX,
            minio_index_path=GOLD_KAGGLE_SKILLS_INDEX,
            keep_local_index=args.keep_local_index,
        )

    # Build full index nếu được chọn
    if selected_index in ["full", "all"]:
        process_one_index(
            client=client,
            model=model,
            df=df,
            text_column="full_text",
            local_embedding_path=LOCAL_FULL_EMBEDDINGS,
            minio_embedding_path=GOLD_KAGGLE_FULL_EMBEDDINGS,
            local_index_path=LOCAL_FULL_INDEX,
            minio_index_path=GOLD_KAGGLE_FULL_INDEX,
            keep_local_index=args.keep_local_index,
        )

    # Xóa Gold parquet local sau khi build xong
    LOCAL_GOLD_FILE.unlink(missing_ok=True)

    # Giải phóng RAM
    del df
    del model
    gc.collect()

    # Kiểm tra vùng Gold
    print("\nBước cuối: Kiểm tra Gold Kaggle Encode")
    list_objects(
        client=client,
        prefix="gold/kaggle/encode/",
    )

    print("\nHoàn thành build FAISS index cho Kaggle.")


if __name__ == "__main__":
    main()