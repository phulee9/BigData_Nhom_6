import os
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

# Thư mục lưu file Gold
DATA_DIR = Path(__file__).parent.parent / "recommendation" / "data"

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")


def read_silver() -> pd.DataFrame:
    # Đọc Silver từ MinIO
    print("[1/3] Doc Silver tu MinIO...")
    df = pd.read_csv(
        client.get_object(BUCKET, "silver/Silver_Jobs_Cleaned.csv")
    ).dropna(subset=["job_title", "job_skills", "title_skills"])
    print(f"{len(df):,} jobs | {df['job_title'].nunique():,} unique titles")
    return df


def encode_embeddings(df: pd.DataFrame) -> Path:
    # Encode title_skills thành vectors bằng Sentence Transformer
    print("[2/3] Encode embeddings (CPU ~75-90 phut)...")
    model    = SentenceTransformer("all-MiniLM-L6-v2")
    texts    = df["title_skills"].tolist()
    emb_file = DATA_DIR / "embeddings.npy"

    with open(emb_file, "wb") as f:
        for i in tqdm(range(0, len(texts), 100000), desc="Encoding"):
            chunk = texts[i:i + 100000]
            emb   = model.encode(
                chunk,
                batch_size          = 256,
                normalize_embeddings = True,
                show_progress_bar   = False
            ).astype("float32")
            np.save(f, emb)

    print(f"Embeddings: {emb_file}")
    return emb_file


def build_faiss_index(emb_file: Path) -> faiss.Index:
    # Build FAISS IndexFlatIP từ embeddings đã encode
    print("[3/3] Build FAISS index...")
    index = faiss.IndexFlatIP(384)

    with open(emb_file, "rb") as f:
        while True:
            try:
                index.add(np.load(f))
            except (ValueError, EOFError):
                break

    print(f"FAISS: {index.ntotal:,} vectors")
    return index


def save_gold(index: faiss.Index, df: pd.DataFrame):
    # Lưu FAISS index và metadata xuống thư mục data
    index_file = DATA_DIR / "faiss_index.bin"
    meta_file  = DATA_DIR / "job_metadata.pkl"

    faiss.write_index(index, str(index_file))
    with open(meta_file, "wb") as f:
        pickle.dump(df, f)

    print("Gold xong!")
    print(f"  faiss_index.bin  : {index_file.stat().st_size / 1e6:.1f} MB")
    print(f"  job_metadata.pkl : {meta_file.stat().st_size / 1e6:.1f} MB")
    print("  Tiep theo: python recommendation/main.py")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df       = read_silver()
    emb_file = encode_embeddings(df)
    index    = build_faiss_index(emb_file)
    save_gold(index, df)