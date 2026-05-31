from dataclasses import dataclass
from pathlib import Path

import faiss
import pandas as pd


@dataclass
class RuntimeIndex:
    source_name: str
    source_weight: float
    metadata: pd.DataFrame
    title_index: faiss.Index
    skills_index: faiss.Index


def load_runtime_index(
    source_name: str,
    runtime_dir: str | Path,
    source_weight: float = 1.0,
) -> RuntimeIndex:
    runtime_dir = Path(runtime_dir)

    if not runtime_dir.exists():
        raise FileNotFoundError(f"Runtime folder not found: {runtime_dir}")

    metadata_path = find_first_existing_file(
        base_dir=runtime_dir,
        candidate_paths=[
            "metadata.parquet",
            "jobs_metadata.parquet",
            "metadata/metadata.parquet",
            "metadata/jobs_metadata.parquet",
        ],
        label="metadata",
    )

    title_index_path = find_first_existing_file(
        base_dir=runtime_dir,
        candidate_paths=[
            "title.faiss.index",
            "title_faiss.index",
            "index/title.faiss.index",
            "index/title_faiss.index",
        ],
        label="title index",
    )

    skills_index_path = find_first_existing_file(
        base_dir=runtime_dir,
        candidate_paths=[
            "skills.faiss.index",
            "skills_faiss.index",
            "index/skills.faiss.index",
            "index/skills_faiss.index",
        ],
        label="skills index",
    )

    metadata = pd.read_parquet(metadata_path)

    title_index = faiss.read_index(str(title_index_path))
    skills_index = faiss.read_index(str(skills_index_path))

    # IVFFlat: nprobe KHÔNG được lưu vào file index -> reset ve 1 sau khi load.
    # HNSWFlat: efSearch duoc luu vao file -> set tuong minh cho ro rang.
    _configure_index(title_index,  label="title")
    _configure_index(skills_index, label="skills")

    validate_runtime_index(
        source_name=source_name,
        metadata=metadata,
        title_index=title_index,
        skills_index=skills_index,
    )

    return RuntimeIndex(
        source_name=source_name,
        source_weight=source_weight,
        metadata=metadata,
        title_index=title_index,
        skills_index=skills_index,
    )


def find_first_existing_file(
    base_dir: Path,
    candidate_paths: list[str],
    label: str,
) -> Path:
    checked_paths = []

    for relative_path in candidate_paths:
        full_path = base_dir / relative_path
        checked_paths.append(str(full_path))

        if full_path.exists():
            return full_path

    raise FileNotFoundError(
        f"Cannot find {label} in {base_dir}.\n"
        f"Checked paths:\n- " + "\n- ".join(checked_paths)
    )


def validate_runtime_index(
    source_name: str,
    metadata: pd.DataFrame,
    title_index: faiss.Index,
    skills_index: faiss.Index,
) -> None:
    # Kiểm tra số dòng metadata có khớp số vector không
    metadata_rows = len(metadata)
    title_vectors = title_index.ntotal
    skills_vectors = skills_index.ntotal

    if metadata_rows != title_vectors or metadata_rows != skills_vectors:
        raise ValueError(
            f"Runtime index is not synchronized for source={source_name}. "
            f"metadata={metadata_rows}, "
            f"title_index={title_vectors}, "
            f"skills_index={skills_vectors}"
        )

    print(f"[OK] Loaded runtime index: {source_name}")
    print(f"     Metadata rows : {metadata_rows}")
    print(f"     Title vectors : {title_vectors}")
    print(f"     Skills vectors: {skills_vectors}")

# ── Index config sau khi load ──────────────────────────────────────────────

# Config này phải khớp với config đã dùng trong benchmark
_IVF_NPROBE   = 16   # benchmark_title.ipynb → best nprobe
_HNSW_EFSEARCH = 16  # benchmark_skills.ipynb → best efSearch

def _configure_index(index: faiss.Index, label: str) -> None:
    """
    Set runtime params sau khi load index từ file.

    - IVFFlat : nprobe bị reset về 1 khi load → phải set lại
    - HNSWFlat: efSearch được lưu vào file → set lại cho tường minh
    - FlatIP   : không có param nào cần set
    """
    index_type = type(index).__name__

    if isinstance(index, faiss.IndexIVF):
        # Bao gồm IndexIVFFlat, IndexIVFPQ, ...
        old = index.nprobe
        index.nprobe = _IVF_NPROBE
        print(f"  [{label}] IVF index — nprobe: {old} → {index.nprobe}")

    elif isinstance(index, faiss.IndexHNSWFlat):
        old = index.hnsw.efSearch
        index.hnsw.efSearch = _HNSW_EFSEARCH
        print(f"  [{label}] HNSW index — efSearch: {old} → {index.hnsw.efSearch}")

    else:
        # FlatIP hoặc loại khác — không cần config
        print(f"  [{label}] {index_type} — no runtime config needed")
