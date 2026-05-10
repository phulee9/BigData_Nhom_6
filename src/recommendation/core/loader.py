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
    full_index: faiss.Index


def load_runtime_index(
    source_name: str,
    runtime_dir: str | Path,
    source_weight: float = 1.0,
) -> RuntimeIndex:
    """
    Load metadata + 3 FAISS indexes:
    - title.faiss.index
    - skills.faiss.index
    - full.faiss.index

    Đồng thời kiểm tra:
    metadata rows = title index vectors = skills index vectors = full index vectors
    """
    runtime_dir = Path(runtime_dir)

    metadata_path = runtime_dir / "metadata.parquet"
    title_index_path = runtime_dir / "title.faiss.index"
    skills_index_path = runtime_dir / "skills.faiss.index"
    full_index_path = runtime_dir / "full.faiss.index"

    required_files = [
        metadata_path,
        title_index_path,
        skills_index_path,
        full_index_path,
    ]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file runtime index: {file_path}"
            )

    metadata = pd.read_parquet(metadata_path)

    title_index = faiss.read_index(str(title_index_path))
    skills_index = faiss.read_index(str(skills_index_path))
    full_index = faiss.read_index(str(full_index_path))

    validate_runtime_index(
        source_name=source_name,
        metadata=metadata,
        title_index=title_index,
        skills_index=skills_index,
        full_index=full_index,
    )

    return RuntimeIndex(
        source_name=source_name,
        source_weight=source_weight,
        metadata=metadata,
        title_index=title_index,
        skills_index=skills_index,
        full_index=full_index,
    )


def validate_runtime_index(
    source_name: str,
    metadata: pd.DataFrame,
    title_index: faiss.Index,
    skills_index: faiss.Index,
    full_index: faiss.Index,
) -> None:
    """
    Đảm bảo metadata và 3 index đồng bộ số dòng/vector.
    """
    metadata_rows = len(metadata)

    title_vectors = title_index.ntotal
    skills_vectors = skills_index.ntotal
    full_vectors = full_index.ntotal

    if not (
        metadata_rows
        == title_vectors
        == skills_vectors
        == full_vectors
    ):
        raise ValueError(
            f"Runtime index không đồng bộ cho source={source_name}. "
            f"metadata={metadata_rows}, "
            f"title_index={title_vectors}, "
            f"skills_index={skills_vectors}, "
            f"full_index={full_vectors}"
        )

    print(f"[OK] Loaded runtime index: {source_name}")
    print(f"     Metadata rows : {metadata_rows}")
    print(f"     Title vectors : {title_vectors}")
    print(f"     Skills vectors: {skills_vectors}")
    print(f"     Full vectors  : {full_vectors}")