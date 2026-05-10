import gc
import sys
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from minio.error import S3Error
from sentence_transformers import SentenceTransformer

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import (
    MINIO_BUCKET,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    NORMALIZE_EMBEDDINGS,
    GOLD_CRAWLER_METADATA,
    GOLD_CRAWLER_TITLE_INDEX,
    GOLD_CRAWLER_SKILLS_INDEX,
    GOLD_CRAWLER_FULL_INDEX,
)
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
    upload_file,
)


LOCAL_TEMP_DIR = Path("data/temp/crawler_append")

LOCAL_METADATA = LOCAL_TEMP_DIR / "metadata.parquet"

LOCAL_TITLE_INDEX = LOCAL_TEMP_DIR / "title.faiss.index"
LOCAL_SKILLS_INDEX = LOCAL_TEMP_DIR / "skills.faiss.index"
LOCAL_FULL_INDEX = LOCAL_TEMP_DIR / "full.faiss.index"


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


def list_gold_batches(client) -> list[str]:
    # Lấy danh sách batch đã có Gold Encode
    objects = client.list_objects(
        bucket_name=MINIO_BUCKET,
        prefix="gold/crawler/batches/",
        recursive=True,
    )

    batch_names = set()

    for obj in objects:
        object_name = obj.object_name

        if not object_name.endswith("/jobs_for_encoding.parquet"):
            continue

        # gold/crawler/batches/week_2026_05_09/jobs_for_encoding.parquet
        parts = object_name.split("/")

        if len(parts) >= 4:
            batch_names.add(parts[3])

    return sorted(batch_names)


def gold_batch_object(batch_name: str) -> str:
    # Đường dẫn Gold batch trên MinIO
    return f"gold/crawler/batches/{batch_name}/jobs_for_encoding.parquet"


def download_object(client, object_name: str, local_path: Path) -> None:
    # Download object từ MinIO về local
    local_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        file_path=str(local_path),
    )


def load_existing_metadata(client) -> pd.DataFrame:
    # Đọc metadata crawler chính nếu đã tồn tại
    if not object_exists(client, GOLD_CRAWLER_METADATA):
        return pd.DataFrame()

    return read_parquet_from_minio(
        client=client,
        object_name=GOLD_CRAWLER_METADATA,
    )


