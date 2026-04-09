import pickle
import faiss
from pathlib import Path

DATA_DIR   = Path(__file__).parent.parent / "data"
INDEX_FILE = DATA_DIR / "faiss_index.bin"
META_FILE  = DATA_DIR / "job_metadata.pkl"


def load_index():
    # Load FAISS index và metadata từ thư mục data
    for f in [INDEX_FILE, META_FILE]:
        if not f.exists():
            raise FileNotFoundError(f"\n[LOI] Khong tim thay: {f}")

    print("Load FAISS index...")
    index = faiss.read_index(str(INDEX_FILE))

    with open(META_FILE, "rb") as f:
        df = pickle.load(f)

    print(f"{index.ntotal:,} vectors | {len(df):,} jobs")
    return index, df