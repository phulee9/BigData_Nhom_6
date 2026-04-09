import pickle
import pandas as pd
from collections import Counter
from pathlib import Path
from skill_config import is_valid_skill

BASE_DIR  = Path(__file__).parent.parent / "data"
META_FILE = BASE_DIR / "job_metadata.pkl"


def load_metadata() -> pd.DataFrame:
    with open(META_FILE, "rb") as f:
        return pickle.load(f)


def skill_gap_roadmap(
    cv_skills: list,
    job_title: str,
    df: pd.DataFrame,
    top_n: int = 5
) -> dict:
    cv_set  = set(s.lower().strip() for s in cv_skills)
    pattern = job_title.lower().strip()

    # Tìm jobs theo title, fallback fuzzy nếu không có kết quả
    target_jobs = df[df["job_title"].str.contains(pattern, case=False, na=False)]

    if target_jobs.empty:
        words = [w for w in pattern.split() if len(w) > 2]
        if words:
            mask = df["job_title"].str.contains("|".join(words), case=False, na=False)
            target_jobs = df[mask]

    total = len(target_jobs)

    if total == 0:
        return {
            "job_title"  : job_title,
            "total_jobs" : 0,
            "cv_skills"  : list(cv_set),
            "must_have"  : [],
            "should_have": [],
            "nice_have"  : [],
            "error"      : f"Khong tim thay '{job_title}' trong du lieu!"
        }

    # Đếm tần suất và tính phần trăm skill
    skill_freq = Counter()
    for _, row in target_jobs.iterrows():
        skills = [
            s.strip().lower()
            for s in row["job_skills"].split(", ")
            if s.strip() and is_valid_skill(s.strip())
        ]
        skill_freq.update(skills)

    skill_pct = {s: round(c / total * 100, 1) for s, c in skill_freq.items()}

    # Xác định ngưỡng động theo phân vị
    pct_values = sorted(skill_pct.values(), reverse=True)
    if len(pct_values) >= 3:
        high_threshold = pct_values[min(5,  len(pct_values) - 1)]
        mid_threshold  = pct_values[min(15, len(pct_values) - 1)]
    else:
        high_threshold = 30
        mid_threshold  = 15

    # Phân loại skills theo mức độ ưu tiên
    must_have, should_have, nice_have = [], [], []

    for skill, pct in sorted(skill_pct.items(), key=lambda x: -x[1]):
        if skill in cv_set:
            continue
        if pct >= high_threshold:
            must_have.append({"skill": skill, "pct": pct})
        elif pct >= mid_threshold:
            should_have.append({"skill": skill, "pct": pct})
        elif pct >= 5:
            nice_have.append({"skill": skill, "pct": pct})

    return {
        "job_title"  : job_title,
        "total_jobs" : total,
        "cv_skills"  : list(cv_set),
        "must_have"  : must_have[:top_n],
        "should_have": should_have[:top_n],
        "nice_have"  : nice_have[:top_n],
    }


def print_roadmap(result: dict):
    LINE = "=" * 50

    if result.get("error"):
        print(f"\n[!] {result['error']}")
        return

    print(f"\n{LINE}")
    print("  LO TRINH HOC SKILLS")
    print(LINE)
    print(f"  Job title : {result['job_title']}")
    print(f"  Tong jobs : {result['total_jobs']:,} jobs phan tich")

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