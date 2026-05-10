import ast
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.config import (
    EMBEDDING_MODEL,
    NORMALIZE_EMBEDDINGS,
)
from src.recommendation.core.loader import (
    RuntimeIndex,
    load_runtime_index,
)



# Runtime index paths


DEFAULT_KAGGLE_RUNTIME_DIR = Path("data/runtime_index/kaggle")
DEFAULT_CRAWLER_RUNTIME_DIR = Path("data/runtime_index/crawler")



# Recommendation configuration


# Lấy 300 job từ index cũ Kaggle, 50 job từ index mới Crawler
SOURCE_TOP_K = {
    "kaggle": 300,
    "crawler": 50,
}

# Trọng số nguồn cho ranking job
SOURCE_WEIGHTS = {
    "kaggle": 0.45,
    "crawler": 0.55,
}

# Trọng số nguồn riêng cho gợi ý missing skills
SKILL_SOURCE_WEIGHTS = {
    "kaggle": 0.40,
    "crawler": 0.60,
}

# Trọng số 3 index vector
INDEX_WEIGHTS = {
    "title_score": 0.30,
    "skills_score": 0.30,
    "full_score": 0.40,
}

# Trọng số rerank
RERANK_WEIGHTS = {
    "semantic_score": 0.45,
    "title_fuzzy_score": 0.20,
    "skill_overlap_score": 0.25,
    "location_score": 0.10,
}


# Text and skill utilities

def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_token(value: Any) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def parse_skills(value: Any) -> list[str]:
    """
    Chuyển skills về list Python.

    Hỗ trợ:
    - list
    - numpy array
    - tuple/set
    - string dạng "SQL, Power BI, Excel"
    - string dạng "['SQL', 'Power BI']"
    """
    if value is None:
        return []

    if isinstance(value, float) and pd.isna(value):
        return []

    if isinstance(value, list):
        return [
            normalize_text(skill)
            for skill in value
            if normalize_text(skill)
        ]

    if isinstance(value, np.ndarray):
        return [
            normalize_text(skill)
            for skill in value.tolist()
            if normalize_text(skill)
        ]

    if isinstance(value, (tuple, set)):
        return [
            normalize_text(skill)
            for skill in list(value)
            if normalize_text(skill)
        ]

    if isinstance(value, str):
        text = value.strip()

        if text.lower() in ["", "[]", "nan", "none", "null"]:
            return []

        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, list):
                return [
                    normalize_text(skill)
                    for skill in parsed
                    if normalize_text(skill)
                ]

            if isinstance(parsed, (tuple, set)):
                return [
                    normalize_text(skill)
                    for skill in list(parsed)
                    if normalize_text(skill)
                ]

        except Exception:
            pass

        if "," in text:
            return [
                item.strip()
                for item in text.split(",")
                if item.strip()
            ]

        return [text]

    return []


def skills_to_text(skills: list[str]) -> str:
    clean_skills = [
        normalize_text(skill)
        for skill in skills
        if normalize_text(skill)
    ]

    if not clean_skills:
        return "Not specified"

    return ", ".join(clean_skills)


def build_query_texts(
    job_title: str,
    skills: list[str],
    location: str,
) -> dict[str, str]:
    """
    Build input text đúng format với Gold Encode:

    title_text:
    Job title: Data Analyst.

    skills_text:
    Required skills: SQL, Power BI, Excel.

    full_text:
    Job title: Data Analyst. Location: Ho Chi Minh, Vietnam. Required skills: SQL, Power BI, Excel.
    """
    job_title = normalize_text(job_title) or "Not specified"
    location = normalize_text(location) or "Unknown"
    skills_text = skills_to_text(skills)

    return {
        "title_text": f"Job title: {job_title}.",
        "skills_text": f"Required skills: {skills_text}.",
        "full_text": (
            f"Job title: {job_title}. "
            f"Location: {location}. "
            f"Required skills: {skills_text}."
        ),
    }



# FAISS search utilities

