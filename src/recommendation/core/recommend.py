from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.config import NORMALIZE_EMBEDDINGS
from src.recommendation.core.loader import RuntimeIndex, load_runtime_index
from src.recommendation.utils.text import (
    normalize_text_lower,
    normalize_token,
    parse_skills_lower,
    skills_to_text,
)


# Đường dẫn Kaggle FAISS local
DEFAULT_KAGGLE_RUNTIME_DIR = Path("data/downloads/kaggle/benchmark")


# Hybrid đang dùng biến này
SOURCE_TOP_K = {
    "kaggle": 300,
}


# Trọng số khi gộp title_score và skills_score
TITLE_WEIGHT = 0.4
SKILLS_WEIGHT = 0.6


# Giữ tên cũ để file hybrid không phải sửa nhiều
parse_skills = parse_skills_lower


def build_query_texts(
    job_title: str,
    skills: list[str],
) -> dict[str, str]:
    # Tạo text query cho title index và skills index
    job_title = normalize_text_lower(job_title) or "not specified"
    skills_text = skills_to_text(skills)

    return {
        "title_text": f"Job title: {job_title}.",
        "skills_text": f"Skills: {skills_text}.",
    }


def encode_query(
    model: SentenceTransformer,
    text: str,
) -> np.ndarray:
    # Encode query thành vector
    embedding = model.encode(
        [text],
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return embedding.astype("float32")


def search_faiss_index(
    index,
    query_embedding: np.ndarray,
    top_k: int,
) -> list[tuple[int, float]]:
    # Search FAISS index
    scores, row_ids = index.search(
        query_embedding,
        top_k,
    )

    results = []

    for row_id, score in zip(row_ids[0], scores[0]):
        if row_id < 0:
            continue

        results.append(
            (
                int(row_id),
                float(score),
            )
        )

    return results


def load_default_runtime_indexes() -> list[RuntimeIndex]:
    # Chỉ load Kaggle index
    runtime = load_runtime_index(
        source_name="kaggle",
        runtime_dir=DEFAULT_KAGGLE_RUNTIME_DIR,
        source_weight=1.0,
    )

    return [runtime]


def collect_candidates_from_source(
    runtime_index: RuntimeIndex,
    query_embeddings: dict[str, np.ndarray],
    top_k_each_index: int,
) -> dict[tuple[str, int], dict[str, Any]]:
    # Search title index và skills index
    candidates = {}

    search_plan = [
        (
            "title_score",
            runtime_index.title_index,
            query_embeddings["title_text"],
        ),
        (
            "skills_score",
            runtime_index.skills_index,
            query_embeddings["skills_text"],
        ),
    ]

    for score_name, index, embedding in search_plan:
        search_results = search_faiss_index(
            index=index,
            query_embedding=embedding,
            top_k=top_k_each_index,
        )

        for row_idx, score in search_results:
            key = (
                runtime_index.source_name,
                row_idx,
            )

            if key not in candidates:
                candidates[key] = {
                    "source_name": runtime_index.source_name,
                    "row_idx": row_idx,
                    "title_score": 0.0,
                    "skills_score": 0.0,
                }

            candidates[key][score_name] = max(
                candidates[key][score_name],
                score,
            )

    return candidates


def build_candidate_rows(
    candidates: dict[tuple[str, int], dict[str, Any]],
    runtime_indexes: list[RuntimeIndex],
    user_job_title: str,
    user_skills: list[str],
) -> pd.DataFrame:
    # Join candidate với metadata
    runtime_map = {
        runtime.source_name: runtime
        for runtime in runtime_indexes
    }

    rows = []

    for candidate in candidates.values():
        source_name = candidate["source_name"]
        row_idx = candidate["row_idx"]

        runtime = runtime_map[source_name]
        metadata_row = runtime.metadata.iloc[row_idx]

        title_score = float(candidate["title_score"])
        skills_score = float(candidate["skills_score"])

        semantic_score = (
            TITLE_WEIGHT * title_score
            + SKILLS_WEIGHT * skills_score
        )

        skills = parse_skills_lower(
            metadata_row.get("skills_normalized", "")
        )

        rows.append(
            {
                "source_name": source_name,
                "row_idx": row_idx,

                "semantic_score": semantic_score,
                "base_score": semantic_score,
                "final_score": semantic_score,

                "title_vector_score": title_score,
                "skills_vector_score": skills_score,

                "job_title_canonical": metadata_row.get("title_core", ""),
                "skills_canonical": skills,
                "job_count": 1,
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return (
        result
        .sort_values("final_score", ascending=False)
        .reset_index(drop=True)
    )


def limit_candidates_by_source(
    candidates_df: pd.DataFrame,
    source_limits: dict[str, int] | None = None,
) -> pd.DataFrame:
    # Giữ top candidates theo từng source
    if source_limits is None:
        source_limits = SOURCE_TOP_K

    if candidates_df.empty:
        return candidates_df

    frames = []

    for source_name, limit in source_limits.items():
        source_df = candidates_df[
            candidates_df["source_name"] == source_name
        ].copy()

        if source_df.empty:
            continue

        source_df = (
            source_df
            .sort_values("semantic_score", ascending=False)
            .head(limit)
        )

        frames.append(source_df)

    if not frames:
        return pd.DataFrame()

    return (
        pd.concat(frames, ignore_index=True)
        .sort_values("final_score", ascending=False)
        .reset_index(drop=True)
    )


def recommend_missing_skills(
    recommended_jobs: pd.DataFrame,
    user_skills: list[str],
    top_n: int = 10,
) -> pd.DataFrame:
    # Lấy skills còn thiếu từ các job liên quan
    user_skill_set = {
        normalize_token(skill)
        for skill in user_skills
        if normalize_token(skill)
    }

    skill_scores = defaultdict(float)
    skill_counts = defaultdict(int)
    skill_names = {}

    for _, row in recommended_jobs.iterrows():
        job_score = float(row.get("base_score", 0.0))
        job_skills = parse_skills_lower(
            row.get("skills_canonical", [])
        )

        for skill in job_skills:
            skill_key = normalize_token(skill)

            if not skill_key:
                continue

            if skill_key in user_skill_set:
                continue

            skill_scores[skill_key] += job_score
            skill_counts[skill_key] += 1
            skill_names[skill_key] = skill

    rows = []

    for skill_key, score in skill_scores.items():
        rows.append(
            {
                "skill": skill_names[skill_key],
                "recommend_score": score,
                "job_count": skill_counts[skill_key],
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return (
        result
        .sort_values(
            ["recommend_score", "job_count"],
            ascending=False,
        )
        .head(top_n)
        .reset_index(drop=True)
    )