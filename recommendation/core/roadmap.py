import numpy as np
import pandas as pd
from collections import Counter
from pathlib import Path
from skill_config import is_valid_skill, normalize_skill
from recommend import model, clean_query, search_index


BASE_DIR = Path(__file__).parent.parent / "data"


def skill_gap_roadmap(
    cv_skills:  list,
    job_title:  str,
    df_old:     pd.DataFrame,
    index_old,
    top_n:      int   = 5,
    index_new         = None,
    df_new            = None,
    w_old:      float = 0.6,
    w_new:      float = 0.4
) -> dict:
    cv_set = set(normalize_skill(s.lower().strip()) for s in cv_skills)

    # Encode query = job_title + cv_skills (giong recommend.py)
    query        = job_title + " " + " ".join(cv_set)
    query_vector = model.encode(
        [clean_query(query)], normalize_embeddings=True
    ).astype("float32")

    # Tim jobs tu index cu, lay tat ca sau filter theo title
    candidates_old = search_index(
        query_vector, index_old, df_old, job_title, k=200
    )
    total_old = len(candidates_old)

    # Tim jobs tu index moi neu co, lay tat ca sau filter theo title
    candidates_new = pd.DataFrame()
    total_new      = 0

    if index_new is not None and df_new is not None and len(df_new) > 0:
        k_new          = min(200, len(df_new))
        candidates_new = search_index(
            query_vector, index_new, df_new, job_title, k=k_new
        )
        total_new = len(candidates_new)

    # TH4: ca 2 deu khong co job -> tra ve error
    if total_old == 0 and total_new == 0:
        return {
            "job_title"  : job_title,
            "total_jobs" : 0,
            "total_old"  : 0,
            "total_new"  : 0,
            "cv_skills"  : list(cv_set),
            "must_have"  : [],
            "should_have": [],
            "nice_have"  : [],
            "error"      : f"Khong tim thay '{job_title}' trong du lieu!"
        }

    # Dem tan suat skills tu index cu
    skill_freq_old = Counter()
    if total_old > 0:
        for _, row in candidates_old.iterrows():
            skills = []
            for s in row["job_skills"].split(", "):
                s_norm = normalize_skill(s.strip().lower())
                if s_norm and is_valid_skill(s_norm):
                    skills.append(s_norm)
            skill_freq_old.update(skills)

    # Dem tan suat skills tu index moi
    skill_freq_new = Counter()
    if total_new > 0:
        for _, row in candidates_new.iterrows():
            skills = []
            for s in row["job_skills"].split(", "):
                s_norm = normalize_skill(s.strip().lower())
                if s_norm and is_valid_skill(s_norm):
                    skills.append(s_norm)
            skill_freq_new.update(skills)

    # Tinh % rieng tung nguon
    skill_pct_old = {s: c / total_old for s, c in skill_freq_old.items()} \
        if total_old > 0 else {}
    skill_pct_new = {s: c / total_new for s, c in skill_freq_new.items()} \
        if total_new > 0 else {}

    # Merge co trong so giong recommend.py — 4 truong hop
    all_skills  = set(skill_pct_old) | set(skill_pct_new)
    skill_score = {}

    for skill in all_skills:
        if skill in cv_set:
            continue

        pct_old = skill_pct_old.get(skill, 0)
        pct_new = skill_pct_new.get(skill, 0)

        if total_old > 0 and total_new > 0:
            # TH1: ca 2 co job -> merge co trong so
            if pct_old > 0 and pct_new > 0:
                skill_score[skill] = w_old * pct_old + w_new * pct_new
            elif pct_new > 0:
                # Chi xuat hien o index moi -> giam trong so
                skill_score[skill] = w_new * pct_new * 0.5
            else:
                # Chi xuat hien o index cu
                skill_score[skill] = w_old * pct_old

        elif total_old > 0:
            # TH2: chi co index cu -> dung 100% index cu
            skill_score[skill] = pct_old

        else:
            # TH3: chi co index moi -> dung 100% index moi
            skill_score[skill] = pct_new

    # Xac dinh nguong dong theo phan vi
    score_values = sorted(skill_score.values(), reverse=True)
    if len(score_values) >= 3:
        high_threshold = score_values[min(5,  len(score_values) - 1)]
        mid_threshold  = score_values[min(15, len(score_values) - 1)]
    else:
        high_threshold = 0.30
        mid_threshold  = 0.15

    # Phan loai skills theo muc do uu tien
    must_have, should_have, nice_have = [], [], []

    for skill, score in sorted(skill_score.items(), key=lambda x: -x[1]):
        pct = round(score * 100, 1)
        if score >= high_threshold:
            must_have.append({"skill": skill, "pct": pct})
        elif score >= mid_threshold:
            should_have.append({"skill": skill, "pct": pct})
        elif score >= 0.05:
            nice_have.append({"skill": skill, "pct": pct})

    return {
        "job_title"  : job_title,
        "total_jobs" : total_old + total_new,
        "total_old"  : total_old,
        "total_new"  : total_new,
        "cv_skills"  : list(cv_set),
        "must_have"  : must_have[:top_n],
        "should_have": should_have[:top_n],
        "nice_have"  : nice_have[:top_n],
    }


def print_roadmap(result: dict):
    LINE  = "=" * 50
    t_old = result.get("total_old", 0)
    t_new = result.get("total_new", 0)
    total = result.get("total_jobs", 0)

    if result.get("error"):
        print(f"\n[!] {result['error']}")
        return

    print(f"\n{LINE}")
    print("  LO TRINH HOC SKILLS")
    print(LINE)
    print(f"  Job title : {result['job_title']}")
    print(f"  Tong jobs : {total:,} ({t_old} cu + {t_new} moi)")

    print(f"\n  Skills da co:")
    for s in result["cv_skills"]:
        print(f"    v {s}")

    print(f"\n  BUOC 1 - MUST HAVE (bat buoc):")
    if result["must_have"]:
        for i, item in enumerate(result["must_have"], 1):
            print(f"    {i}. {item['skill']} ({item['pct']}% jobs yeu cau)")
    else:
        print("    Da co du skills bat buoc!")

    print(f"\n  BUOC 2 - SHOULD HAVE (nen co):")
    if result["should_have"]:
        for i, item in enumerate(result["should_have"], 1):
            print(f"    {i}. {item['skill']} ({item['pct']}% jobs yeu cau)")
    else:
        print("    Khong co skills can bo sung!")

    print(f"\n  BUOC 3 - NICE TO HAVE (them diem):")
    if result["nice_have"]:
        for i, item in enumerate(result["nice_have"], 1):
            print(f"    {i}. {item['skill']} ({item['pct']}% jobs yeu cau)")
    else:
        print("    Khong co!")

    print(LINE)