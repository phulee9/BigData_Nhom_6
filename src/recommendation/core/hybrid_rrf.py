from __future__ import annotations
from collections import defaultdict
import pandas as pd

def reciprocal_rank_fusion(
    bm25_skills: list[dict],
    emb_skills: list[dict] | pd.DataFrame,
    k: int = 60,
    top_k: int = 10,
) -> list[dict]:
    
    # List[dict] với keys: skill, rrf_score, bm25_rank, emb_rank, job_count
    
    if isinstance(emb_skills, pd.DataFrame):
        emb_list = emb_skills.to_dict("records") if not emb_skills.empty else []
    else:
        emb_list = emb_skills or []

    bm25_list = bm25_skills or []

    rrf_scores: dict[str, float] = defaultdict(float)
    bm25_ranks: dict[str, int] = {}
    emb_ranks: dict[str, int] = {}
    job_counts: dict[str, int] = {}

    for rank, item in enumerate(bm25_list, start=1):
        skill = item["skill"]
        rrf_scores[skill] += 1.0 / (k + rank)
        bm25_ranks[skill] = rank
        job_counts[skill] = item.get("job_count", 0)

    for rank, item in enumerate(emb_list, start=1):
        skill = item["skill"]
        rrf_scores[skill] += 1.0 / (k + rank)
        emb_ranks[skill] = rank
        emb_count = item.get("job_count", 0)
        if emb_count > job_counts.get(skill, 0):
            job_counts[skill] = emb_count

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
