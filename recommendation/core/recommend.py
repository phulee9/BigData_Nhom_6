from collections import Counter, defaultdict

import numpy as np
from rapidfuzz import fuzz

from recommendation.core.preprocess import normalize_skill


def jaccard_score(a, b):
    a = set(a)
    b = set(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def location_score(query_location, job_location):
    query_location = str(query_location).lower().strip()
    job_location = str(job_location).lower().strip()

    if query_location == job_location:
        return 1.0

    if query_location == "remote" and job_location == "remote":
        return 1.0

    return 0.0


def title_score(query_title, job_title):
    return fuzz.token_set_ratio(query_title, job_title) / 100


def normalize_skill_set(skills):
    return set(
        normalize_skill(skill)
        for skill in skills
        if normalize_skill(skill)
    )


def recommend_from_cv_input(
    cv_input,
    index,
    metadata,
    model,
    retrieve_jobs=200,
    rerank_jobs=50,
    top_skills=10,
):
    title = cv_input.get("job_title", "")
    location = cv_input.get("location", "other")

    # Normalize lại skill user lần cuối để chống trùng kiểu node / node js / node.js
    current_skills = normalize_skill_set(cv_input.get("skills", []))

    if not title:
        raise ValueError("job_title rỗng sau khi clean")

    query = f"{title} in {location}"

    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.asarray(query_vec).astype("float32")

    scores, ids = index.search(query_vec, retrieve_jobs)

    candidates = []

    for semantic, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue

        item = metadata[idx]

        job_title = item.get("job_title", "")
        job_location = item.get("location", "other")

        # Normalize job skills trước khi tính overlap + recommend
        job_skills_norm = sorted(list(normalize_skill_set(item.get("skills", []))))

        semantic = float(semantic)
        title_sim = title_score(title, job_title)
        overlap_sim = jaccard_score(current_skills, job_skills_norm)
        location_sim = location_score(location, job_location)

        job_score = (
            0.50 * semantic
            + 0.25 * title_sim
            + 0.15 * overlap_sim
            + 0.10 * location_sim
        )

        candidates.append(
            {
                "job_title": job_title,
                "location": job_location,
                "skills": job_skills_norm,
                "score": round(job_score, 4),
                "semantic_score": round(semantic, 4),
                "title_score": round(title_sim, 4),
                "skill_overlap_score": round(overlap_sim, 4),
                "location_score": round(location_sim, 4),
            }
        )

    candidates = sorted(
        candidates,
        key=lambda x: x["score"],
        reverse=True,
    )[:rerank_jobs]

    top_jobs = [
        {
            "rank": i + 1,
            "job_title": job["job_title"],
            "location": job["location"],
            "score": job["score"],
        }
        for i, job in enumerate(candidates[:5])
    ]

    skill_weighted_scores = defaultdict(float)
    skill_freq = Counter()

    for job in candidates:
        for skill in job["skills"]:
            # skill ở đây đã normalize rồi, nhưng vẫn check lại cho chắc
            skill_norm = normalize_skill(skill)

            if not skill_norm:
                continue

            # Nếu user đã có node, thì node js/node.js/nodejs đều đã thành node và bị loại
            if skill_norm in current_skills:
                continue

            skill_weighted_scores[skill_norm] += job["score"]
            skill_freq[skill_norm] += 1

    max_weighted_score = max(skill_weighted_scores.values(), default=1.0)
    max_freq = max(skill_freq.values(), default=1)

    final_skill_scores = {}

    for skill in skill_weighted_scores:
        weighted_score_norm = skill_weighted_scores[skill] / max_weighted_score
        freq_score_norm = skill_freq[skill] / max_freq

        final_skill_scores[skill] = (
            0.80 * weighted_score_norm
            + 0.20 * freq_score_norm
        )

    ranked_skills = sorted(
        final_skill_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    top_missing_skills = []
    seen_skills = set()

    for skill, score in ranked_skills:
        skill_norm = normalize_skill(skill)

        if not skill_norm:
            continue

        if skill_norm in current_skills:
            continue

        if skill_norm in seen_skills:
            continue

        seen_skills.add(skill_norm)

        top_missing_skills.append(
            {
                "rank": len(top_missing_skills) + 1,
                "skill": skill_norm,
                "score": round(score, 4),
                "frequency": skill_freq[skill_norm],
            }
        )

        if len(top_missing_skills) >= top_skills:
            break

    return {
        "query": query,
        "top_5_similar_jobs": top_jobs,
        "top_10_missing_skills": top_missing_skills,
    }