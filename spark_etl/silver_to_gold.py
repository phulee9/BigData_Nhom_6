import os, pickle
import numpy as np
import pandas as pd
import faiss
from minio import Minio
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent.parent / "recomendation_system"

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")

# ── Đọc Silver ─────────────────────────────────────────
print("⏳ [1/3] Đọc Silver từ MinIO...")
df = pd.read_csv(
    client.get_object(BUCKET, "silver/Silver_Jobs_Cleaned.csv")
).dropna(subset=["job_title", "job_skills", "title_skills"])

print(f"✓ {len(df):,} jobs")
print(f"✓ Unique job_title: {df['job_title'].nunique():,}")

# ── Encode ─────────────────────────────────────────────
print("⏳ [2/3] Encode embeddings (CPU ~75-90 phút)...")
model    = SentenceTransformer("all-MiniLM-L6-v2")
texts    = df["title_skills"].tolist()
EMB_FILE = BASE_DIR / "embeddings.npy"

with open(EMB_FILE, "wb") as f:
    for i in tqdm(range(0, len(texts), 100000), desc="Encoding"):
        chunk = texts[i:i + 100000]
        emb   = model.encode(
            chunk,
            batch_size=256,
            normalize_embeddings=True,
            show_progress_bar=False
        ).astype("float32")
        np.save(f, emb)

print(f"✓ Embeddings: {EMB_FILE}")

# ── Build FAISS ─────────────────────────────────────────
print("⏳ [3/3] Build FAISS index...")
index = faiss.IndexFlatIP(384)
with open(EMB_FILE, "rb") as f:
    while True:
        try:
            index.add(np.load(f))
        except (ValueError, EOFError):
            break

print(f"✓ FAISS: {index.ntotal:,} vectors")

# ── Lưu ───────────────────────────────────────────────
faiss.write_index(index, str(BASE_DIR / "faiss_index.bin"))
with open(BASE_DIR / "job_metadata.pkl", "wb") as f:
    pickle.dump(df, f)

print("✓ Gold xong!")
print(f"  faiss_index.bin  : {(BASE_DIR/'faiss_index.bin').stat().st_size/1e6:.1f} MB")
print(f"  job_metadata.pkl : {(BASE_DIR/'job_metadata.pkl').stat().st_size/1e6:.1f} MB")
print("  Tiếp theo: python recomendation_system/main.py")