def find_unappended_batch(
    client,
    metadata_df: pd.DataFrame,
) -> str | None:
    # Tìm batch Gold chưa được append vào metadata/index chính
    gold_batches = list_gold_batches(client)

    if not gold_batches:
        print("Không tìm thấy Gold batch nào trong gold/crawler/batches/")
        return None

    if metadata_df.empty or "crawl_batch" not in metadata_df.columns:
        return gold_batches[0]

    appended_batches = set(
        metadata_df["crawl_batch"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    for batch_name in gold_batches:
        if batch_name in appended_batches:
            print(f"Bỏ qua batch đã append index: {batch_name}")
            continue

        return batch_name

    return None


def encode_texts(
    model: SentenceTransformer,
    texts: pd.Series,
) -> np.ndarray:
    # Encode text theo batch và trả về numpy array
    all_embeddings = []

    total_rows = len(texts)

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

        all_embeddings.append(batch_embeddings)

        print(f"Đã encode: {end_idx}/{total_rows}")

    return np.vstack(all_embeddings).astype("float32")


def load_or_create_index(
    client,
    minio_index_path: str,
    local_index_path: Path,
    embedding_dim: int,
) -> faiss.Index:
    # Nếu index đã tồn tại thì download và đọc
    if object_exists(client, minio_index_path):
        print(f"Download index cũ: {minio_index_path}")

        download_object(
            client=client,
            object_name=minio_index_path,
            local_path=local_index_path,
        )

        index = faiss.read_index(
            str(local_index_path)
        )

        return index

    # Nếu chưa có thì tạo index mới
    print(f"Chưa có index cũ, tạo index mới: {minio_index_path}")

    return faiss.IndexFlatIP(embedding_dim)


def append_to_index(
    client,
    embeddings: np.ndarray,
    minio_index_path: str,
    local_index_path: Path,
) -> faiss.Index:
    # Load index cũ hoặc tạo mới
    embedding_dim = embeddings.shape[1]

    index = load_or_create_index(
        client=client,
        minio_index_path=minio_index_path,
        local_index_path=local_index_path,
        embedding_dim=embedding_dim,
    )

    print(f"Số vector trước append: {index.ntotal}")

    # Append vector mới vào cuối index
    index.add(embeddings)

    print(f"Số vector sau append: {index.ntotal}")

    # Lưu index local
    faiss.write_index(
        index,
        str(local_index_path),
    )

    # Upload index mới lên MinIO
    upload_file(
        client=client,
        local_path=str(local_index_path),
        object_name=minio_index_path,
    )

    return index


def build_metadata_from_gold(gold_df: pd.DataFrame) -> pd.DataFrame:
    # Metadata dùng để tra ngược kết quả FAISS về thông tin job
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
        "crawl_batch",
    ]

    existing_cols = [
        col for col in metadata_cols
        if col in gold_df.columns
    ]

    metadata_df = gold_df[existing_cols].copy()

    for col in metadata_cols:
        if col not in metadata_df.columns:
            metadata_df[col] = ""

    return metadata_df[metadata_cols].copy()


def append_metadata(
    client,
    old_metadata_df: pd.DataFrame,
    new_metadata_df: pd.DataFrame,
) -> pd.DataFrame:
    # Append metadata mới vào cuối metadata cũ
    if old_metadata_df.empty:
        final_metadata_df = new_metadata_df.copy()
    else:
        final_metadata_df = pd.concat(
            [old_metadata_df, new_metadata_df],
            ignore_index=True,
        )

    # Lưu metadata local
    LOCAL_METADATA.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    final_metadata_df.to_parquet(
        LOCAL_METADATA,
        index=False,
        engine="pyarrow",
    )

    # Upload metadata lên MinIO
    upload_file(
        client=client,
        local_path=str(LOCAL_METADATA),
        object_name=GOLD_CRAWLER_METADATA,
    )

    return final_metadata_df


def main() -> None:
    print("Bắt đầu append Gold Crawler batch vào crawler indexes")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    print(f"Batch size: {EMBEDDING_BATCH_SIZE}")
    print(f"Normalize embeddings: {NORMALIZE_EMBEDDINGS}")

    LOCAL_TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Kết nối MinIO
    client = get_minio_client()

    # Đọc metadata cũ nếu có
    print("\nBước 1: Đọc metadata crawler hiện tại")
    old_metadata_df = load_existing_metadata(client)

    if old_metadata_df.empty:
        print("Chưa có metadata crawler cũ. Đây có thể là batch crawler đầu tiên.")
    else:
        print(f"Số dòng metadata hiện tại: {len(old_metadata_df)}")

    # Tìm Gold batch chưa append
    print("\nBước 2: Tìm Gold batch chưa append index")
    batch_name = find_unappended_batch(
        client=client,
        metadata_df=old_metadata_df,
    )

    if batch_name is None:
        print("\nKhông có Gold crawler batch mới cần append.")
        print("Dừng bước append index.")
        return

    gold_object = gold_batch_object(batch_name)

    print(f"Batch cần append: {batch_name}")
    print(f"Input Gold batch: s3://{MINIO_BUCKET}/{gold_object}")

    # Đọc Gold batch mới
    print("\nBước 3: Đọc Gold batch mới")
    gold_df = read_parquet_from_minio(
        client=client,
        object_name=gold_object,
    )

    print(f"Số dòng Gold batch: {len(gold_df)}")

    if gold_df.empty:
        print("Gold batch rỗng. Dừng append.")
        return

    # Load embedding model
    print("\nBước 4: Load embedding model")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Encode và append title index
    print("\nBước 5: Encode và append title index")
    title_embeddings = encode_texts(
        model=model,
        texts=gold_df["title_text"],
    )

    title_index = append_to_index(
        client=client,
        embeddings=title_embeddings,
        minio_index_path=GOLD_CRAWLER_TITLE_INDEX,
        local_index_path=LOCAL_TITLE_INDEX,
    )

    del title_embeddings
    gc.collect()

    # Encode và append skills index
    print("\nBước 6: Encode và append skills index")
    skills_embeddings = encode_texts(
        model=model,
        texts=gold_df["skills_text"],
    )

    skills_index = append_to_index(
        client=client,
        embeddings=skills_embeddings,
        minio_index_path=GOLD_CRAWLER_SKILLS_INDEX,
        local_index_path=LOCAL_SKILLS_INDEX,
    )

    del skills_embeddings
    gc.collect()

    # Encode và append full index
    print("\nBước 7: Encode và append full index")
    full_embeddings = encode_texts(
        model=model,
        texts=gold_df["full_text"],
    )

    full_index = append_to_index(
        client=client,
        embeddings=full_embeddings,
        minio_index_path=GOLD_CRAWLER_FULL_INDEX,
        local_index_path=LOCAL_FULL_INDEX,
    )

    del full_embeddings
    gc.collect()

    # Append metadata
    print("\nBước 8: Append metadata")
    new_metadata_df = build_metadata_from_gold(gold_df)

    final_metadata_df = append_metadata(
        client=client,
        old_metadata_df=old_metadata_df,
        new_metadata_df=new_metadata_df,
    )

    print(f"Số dòng metadata sau append: {len(final_metadata_df)}")

    # Kiểm tra số dòng metadata và số vector index
    print("\nBước 9: Kiểm tra đồng bộ metadata và index")
    print(f"Metadata rows: {len(final_metadata_df)}")
    print(f"Title index vectors: {title_index.ntotal}")
    print(f"Skills index vectors: {skills_index.ntotal}")
    print(f"Full index vectors: {full_index.ntotal}")

    if not (
        len(final_metadata_df)
        == title_index.ntotal
        == skills_index.ntotal
        == full_index.ntotal
    ):
        raise ValueError(
            "Metadata và FAISS indexes không khớp số dòng/vector."
        )

    # Xóa file local tạm
    LOCAL_METADATA.unlink(missing_ok=True)
    LOCAL_TITLE_INDEX.unlink(missing_ok=True)
    LOCAL_SKILLS_INDEX.unlink(missing_ok=True)
    LOCAL_FULL_INDEX.unlink(missing_ok=True)

    del model
    del gold_df
    del old_metadata_df
    del new_metadata_df
    del final_metadata_df
    del title_index
    del skills_index
    del full_index
    gc.collect()

    print("\nHoàn thành append Gold Crawler batch vào crawler indexes.")


if __name__ == "__main__":
    main()