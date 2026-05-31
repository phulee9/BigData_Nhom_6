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
    """
    Load metadata + 2 FAISS indexes:
    - title index
    - skills index

    Ten file linh hoat:
    - metadata: metadata.parquet hoac jobs_metadata.parquet
    - title: title.faiss.index hoac title_faiss.index
    - skills: skills.faiss.index hoac skills_faiss.index

    Kiem tra: metadata rows = title vectors = skills vectors
    """
    runtime_dir = Path(runtime_dir)

    metadata_path = _find_file(
        runtime_dir,
        ["metadata.parquet", "jobs_metadata.parquet"],
        required=True,
        label="metadata",
    )

    title_index_path = _find_file(
        runtime_dir,
        ["title.faiss.index", "title_faiss.index"],
        required=True,
        label="title index",
    )

    skills_index_path = _find_file(
        runtime_dir,
        ["skills.faiss.index", "skills_faiss.index"],
        required=True,
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


def _find_file(
    directory: Path,
    candidate_names: list[str],
    required: bool,
    label: str,
) -> Path | None:
    """
    Tim file trong thu muc theo danh sach ten uu tien.
    Tra ve path dau tien tim thay.
    """
    for name in candidate_names:
        path = directory / name
        if path.exists():
            return path

    if required:
        raise FileNotFoundError(
            f"Khong tim thay file {label} trong {directory}. "
            f"Da tim: {candidate_names}"
        )

    return None


def validate_runtime_index(
    source_name: str,
    metadata: pd.DataFrame,
    title_index: faiss.Index,
    skills_index: faiss.Index,
) -> None:
    """
    Dam bao metadata va 2 index dong bo so dong/vector.
    """
    metadata_rows = len(metadata)

    title_vectors = title_index.ntotal
    skills_vectors = skills_index.ntotal

    if not (
        metadata_rows
        == title_vectors
        == skills_vectors
    ):
        raise ValueError(
            f"Runtime index khong dong bo cho source={source_name}. "
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
