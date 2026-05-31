from pathlib import Path
import re

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.config import EMBEDDING_MODEL
from src.config.silver_config import CITY_ALIASES
from src.recommendation.core.loader import load_runtime_index
from src.recommendation.core.recommend import (
    build_query_texts,
    encode_query,
    parse_skills,
    search_faiss_index,
)
from src.recommendation.utils.text import normalize_text_lower


# Đường dẫn local chứa crawler metadata + FAISS index
DEFAULT_CRAWLER_RUNTIME_DIR = Path("data/downloads/crawler/gold")


# Trọng số khi gộp điểm title và skills
TITLE_WEIGHT = 0.5
SKILLS_WEIGHT = 0.5


def load_embedding_model():
    # Load embedding model
    return SentenceTransformer(EMBEDDING_MODEL)


def load_crawler_runtime():
    # Load crawler metadata + title index + skills index
    return load_runtime_index(
        source_name="crawler",
        runtime_dir=DEFAULT_CRAWLER_RUNTIME_DIR,
        source_weight=1.0,
    )


def clean_location(value: str | None) -> str:
    # Chuyển location về chữ thường và chuẩn hóa khoảng trắng
    value = normalize_text_lower(value)

    if not value:
        return ""

    value = value.replace("-", " ")
    value = value.replace("_", " ")
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = " ".join(value.split())

    return value


def normalize_location(value: str | None) -> str:
    # Map location bằng regex với CITY_ALIASES
    value = clean_location(value)

    if not value:
        return ""

    aliases = {
        clean_location(alias): city
        for alias, city in CITY_ALIASES.items()
    }

    # Ưu tiên match chính xác
    if value in aliases:
        return aliases[value]

    # Sau đó match theo regex
    for alias, city in aliases.items():
        if not alias:
            continue

        pattern = rf"(^|\s){re.escape(alias)}($|\s)"

        if re.search(pattern, value):
            return city

    return value


def filter_metadata_by_city(
    metadata: pd.DataFrame,
    location: str | None,
) -> pd.DataFrame:
    # Lọc metadata theo city trước khi search FAISS
    metadata = metadata.copy()
    metadata["row_idx"] = metadata.index

    target_city = normalize_location(location)

    if not target_city:
        return metadata

    if "city" not in metadata.columns:
        raise KeyError("Metadata không có cột city.")

    metadata["city_normalized"] = metadata["city"].apply(
        normalize_location
    )

    filtered = metadata[
        metadata["city_normalized"] == target_city
    ].copy()

    return filtered.drop(
        columns=["city_normalized"],
        errors="ignore",
    )


def build_subset_index(
    source_index,
    row_indices: list[int],
):
    # Tạo FAISS index tạm từ các job đã lọc theo city
    vectors = [
        source_index.reconstruct(int(row_idx))
        for row_idx in row_indices
    ]

    vectors = np.asarray(vectors).astype("float32")

    subset_index = faiss.IndexFlatIP(source_index.d)
    subset_index.add(vectors)

    return subset_index


def search_subset_index(
    source_index,
    query_vector,
    row_indices: list[int],
    top_k: int,
) -> pd.DataFrame:
    # Search trên subset index và map về row_idx gốc
    if not row_indices:
        return pd.DataFrame(
            columns=[
                "row_idx",
                "score",
            ]
        )

    subset_index = build_subset_index(
        source_index=source_index,
        row_indices=row_indices,
    )

    top_k = min(top_k, len(row_indices))

    scores, local_ids = subset_index.search(
        query_vector,
        top_k,
    )

    rows = []

    for local_id, score in zip(local_ids[0], scores[0]):
        if local_id < 0:
            continue

        rows.append(
            {
                "row_idx": int(row_indices[int(local_id)]),
                "score": float(score),
            }
        )

    return pd.DataFrame(rows)


def search_full_index(
    index,
    query_vector,
    top_k: int,
) -> pd.DataFrame:
    # Search toàn bộ index khi user không nhập location
    results = search_faiss_index(
        index=index,
        query_embedding=query_vector,
        top_k=top_k,
    )

    return pd.DataFrame(
        results,
        columns=[
            "row_idx",
            "score",
        ],
    )


