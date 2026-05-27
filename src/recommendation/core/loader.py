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