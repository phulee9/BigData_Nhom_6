import pickle
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "models" / "kaggle"


def load_system():
    faiss_path = MODEL_DIR / "faiss.index"
    metadata_path = MODEL_DIR / "metadata.pkl"

    if not faiss_path.exists():
        raise FileNotFoundError(f"Không tìm thấy FAISS index: {faiss_path}")

    if not metadata_path.exists():
        raise FileNotFoundError(f"Không tìm thấy metadata: {metadata_path}")

    index = faiss.read_index(str(faiss_path))

    with open(metadata_path, "rb") as f:
        metadata = pickle.load(f)

    model = SentenceTransformer("all-MiniLM-L6-v2")

    return index, metadata, model