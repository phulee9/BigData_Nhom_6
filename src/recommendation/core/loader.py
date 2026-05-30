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
    print(f"Metadata rows : {metadata_rows:,}")
    print(f"Title vectors : {title_vectors:,}")
    print(f"Skills vectors: {skills_vectors:,}")