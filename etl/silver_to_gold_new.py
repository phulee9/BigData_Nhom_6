import io
import os
import json
import pickle
import numpy as np
import pandas as pd
import faiss
from minio import Minio
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DATA_DIR         = Path(__file__).parent.parent / "recommendation" / "data"
INDEX_FILE       = DATA_DIR / "faiss_index_new.bin"
META_FILE        = DATA_DIR / "job_metadata_new.pkl"
ENCODED_LOG_FILE = DATA_DIR / "encoded_files.json"

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key = os.getenv("MINIO_ACCESS_KEY"),
    secret_key = os.getenv("MINIO_SECRET_KEY"),
    secure     = False
)
BUCKET        = os.getenv("MINIO_BUCKET")
PROCESSED_LOG = "silver/processed_files.json"


def load_processed_log() -> set:
    # Doc danh sach files da xu ly tu Bronze sang Silver (tren MinIO)
    try:
        data = json.loads(
            client.get_object(BUCKET, PROCESSED_LOG).read().decode()
        )
        return set(data)
    except Exception:
        return set()


def load_encoded_log() -> set:
    # Doc danh sach files da duoc encode vao FAISS (local)
    if ENCODED_LOG_FILE.exists():
        with open(ENCODED_LOG_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_encoded_log(encoded: set):
    # Luu danh sach files da encode xuong local
    with open(ENCODED_LOG_FILE, "w") as f:
        json.dump(sorted(list(encoded)), f)


def get_new_files(processed: set, encoded: set) -> list:
    # Lay files da co trong Silver nhung chua duoc encode
    # processed - encoded = files can encode tiep
    return sorted(processed - encoded)


def read_silver_file(key: str) -> pd.DataFrame:
    # Doc file Silver tuong ung voi key
    # key: "indeed/2026-04-10.csv" -> silver/new/indeed/2026-04-10.csv
    silver_path = f"silver/new/{key}"
    try:
        data = client.get_object(BUCKET, silver_path).read()
        df   = pd.read_csv(io.BytesIO(data))
        df   = df.dropna(subset=["job_title", "job_skills", "title_skills"])
        print(f"  Doc duoc: {len(df):,} jobs")
        return df
    except Exception as e:
        print(f"  [!] Loi doc Silver: {e}")
        return pd.DataFrame()


def load_existing_index():
    # Load FAISS index va metadata hien co neu da ton tai
    if INDEX_FILE.exists() and META_FILE.exists():
        print("Load FAISS index hien co...")
        index = faiss.read_index(str(INDEX_FILE))
        with open(META_FILE, "rb") as f:
            df_existing = pickle.load(f)
        print(f"Index hien co: {index.ntotal:,} vectors")
        return index, df_existing
    print("Chua co index, tao moi...")
    return None, pd.DataFrame()


def encode_jobs(df: pd.DataFrame) -> np.ndarray:
    # Encode title_skills thanh vectors 384 chieu bang Sentence Transformer
    print(f"  Encode {len(df):,} jobs...")
    model  = SentenceTransformer("all-MiniLM-L6-v2")
    texts  = df["title_skills"].tolist()
    chunks = []

    for i in tqdm(range(0, len(texts), 10000), desc="Encoding"):
        chunk = texts[i:i + 10000]
        emb   = model.encode(
            chunk,
            batch_size           = 256,
            normalize_embeddings = True,
            show_progress_bar    = False
        ).astype("float32")
        chunks.append(emb)

    return np.vstack(chunks)


def append_to_index(
    index,
    df_existing: pd.DataFrame,
    df_new: pd.DataFrame,
    new_vectors: np.ndarray
):
    # Them vectors moi vao FAISS index
    # Neu chua co index thi tao moi IndexFlatIP
    if index is None:
        index = faiss.IndexFlatIP(new_vectors.shape[1])

    old_total = index.ntotal
    index.add(new_vectors)

    # Gop metadata cu va moi
    df_updated = pd.concat(
        [df_existing, df_new], ignore_index=True
    ) if not df_existing.empty else df_new

    print(f"  FAISS: {old_total:,} -> {index.ntotal:,} vectors")
    return index, df_updated


def save_gold_new(index, df_updated: pd.DataFrame):
    # Luu FAISS index va metadata xuong local
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_FILE))
    with open(META_FILE, "wb") as f:
        pickle.dump(df_updated, f)

    print("Gold New xong!")
    print(f"  faiss_index_new.bin  : {INDEX_FILE.stat().st_size / 1e6:.1f} MB")
    print(f"  job_metadata_new.pkl : {META_FILE.stat().st_size / 1e6:.1f} MB")
    print("  Tiep theo: python recommendation/main.py")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Doc processed log va encoded log de tim files chua encode
    processed = load_processed_log()
    encoded   = load_encoded_log()
    print(f"Da xu ly (Silver): {len(processed)} files")
    print(f"Da encode (FAISS) : {len(encoded)} files")

    new_files = get_new_files(processed, encoded)
    if not new_files:
        print("Khong co file moi can encode!")
        exit(0)

    print(f"Can encode: {len(new_files)} files:")
    for f in new_files:
        print(f"  - {f}")

    # Load FAISS index hien co neu co
    index, df_existing = load_existing_index()

    # Xu ly tung file moi
    for key in new_files:
        print(f"\nEncode: {key}")

        # Doc file Silver tuong ung
        df_new = read_silver_file(key)
        if df_new.empty:
            encoded.add(key)
            continue

        # Encode jobs moi thanh vectors
        new_vectors = encode_jobs(df_new)

        # Append vectors vao FAISS index
        index, df_existing = append_to_index(
            index, df_existing, df_new, new_vectors
        )

        # Danh dau file da encode
        encoded.add(key)

    # Luu FAISS index va metadata
    save_gold_new(index, df_existing)

    # Luu encoded log
    save_encoded_log(encoded)
    print("\nXong!")