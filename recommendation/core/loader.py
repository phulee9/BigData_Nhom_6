import pickle
import faiss
from pathlib import Path

DATA_DIR       = Path(__file__).parent.parent / "data"
INDEX_FILE_OLD = DATA_DIR / "faiss_index.bin"
META_FILE_OLD  = DATA_DIR / "job_metadata.pkl"
INDEX_FILE_NEW = DATA_DIR / "faiss_index_new.bin"
META_FILE_NEW  = DATA_DIR / "job_metadata_new.pkl"


def load_index():
    # Load FAISS index va metadata cua data cu (Kaggle 812K)
    for f in [INDEX_FILE_OLD, META_FILE_OLD]:
        if not f.exists():
            raise FileNotFoundError(f"\n[LOI] Khong tim thay: {f}")

    print("Load FAISS index cu...")
    index_old = faiss.read_index(str(INDEX_FILE_OLD))
    with open(META_FILE_OLD, "rb") as f:
        df_old = pickle.load(f)

    print(f"Index cu: {index_old.ntotal:,} vectors | {len(df_old):,} jobs")
    return index_old, df_old


def load_index_new():
    # Load FAISS index va metadata cua data moi (Crawl)
    # Tra ve None neu chua co data crawl
    if not INDEX_FILE_NEW.exists() or not META_FILE_NEW.exists():
        print("Chua co index moi, chi dung index cu")
        return None, None

    print("Load FAISS index moi...")
    index_new = faiss.read_index(str(INDEX_FILE_NEW))
    with open(META_FILE_NEW, "rb") as f:
        df_new = pickle.load(f)

    print(f"Index moi: {index_new.ntotal:,} vectors | {len(df_new):,} jobs")
    return index_new, df_new


def load_all_indexes():
    # Load ca 2 index cung luc
    # Dung cho recommend.py khi can goi y tu ca 2 nguon
    index_old, df_old = load_index()
    index_new, df_new = load_index_new()
    return index_old, df_old, index_new, df_new