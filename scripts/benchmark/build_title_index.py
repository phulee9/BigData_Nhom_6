import gc
import time
import argparse
import logging
from pathlib import Path

import faiss
import numpy as np

# ── logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── default paths ──────────────────────────────────────────────────────────
_ROOT    = Path(__file__).resolve().parent.parent.parent
EMB_PATH     = _ROOT / "data/faiss/title_embeddings.npy"
OUT_DIR      = _ROOT / "data/runtime_index/kaggle/benchmark"
OUT_PATH     = OUT_DIR / "title_faiss.index"

# ── IVFFlat config (từ benchmark_title.ipynb) ─────────────────────────────
IVF_NLIST      = 1024          # số cluster; sqrt(N) ≈ 1140 với 1.3M vectors
IVF_NPROBE     = 8             # best nprobe từ benchmark_title.ipynb (recall=0.973, 3.79x)            # best nprobe từ benchmark (thay đổi nếu cần)
IVF_TRAIN_SIZE = 50_000       # số vector dùng để train quantizer
BATCH_SIZE     = 100_000       # số vector mỗi lần add vào index


# ── helpers ────────────────────────────────────────────────────────────────

def load_normalize_batch(x_all: np.ndarray, start: int, end: int) -> np.ndarray:
    """Load một batch, ép float32, L2-normalize (để dùng IP ≡ cosine)."""
    batch = np.array(x_all[start:end], dtype="float32", copy=True)
    batch = np.ascontiguousarray(batch)
    faiss.normalize_L2(batch)
    return batch


def build_ivf(emb_path: Path, out_path: Path, nprobe: int) -> None:
    log.info("Loading embeddings từ %s", emb_path)
    x_all = np.load(emb_path, mmap_mode="r")
    n_total, d = x_all.shape
    log.info("Shape: %s  dtype: %s", x_all.shape, x_all.dtype)

    # ── train quantizer ────────────────────────────────────────────────────
    log.info("Sampling %d vectors để train IVF quantizer …", IVF_TRAIN_SIZE)
    rng       = np.random.default_rng(42)
    train_ids = rng.choice(n_total, size=min(IVF_TRAIN_SIZE, n_total), replace=False)
    x_train   = np.array(x_all[np.sort(train_ids)], dtype="float32")
    x_train   = np.ascontiguousarray(x_train)
    faiss.normalize_L2(x_train)

    quantizer = faiss.IndexFlatIP(d)
    index     = faiss.IndexIVFFlat(quantizer, d, IVF_NLIST, faiss.METRIC_INNER_PRODUCT)

    t0 = time.perf_counter()
    log.info("Training IVF (nlist=%d) …", IVF_NLIST)
    index.train(x_train)
    del x_train; gc.collect()
    log.info("  train xong — %.1f s", time.perf_counter() - t0)

    # ── add vectors theo batch ─────────────────────────────────────────────
    log.info("Adding %d vectors (batch=%d) …", n_total, BATCH_SIZE)
    t_add = time.perf_counter()

    for start in range(0, n_total, BATCH_SIZE):
        end   = min(start + BATCH_SIZE, n_total)
        batch = load_normalize_batch(x_all, start, end)
        index.add(batch)
        pct = end / n_total * 100
        log.info("  %d / %d  (%.1f%%)", end, n_total, pct)

    elapsed_add = time.perf_counter() - t_add
    log.info("Add xong — %.1f s | ntotal=%d", elapsed_add, index.ntotal)
    assert index.ntotal == n_total, f"ntotal mismatch: {index.ntotal} != {n_total}"

    # ── set nprobe & save ──────────────────────────────────────────────────
    index.nprobe = nprobe
    out_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out_path))
    size_mb = out_path.stat().st_size / 1024 / 1024
    log.info("Saved → %s  (%.1f MB)", out_path, size_mb)

    total = time.perf_counter() - t0
    log.info("Tổng thời gian build: %.1f s (%.1f phút)", total, total / 60)

    del index; gc.collect()


def verify(path: Path, n_expected: int, d_expected: int = 384) -> None:
    log.info("Verifying %s …", path.name)
    idx = faiss.read_index(str(path))
    ok  = idx.d == d_expected and idx.ntotal == n_expected
    status = "OK ✓" if ok else "FAIL ✗"
    log.info("  dim=%d  ntotal=%d  nprobe=%d  → %s",
              idx.d, idx.ntotal, idx.nprobe, status)
    if not ok:
        raise RuntimeError(f"Verify FAIL: dim={idx.d} ntotal={idx.ntotal}")
    del idx; gc.collect()


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Build IVFFlat index cho title_embeddings")
    p.add_argument("--emb",    type=Path, default=EMB_PATH,  help="Path tới title_embeddings.npy")
    p.add_argument("--out",    type=Path, default=OUT_PATH,  help="Path lưu file .index")
    p.add_argument("--nprobe", type=int,  default=IVF_NPROBE, help="nprobe (default từ benchmark)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    log.info("=" * 60)
    log.info("BUILD TITLE INDEX — IVFFlat")
    log.info("  emb    : %s", args.emb)
    log.info("  out    : %s", args.out)
    log.info("  nlist  : %d", IVF_NLIST)
    log.info("  nprobe : %d", args.nprobe)
    log.info("=" * 60)

    build_ivf(args.emb, args.out, args.nprobe)

    x_all = np.load(args.emb, mmap_mode="r")
    verify(args.out, n_expected=x_all.shape[0])

    log.info("Done.")
