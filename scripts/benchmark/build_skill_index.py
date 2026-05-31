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
EMB_PATH = _ROOT / "data/faiss/skills_embeddings.npy"
OUT_DIR  = _ROOT / "data/runtime_index/kaggle/benchmark"
OUT_PATH = OUT_DIR / "skills_faiss.index"

# ── HNSWFlat config (từ benchmark_skills.ipynb) ────────────────────────────
HNSW_M               = 32     # số neighbor mỗi node (trade-off size/recall)
HNSW_EF_CONSTRUCTION = 200    # efConstruction (cao hơn = recall tốt hơn lúc build)
HNSW_EF_SEARCH       = 16     # best efSearch từ benchmark_skills.ipynb (recall=0.9845, 37.39x)
BATCH_SIZE           = 100_000


# ── helpers ────────────────────────────────────────────────────────────────

def load_normalize_batch(x_all: np.ndarray, start: int, end: int) -> np.ndarray:
    """Load một batch, ép float32, L2-normalize (để dùng IP ≡ cosine)."""
    batch = np.array(x_all[start:end], dtype="float32", copy=True)
    batch = np.ascontiguousarray(batch)
    faiss.normalize_L2(batch)
    return batch


def build_hnsw(emb_path: Path, out_path: Path, ef_search: int) -> None:
    log.info("Loading embeddings từ %s", emb_path)
    x_all = np.load(emb_path, mmap_mode="r")
    n_total, d = x_all.shape
    log.info("Shape: %s  dtype: %s", x_all.shape, x_all.dtype)

    # ── khởi tạo index ─────────────────────────────────────────────────────
    index = faiss.IndexHNSWFlat(d, HNSW_M, faiss.METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
    index.hnsw.efSearch       = ef_search

    log.info(
        "HNSWFlat — M=%d  efConstruction=%d  efSearch=%d",
        HNSW_M, HNSW_EF_CONSTRUCTION, ef_search,
    )

    # ── add vectors theo batch ─────────────────────────────────────────────
    # HNSW không cần train; add trực tiếp
    log.info("Adding %d vectors (batch=%d) …", n_total, BATCH_SIZE)
    t0 = time.perf_counter()

    for start in range(0, n_total, BATCH_SIZE):
        end     = min(start + BATCH_SIZE, n_total)
        batch   = load_normalize_batch(x_all, start, end)
        index.add(batch)

        elapsed = time.perf_counter() - t0
        speed   = end / elapsed if elapsed > 0 else float("inf")
        eta     = (n_total - end) / speed if speed > 0 else 0
        log.info(
            "  %d / %d  | %.1f min elapsed | ETA %.1f min",
            end, n_total, elapsed / 60, eta / 60,
        )

    elapsed_total = time.perf_counter() - t0
    log.info("Add xong — %.1f s | ntotal=%d", elapsed_total, index.ntotal)
    assert index.ntotal == n_total, f"ntotal mismatch: {index.ntotal} != {n_total}"

    # ── save ───────────────────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out_path))
    size_mb = out_path.stat().st_size / 1024 / 1024
    log.info("Saved → %s  (%.1f MB)", out_path, size_mb)
    log.info("Tổng thời gian build: %.1f s (%.1f phút)", elapsed_total, elapsed_total / 60)

    del index; gc.collect()


def verify(path: Path, n_expected: int, d_expected: int = 384) -> None:
    log.info("Verifying %s …", path.name)
    idx = faiss.read_index(str(path))
    ok  = idx.d == d_expected and idx.ntotal == n_expected
    status = "OK ✓" if ok else "FAIL ✗"
    log.info("  dim=%d  ntotal=%d  efSearch=%d  → %s",
              idx.d, idx.ntotal, idx.hnsw.efSearch, status)
    if not ok:
        raise RuntimeError(f"Verify FAIL: dim={idx.d} ntotal={idx.ntotal}")
    del idx; gc.collect()


# ── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Build HNSWFlat index cho skill_embeddings")
    p.add_argument("--emb",       type=Path, default=EMB_PATH,     help="Path tới skill_embeddings.npy")
    p.add_argument("--out",       type=Path, default=OUT_PATH,     help="Path lưu file .index")
    p.add_argument("--ef-search", type=int,  default=HNSW_EF_SEARCH, help="efSearch (default từ benchmark)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    log.info("=" * 60)
    log.info("BUILD SKILL INDEX — HNSWFlat")
    log.info("  emb          : %s", args.emb)
    log.info("  out          : %s", args.out)
    log.info("  M            : %d", HNSW_M)
    log.info("  efConstruct  : %d", HNSW_EF_CONSTRUCTION)
    log.info("  efSearch     : %d", args.ef_search)
    log.info("=" * 60)

    build_hnsw(args.emb, args.out, args.ef_search)

    x_all = np.load(args.emb, mmap_mode="r")
    verify(args.out, n_expected=x_all.shape[0])

    log.info("Done.")
