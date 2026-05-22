"""
Hybrid RRF (Reciprocal Rank Fusion) — Kết hợp missing skills
từ BM25Plus (keyword) và Embedding (semantic).

RRF score cho mỗi skill:
    rrf_score = Σ 1 / (k + rank_i)

Skill xuất hiện ở cả 2 bên → score cao hơn.
Skill chỉ xuất hiện 1 bên → vẫn có score nhưng thấp hơn.
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd


def reciprocal_rank_fusion(
    bm25_skills: list[dict],
    emb_skills: list[dict] | pd.DataFrame,
    k: int = 60,
    top_k: int = 10,
) -> list[dict]:
    """
    Kết hợp 2 danh sách xếp hạng missing skills bằng RRF.

    Parameters:
        bm25_skills: Kết quả từ BM25PlusRecommender.query()
                     List[dict] với keys: skill, recommend_score, job_count
        emb_skills: Kết quả từ recommend_missing_skills()
                    DataFrame hoặc List[dict] với key: skill, recommend_score, job_count
        k: Hằng số RRF (mặc định 60, giá trị chuẩn trong literature)
        top_k: Số skills trả về

    Returns:
        List[dict] với keys: skill, rrf_score, bm25_rank, emb_rank, job_count
    """
    # Chuẩn hóa emb_skills về list[dict]
    if isinstance(emb_skills, pd.DataFrame):
        emb_list = emb_skills.to_dict("records") if not emb_skills.empty else []
    else:
        emb_list = emb_skills or []

    bm25_list = bm25_skills or []

    # Tính RRF score
    rrf_scores: dict[str, float] = defaultdict(float)
    bm25_ranks: dict[str, int] = {}
    emb_ranks: dict[str, int] = {}
    job_counts: dict[str, int] = {}

    # BM25 ranking
    for rank, item in enumerate(bm25_list, start=1):
        skill = item["skill"]
        rrf_scores[skill] += 1.0 / (k + rank)
        bm25_ranks[skill] = rank
        job_counts[skill] = item.get("job_count", 0)

    # Embedding ranking
    for rank, item in enumerate(emb_list, start=1):
        skill = item["skill"]
        rrf_scores[skill] += 1.0 / (k + rank)
        emb_ranks[skill] = rank
        # Giữ job_count lớn hơn
        emb_count = item.get("job_count", 0)
        if emb_count > job_counts.get(skill, 0):
            job_counts[skill] = emb_count

    # Build result
    results = [
        {
            "skill": skill,
            "rrf_score": score,
            "bm25_rank": bm25_ranks.get(skill, None),
            "emb_rank": emb_ranks.get(skill, None),
            "job_count": job_counts.get(skill, 0),
        }
        for skill, score in rrf_scores.items()
    ]

    results.sort(key=lambda x: x["rrf_score"], reverse=True)
    return results[:top_k]
