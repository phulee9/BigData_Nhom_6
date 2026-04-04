import pickle
import pandas as pd
from collections import Counter
from pathlib import Path
from skill_config import is_valid_skill

BASE_DIR = Path(__file__).parent

def load_metadata() -> pd.DataFrame:
    with open(BASE_DIR / "job_metadata.pkl", "rb") as f:
        df = pickle.load(f)
    return df

def get_top_skills(
    job_title: str,
    df:        pd.DataFrame,
    top_n:     int = 20
) -> dict:
    pattern     = job_title.lower().strip()
    target_jobs = df[
        df["job_title"].str.contains(pattern, case=False, na=False)
    ]

    if target_jobs.empty:
        words = [w for w in pattern.split() if len(w) > 2]
        if words:
            mask = df["job_title"].str.contains(
                "|".join(words), case=False, na=False
            )
            target_jobs = df[mask]

    total = len(target_jobs)
    if total == 0:
        return {}

    skill_freq = Counter()
    for _, row in target_jobs.iterrows():
        skills = [
            s.strip().lower()
            for s in row["job_skills"].split(", ")
            if s.strip() and is_valid_skill(s.strip())
        ]
        skill_freq.update(skills)

    return {
        s: round(c / total * 100, 1)
        for s, c in skill_freq.most_common(top_n)
    }

def career_switch_analysis(
    job_from:  str,
    job_to:    str,
    cv_skills: list,
    df:        pd.DataFrame,
    top_n:     int = 20
) -> dict:

    cv_set = set(s.lower().strip() for s in cv_skills)

    skills_from = get_top_skills(job_from, df, top_n)
    skills_to   = get_top_skills(job_to,   df, top_n)

    if not skills_from:
        return {"error": f"Khong tim thay '{job_from}'!"}
    if not skills_to:
        return {"error": f"Khong tim thay '{job_to}'!"}

    set_from = set(skills_from.keys())
    set_to   = set(skills_to.keys())

    # Skills chung
    common   = set_from & set_to

    # Skills chỉ của vị trí đích
    only_to  = set_to - set_from

    # Skills cần học (vị trí đích mà CV chưa có)
    need_to_learn = {
        s: skills_to[s]
        for s in set_to
        if s not in cv_set
    }

    need_to_learn_sorted = sorted(
        need_to_learn.items(), key=lambda x: -x[1]
    )
    common_sorted = sorted(
        [(s, skills_to.get(s, 0)) for s in common],
        key=lambda x: -x[1]
    )
    only_to_sorted = sorted(
        [(s, skills_to[s]) for s in only_to],
        key=lambda x: -x[1]
    )

    # CV match với vị trí đích
    cv_match = {
        s: skills_to[s]
        for s in set_to
        if s in cv_set
    }
    match_pct = round(
        len(cv_match) / len(set_to) * 100, 1
    ) if set_to else 0

    return {
        "job_from"      : job_from,
        "job_to"        : job_to,
        "cv_skills"     : list(cv_set),
        "match_pct"     : match_pct,
        "cv_match"      : sorted(cv_match.items(),
                                  key=lambda x: -x[1])[:10],
        "common_skills" : common_sorted[:10],
        "only_to_skills": only_to_sorted[:10],
        "need_to_learn" : need_to_learn_sorted[:10],
    }

def print_career_switch(result: dict):
    LINE = "=" * 50

    if result.get("error"):
        print(f"\n[!] {result['error']}")
        return

    print(f"\n{LINE}")
    print("  PHAN TICH CHUYEN HUONG NGHE NGHIEP")
    print(LINE)
    print(f"  Tu    : {result['job_from']}")
    print(f"  Sang  : {result['job_to']}")
    print(f"  Match : {result['match_pct']}% skills phu hop")

    print(f"\n  Skills CV da co phu hop voi {result['job_to']}:")
    if result["cv_match"]:
        for s, pct in result["cv_match"]:
            print(f"    v {s} ({pct}% jobs yeu cau)")
    else:
        print("    → Chua co skills nao phu hop!")

    print(f"\n  Skills chung cua ca 2 vi tri:")
    for s, pct in result["common_skills"][:5]:
        print(f"    = {s} ({pct}% jobs yeu cau)")

    print(f"\n  Skills dac trung cua {result['job_to']}:")
    for s, pct in result["only_to_skills"][:5]:
        print(f"    ! {s} ({pct}% jobs yeu cau)")

    print(f"\n  Ban can hoc them de chuyen sang {result['job_to']}:")
    if result["need_to_learn"]:
        for i, (s, pct) in enumerate(result["need_to_learn"], 1):
            print(f"    {i}. {s} ({pct}% jobs yeu cau)")
    else:
        print("    → Ban da co du skills!")

    print(LINE)