def encode_query(
    model: SentenceTransformer,
    text: str,
) -> np.ndarray:
    embedding = model.encode(
        [text],
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")

    return embedding


def search_faiss_index(
    index,
    query_embedding: np.ndarray,
    top_k: int,
) -> list[tuple[int, float]]:
    scores, indices = index.search(
        query_embedding,
        top_k,
    )

    results = []

    for idx, score in zip(indices[0], scores[0]):
        if idx < 0:
            continue

        results.append(
            (int(idx), float(score))
        )

    return results


# Rerank score utilities

def safe_score(value: Any) -> float:
    if value is None:
        return 0.0

    try:
        value = float(value)
    except Exception:
        return 0.0

    if math.isnan(value):
        return 0.0

    return value


def text_similarity(a: str, b: str) -> float:
    """
    Fuzzy score đơn giản theo token overlap.

    Ví dụ:
    Data Analyst vs Senior Data Analyst sẽ ra điểm cao.
    """
    a = normalize_token(a)
    b = normalize_token(b)

    if not a or not b:
        return 0.0

    a_tokens = set(a.split())
    b_tokens = set(b.split())

    if not a_tokens or not b_tokens:
        return 0.0

    intersection = a_tokens.intersection(b_tokens)
    union = a_tokens.union(b_tokens)

    jaccard = len(intersection) / len(union)
    containment = len(intersection) / max(len(a_tokens), 1)

    return max(jaccard, containment)


def skill_overlap_score(
    user_skills: list[str],
    job_skills: list[str],
) -> float:
    user_set = {
        normalize_token(skill)
        for skill in user_skills
        if normalize_token(skill)
    }

    job_set = {
        normalize_token(skill)
        for skill in job_skills
        if normalize_token(skill)
    }

    if not user_set or not job_set:
        return 0.0

    intersection = user_set.intersection(job_set)

    return len(intersection) / len(user_set)


def location_score(
    user_location: str,
    job_location: str,
) -> float:
    user_location = normalize_token(user_location)
    job_location = normalize_token(job_location)

    if not user_location:
        return 0.0

    if not job_location or job_location == "unknown":
        return 0.0

    if user_location == job_location:
        return 1.0

    if user_location in job_location or job_location in user_location:
        return 0.8

    user_parts = set(user_location.split())
    job_parts = set(job_location.split())

    if not user_parts or not job_parts:
        return 0.0

    overlap = user_parts.intersection(job_parts)

    if overlap:
        return min(
            0.6,
            len(overlap) / max(len(user_parts), 1),
        )

    return 0.0


# Load runtime indexes

def load_default_runtime_indexes() -> list[RuntimeIndex]:
    """
    Luôn cố gắng load cả 2 index:
    - Kaggle: index cũ
    - Crawler: index mới

    Nếu một nguồn chưa có folder thì bỏ qua nguồn đó.
    Nhưng nếu không có nguồn nào thì báo lỗi.
    """
    runtime_indexes = []

    if DEFAULT_KAGGLE_RUNTIME_DIR.exists():
        runtime_indexes.append(
            load_runtime_index(
                source_name="kaggle",
                runtime_dir=DEFAULT_KAGGLE_RUNTIME_DIR,
                source_weight=SOURCE_WEIGHTS["kaggle"],
            )
        )
    else:
        print(f"Bỏ qua Kaggle vì chưa có folder: {DEFAULT_KAGGLE_RUNTIME_DIR}")

    if DEFAULT_CRAWLER_RUNTIME_DIR.exists():
        runtime_indexes.append(
            load_runtime_index(
                source_name="crawler",
                runtime_dir=DEFAULT_CRAWLER_RUNTIME_DIR,
                source_weight=SOURCE_WEIGHTS["crawler"],
            )
        )
    else:
        print(f"Bỏ qua Crawler vì chưa có folder: {DEFAULT_CRAWLER_RUNTIME_DIR}")

    if not runtime_indexes:
        raise FileNotFoundError(
            "Không tìm thấy runtime index nào. "
            "Cần có data/runtime_index/kaggle hoặc data/runtime_index/crawler."
        )

    return runtime_indexes


# Candidate retrieval

def collect_candidates_from_source(
    runtime_index: RuntimeIndex,
    query_embeddings: dict[str, np.ndarray],
    top_k_each_index: int,
) -> dict[tuple[str, int], dict[str, Any]]:
    """
    Search 3 indexes trong cùng một source:
    - title_index
    - skills_index
    - full_index

    Candidate có thể xuất hiện trong nhiều index.
    Nếu trùng, giữ score cao nhất cho từng loại score.
    """
    source_name = runtime_index.source_name

    candidates: dict[tuple[str, int], dict[str, Any]] = {}

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
        (
            "full_score",
            runtime_index.full_index,
            query_embeddings["full_text"],
        ),
    ]

    for score_name, index, embedding in search_plan:
        search_results = search_faiss_index(
            index=index,
            query_embedding=embedding,
            top_k=top_k_each_index,
        )

        for row_idx, score in search_results:
            key = (source_name, row_idx)

            if key not in candidates:
                candidates[key] = {
                    "source_name": source_name,
                    "source_weight": runtime_index.source_weight,
                    "row_idx": row_idx,
                    "title_score": 0.0,
                    "skills_score": 0.0,
                    "full_score": 0.0,
                }

            candidates[key][score_name] = max(
                candidates[key][score_name],
                float(score),
            )

    return candidates


def build_candidate_rows(
    candidates: dict[tuple[str, int], dict[str, Any]],
    runtime_indexes: list[RuntimeIndex],
    user_job_title: str,
    user_skills: list[str],
    user_location: str,
) -> pd.DataFrame:
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

        job_title = normalize_text(
            metadata_row.get("job_title_canonical", "")
        )

        job_location = normalize_text(
            metadata_row.get("location_final", "")
        )

        job_skills = parse_skills(
            metadata_row.get("skills_canonical", [])
        )

        title_vector_score = safe_score(candidate["title_score"])
        skills_vector_score = safe_score(candidate["skills_score"])
        full_vector_score = safe_score(candidate["full_score"])

        semantic_score = (
            INDEX_WEIGHTS["title_score"] * title_vector_score
            + INDEX_WEIGHTS["skills_score"] * skills_vector_score
            + INDEX_WEIGHTS["full_score"] * full_vector_score
        )

        title_fuzzy = text_similarity(
            user_job_title,
            job_title,
        )

        skill_overlap = skill_overlap_score(
            user_skills,
            job_skills,
        )

        loc_score = location_score(
            user_location,
            job_location,
        )

        base_score = (
            RERANK_WEIGHTS["semantic_score"] * semantic_score
            + RERANK_WEIGHTS["title_fuzzy_score"] * title_fuzzy
            + RERANK_WEIGHTS["skill_overlap_score"] * skill_overlap
            + RERANK_WEIGHTS["location_score"] * loc_score
        )

        source_weight = safe_score(candidate["source_weight"])
        final_score = base_score * source_weight

        rows.append(
            {
                "source_name": source_name,
                "source_weight": source_weight,
                "row_idx": row_idx,

                "final_score": final_score,
                "base_score": base_score,
                "semantic_score": semantic_score,

                "title_vector_score": title_vector_score,
                "skills_vector_score": skills_vector_score,
                "full_vector_score": full_vector_score,

                "title_fuzzy_score": title_fuzzy,
                "skill_overlap_score": skill_overlap,
                "location_score": loc_score,

                "source_job_id": metadata_row.get("source_job_id", ""),
                "company": metadata_row.get("company", ""),
                "job_title_canonical": job_title,
                "occupation_group_final": metadata_row.get("occupation_group_final", ""),
                "occupation_family_final": metadata_row.get("occupation_family_final", ""),
                "seniority": metadata_row.get("seniority", ""),
                "city_clean": metadata_row.get("city_clean", ""),
                "country_clean": metadata_row.get("country_clean", ""),
                "location_final": job_location,
                "skills_canonical": job_skills,
                "skills_count_final": metadata_row.get("skills_count_final", 0),
                "job_url": metadata_row.get("job_url", ""),
                "job_link": metadata_row.get("job_link", ""),
                "crawl_batch": metadata_row.get("crawl_batch", ""),
            }
        )

    result_df = pd.DataFrame(rows)

    if result_df.empty:
        return result_df

    result_df = result_df.sort_values(
        by="final_score",
        ascending=False,
    ).reset_index(drop=True)

    return result_df


def limit_candidates_by_source(
    candidates_df: pd.DataFrame,
    source_limits: dict[str, int] | None = None,
) -> pd.DataFrame:
    """
    Giữ đúng số lượng candidates theo từng nguồn sau khi đã tính điểm:

    - Kaggle: Top 300
    - Crawler: Top 50

    Sort trong từng source theo semantic_score trước,
    vì đây là điểm vector retrieval ban đầu.
    Sau khi gộp lại, sort theo final_score để rerank.
    """
    if source_limits is None:
        source_limits = SOURCE_TOP_K

    if candidates_df.empty:
        return candidates_df

    limited_frames = []

    for source_name, limit in source_limits.items():
        source_df = candidates_df[
            candidates_df["source_name"] == source_name
        ].copy()

        if source_df.empty:
            continue

        source_df = source_df.sort_values(
            by="semantic_score",
            ascending=False,
        ).head(limit)

        limited_frames.append(source_df)

    if not limited_frames:
        return pd.DataFrame()

    result_df = pd.concat(
        limited_frames,
        ignore_index=True,
    )

    result_df = result_df.sort_values(
        by="final_score",
        ascending=False,
    ).reset_index(drop=True)

    return result_df


# Missing skills recommendation

def recommend_missing_skills(
    recommended_jobs: pd.DataFrame,
    user_skills: list[str],
    top_n: int = 10,
    skill_source_weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Gợi ý skills còn thiếu từ toàn bộ rerank pool.

    Không chỉ tính trên Top 10 job, mà tính trên toàn bộ 350 candidates.

    Score skill:
    skill_score += base_score_of_job * skill_source_weight
    """
    if skill_source_weights is None:
        skill_source_weights = SKILL_SOURCE_WEIGHTS

    user_skill_set = {
        normalize_token(skill)
        for skill in user_skills
        if normalize_token(skill)
    }

    skill_scores = defaultdict(float)
    skill_counts = defaultdict(int)
    skill_display_name = {}
    skill_source_counts = defaultdict(lambda: defaultdict(int))

    for _, row in recommended_jobs.iterrows():
        job_skills = parse_skills(
            row.get("skills_canonical", [])
        )

        source_name = str(row.get("source_name", "") or "").strip()

        # Dùng base_score để skill không bị nhân source_weight 2 lần
        job_base_score = safe_score(
            row.get("base_score", row.get("final_score", 0.0))
        )

        skill_source_weight = skill_source_weights.get(
            source_name,
            1.0,
        )

        weighted_job_score = job_base_score * skill_source_weight

        for skill in job_skills:
            skill_key = normalize_token(skill)

            if not skill_key:
                continue

            # Bỏ skill user đã có
            if skill_key in user_skill_set:
                continue

            skill_scores[skill_key] += weighted_job_score
            skill_counts[skill_key] += 1
            skill_display_name[skill_key] = skill
            skill_source_counts[skill_key][source_name] += 1

    rows = []

    for skill_key, total_score in skill_scores.items():
        source_count_dict = dict(skill_source_counts[skill_key])

        rows.append(
            {
                "skill": skill_display_name[skill_key],
                "recommend_score": total_score,
                "job_count": skill_counts[skill_key],
                "kaggle_count": source_count_dict.get("kaggle", 0),
                "crawler_count": source_count_dict.get("crawler", 0),
            }
        )

    skill_df = pd.DataFrame(rows)

    if skill_df.empty:
        return skill_df

    skill_df = skill_df.sort_values(
        by=["recommend_score", "job_count"],
        ascending=False,
    ).head(top_n).reset_index(drop=True)

    return skill_df


# Main recommendation function

def recommend_jobs(
    job_title: str,
    skills: list[str] | str,
    location: str,
    top_n_jobs: int = 10,
    top_n_skills: int = 10,
    source_top_k: dict[str, int] | None = None,
    skill_source_weights: dict[str, float] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Main recommend function.

    Logic:
    1. Parse input
    2. Build query text đúng format Gold
    3. Encode 3 query texts
    4. Search Kaggle index lấy Top 300
    5. Search Crawler index lấy Top 50
    6. Gộp thành tối đa 350 candidates
    7. Rerank 350 candidates
    8. Lấy Top 10 jobs
    9. Tính Top 10 missing skills từ toàn bộ 350 candidates
    """
    if source_top_k is None:
        source_top_k = SOURCE_TOP_K

    user_job_title = normalize_text(job_title)
    user_skills = parse_skills(skills)
    user_location = normalize_text(location)

    print("Input:")
    print(f"- Job title: {user_job_title}")
    print(f"- Skills: {user_skills}")
    print(f"- Location: {user_location}")

    query_texts = build_query_texts(
        job_title=user_job_title,
        skills=user_skills,
        location=user_location,
    )

    print("\nQuery texts:")
    print(query_texts)

    runtime_indexes = load_default_runtime_indexes()

    print("\nLoad embedding model")
    model = SentenceTransformer(EMBEDDING_MODEL)

    query_embeddings = {
        "title_text": encode_query(
            model=model,
            text=query_texts["title_text"],
        ),
        "skills_text": encode_query(
            model=model,
            text=query_texts["skills_text"],
        ),
        "full_text": encode_query(
            model=model,
            text=query_texts["full_text"],
        ),
    }

    all_candidates = {}

    for runtime in runtime_indexes:
        source_name = runtime.source_name
        top_k_for_source = source_top_k.get(source_name, 100)

        # Để tránh sau khi dedup không đủ 300/50,
        # search mỗi index nhiều hơn một chút.
        search_top_k_each_index = max(
            top_k_for_source * 2,
            top_k_for_source,
        )

        print(f"\nSearch source: {source_name}")
        print(f"Source weight: {runtime.source_weight}")
        print(f"Target Top K for source: {top_k_for_source}")
        print(f"Search Top K each FAISS index: {search_top_k_each_index}")

        source_candidates = collect_candidates_from_source(
            runtime_index=runtime,
            query_embeddings=query_embeddings,
            top_k_each_index=search_top_k_each_index,
        )

        print(f"Số candidates raw từ {source_name}: {len(source_candidates)}")

        all_candidates.update(source_candidates)

    all_jobs_df = build_candidate_rows(
        candidates=all_candidates,
        runtime_indexes=runtime_indexes,
        user_job_title=user_job_title,
        user_skills=user_skills,
        user_location=user_location,
    )

    if all_jobs_df.empty:
        return {
            "top_jobs": pd.DataFrame(),
            "missing_skills": pd.DataFrame(),
            "all_candidates": pd.DataFrame(),
            "rerank_pool": pd.DataFrame(),
        }

    # Giữ 300 Kaggle + 50 Crawler theo semantic_score
    rerank_pool_df = limit_candidates_by_source(
        candidates_df=all_jobs_df,
        source_limits=source_top_k,
    )

    print("\nRerank pool by source:")
    print(rerank_pool_df["source_name"].value_counts())
    print(f"Tổng số job trong rerank pool: {len(rerank_pool_df)}")

    # Top jobs lấy từ pool sau rerank
    top_jobs_df = rerank_pool_df.sort_values(
        by="final_score",
        ascending=False,
    ).head(top_n_jobs).copy()

    # Missing skills tính trên toàn bộ rerank pool, không chỉ Top 10 jobs
    missing_skills_df = recommend_missing_skills(
        recommended_jobs=rerank_pool_df,
        user_skills=user_skills,
        top_n=top_n_skills,
        skill_source_weights=skill_source_weights,
    )

    return {
        "top_jobs": top_jobs_df,
        "missing_skills": missing_skills_df,
        "all_candidates": all_jobs_df,
        "rerank_pool": rerank_pool_df,
    }