def search_index(
    index,
    query_vector,
    row_indices: list[int],
    has_location: bool,
    top_k: int,
) -> pd.DataFrame:
    # Nếu có location thì search subset, không có thì search toàn bộ
    if has_location:
        return search_subset_index(
            source_index=index,
            query_vector=query_vector,
            row_indices=row_indices,
            top_k=top_k,
        )

    return search_full_index(
        index=index,
        query_vector=query_vector,
        top_k=top_k,
    )


def search_crawler_faiss(
    model,
    runtime,
    job_title: str,
    skills,
    location: str | None = None,
    top_k_each_index: int = 100,
) -> pd.DataFrame:
    # Lọc city trước
    filtered_metadata = filter_metadata_by_city(
        metadata=runtime.metadata,
        location=location,
    )

    if filtered_metadata.empty:
        return pd.DataFrame()

    row_indices = filtered_metadata["row_idx"].astype(int).tolist()
    has_location = bool(normalize_location(location))

    # Parse skills input
    user_skills = parse_skills(skills)

    # Tạo query title và skills
    query_texts = build_query_texts(
        job_title=job_title,
        skills=user_skills,
    )

    # Encode query title
    title_vector = encode_query(
        model=model,
        text=query_texts["title_text"],
    )

    # Encode query skills
    skills_vector = encode_query(
        model=model,
        text=query_texts["skills_text"],
    )

    # Search title index
    title_df = search_index(
        index=runtime.title_index,
        query_vector=title_vector,
        row_indices=row_indices,
        has_location=has_location,
        top_k=top_k_each_index,
    ).rename(
        columns={
            "score": "title_score",
        }
    )

    # Search skills index
    skills_df = search_index(
        index=runtime.skills_index,
        query_vector=skills_vector,
        row_indices=row_indices,
        has_location=has_location,
        top_k=top_k_each_index,
    ).rename(
        columns={
            "score": "skills_score",
        }
    )

    # Gộp kết quả title và skills
    candidates = title_df.merge(
        skills_df,
        on="row_idx",
        how="outer",
    ).fillna(0)

    # Tính điểm cuối
    candidates["final_score"] = (
        TITLE_WEIGHT * candidates["title_score"]
        + SKILLS_WEIGHT * candidates["skills_score"]
    )

    return (
        candidates
        .sort_values("final_score", ascending=False)
        .reset_index(drop=True)
    )


def get_first_value(
    row,
    columns: list[str],
    default="",
):
    # Lấy giá trị theo danh sách cột ưu tiên
    for column in columns:
        if column not in row.index:
            continue

        value = row.get(column)

        if pd.notna(value) and str(value).strip() != "":
            return value

    return default


def build_job_results(
    candidates: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    # Join kết quả FAISS với metadata job
    rows = []

    for item in candidates.itertuples(index=False):
        metadata_row = metadata.iloc[int(item.row_idx)]

        title = get_first_value(
            metadata_row,
            [
                "title_core",
                "job_title",
                "title",
            ],
        )

        city = get_first_value(
            metadata_row,
            [
                "city",
            ],
        )

        location_raw = get_first_value(
            metadata_row,
            [
                "location_raw",
            ],
        )

        link = get_first_value(
            metadata_row,
            [
                "job_url",
                "job_link",
                "url",
                "link",
            ],
        )

        rows.append(
            {
                "title": title,
                "city": city,
                "location_raw": location_raw,
                "score": float(item.final_score),
                "link": link,
            }
        )

    return pd.DataFrame(rows)


def recommend_jobs_by_faiss(
    model,
    runtime,
    job_title: str,
    skills,
    location: str | None = None,
    top_k_each_index: int = 100,
    top_n: int = 10,
) -> pd.DataFrame:
    # Recommend job theo city trước, FAISS sau
    candidates = search_crawler_faiss(
        model=model,
        runtime=runtime,
        job_title=job_title,
        skills=skills,
        location=location,
        top_k_each_index=top_k_each_index,
    )

    if candidates.empty:
        return pd.DataFrame()

    jobs = build_job_results(
        candidates=candidates,
        metadata=runtime.metadata,
    )

    return (
        jobs
        .sort_values("score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )