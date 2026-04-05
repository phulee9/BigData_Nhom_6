import os, re, pickle, nltk
import numpy as np
import pandas as pd
import faiss
from collections import Counter
from sentence_transformers import SentenceTransformer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from dotenv import load_dotenv
from pathlib import Path
from skill_config import normalize_skill, is_valid_skill

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_DIR   = Path(__file__).parent
INDEX_FILE = BASE_DIR / "faiss_index.bin"
META_FILE  = BASE_DIR / "job_metadata.pkl"

# ── Setup NLP ──────────────────────────────────────────
for pkg in ["wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(f"corpora/{pkg}")
    except:
        nltk.download(pkg, quiet=True)

lemmatizer = WordNetLemmatizer()
STOP_WORDS  = set(stopwords.words("english"))

def clean_query(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text   = text.lower()
    text   = re.sub(r"[^\w\s]", " ", text)
    text   = re.sub(r"\s+", " ", text).strip()
    tokens = [w for w in text.split() if w not in STOP_WORDS]
    return " ".join(lemmatizer.lemmatize(w) for w in tokens)

# ── Load model ─────────────────────────────────────────
print("⏳ Load Sentence Transformer...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("✓ Model ready!")

# ── Load FAISS ─────────────────────────────────────────
def load_index():
    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"\n[LOI] Khong tim thay: {INDEX_FILE}"
        )
    if not META_FILE.exists():
        raise FileNotFoundError(
            f"\n[LOI] Khong tim thay: {META_FILE}"
        )
    print("⏳ Load FAISS index...")
    index = faiss.read_index(str(INDEX_FILE))
    with open(META_FILE, "rb") as f:
        df = pickle.load(f)
    print(f"✓ {index.ntotal:,} vectors | {len(df):,} jobs")
    return index, df

# ── Recommend ──────────────────────────────────────────
def recommend_skills(
    cv_skills:  list,
    job_title:  str,
    index,
    df:         pd.DataFrame,
    top_k:      int = 150,
    top_skills: int = 10
) -> dict:

    # Normalize CV skills
    cv_skills_clean = [
        normalize_skill(s.lower().strip())
        for s in cv_skills
    ]

    # ── Bước 1: Encode query = job_title + cv_skills ──
    # Giống format index: title_skills = job_title + job_skills
    query       = job_title + " " + " ".join(cv_skills_clean)
    query_clean = clean_query(query)

    title_vector = model.encode(
        [query_clean], normalize_embeddings=True
    ).astype("float32")

    # ── Bước 2: FAISS search 812K → top 200 ───────────
    scores, indices = index.search(title_vector, k=200)

    candidate_jobs          = df.iloc[indices[0]].copy()
    candidate_jobs["score"] = scores[0]

    # ── Bước 3: Filter theo title trong 200 jobs ──────
    keywords = [
        w for w in job_title.lower().split()
        if len(w) > 2
    ]

    if keywords:
        pattern  = "|".join(keywords)
        mask     = candidate_jobs["job_title"].str.contains(
            pattern, case=False, na=False
        )
        filtered = candidate_jobs[mask]
    else:
        filtered = candidate_jobs

    # Nếu filter quá ít → dùng toàn bộ 200
    if len(filtered) < 30:
        print(f"  [!] Chi co {len(filtered)} jobs sau filter"
              f", dung toan bo 200 jobs")
        filtered = candidate_jobs

    # Lấy top_k
    candidate_jobs   = filtered.head(top_k)
    total_candidates = len(candidate_jobs)

    print(f"  Jobs sau filter: {total_candidates}")

    # ── Bước 4: Content-Based Filtering ───────────────
    user_skills_set = set(cv_skills_clean)
    missing = []

    for _, row in candidate_jobs.iterrows():
        job_skills = set(
            normalize_skill(s)
            for s in row["job_skills"].lower().split(", ")
            if s.strip() and is_valid_skill(normalize_skill(s.strip()))
        )
        missing += list(job_skills - user_skills_set)

    skill_counts = Counter(missing).most_common(top_skills)

    return {
        "vi_tri_ung_tuyen":    job_title,
        "job_titles_gan_nhat": candidate_jobs["job_title"] \
                                             .unique()[:3].tolist(),
        "top_scores":          candidate_jobs["score"] \
                                             .head(3).tolist(),
        "skills_da_co":        cv_skills_clean,
        "total_candidates":    total_candidates,
        "skills_goi_y": [
            {"skill": s, "count": c}
            for s, c in skill_counts
        ]
    }

# ── In kết quả ─────────────────────────────────────────
def print_recommendation(result: dict):
    LINE  = "=" * 50
    total = result.get("total_candidates", 150)

    print(f"\n{LINE}")
    print("  KET QUA GOI Y SKILLS")
    print(LINE)
    print(f"  Vi tri : {result['vi_tri_ung_tuyen']}")

    print(f"\n  Job titles gan nhat:")
    for i, (t, s) in enumerate(
        zip(result["job_titles_gan_nhat"],
            result["top_scores"]), 1
    ):
        print(f"    {i}. {t} (do tuong dong: {s:.2f})")

    print(f"\n  Skills da co ({len(result['skills_da_co'])}):")
    for s in result["skills_da_co"]:
        print(f"    v {s}")

    print(f"\n  Skills nen hoc them:")
    for i, item in enumerate(result["skills_goi_y"], 1):
        print(f"    {i}. {item['skill']}"
              f" (xuat hien trong {item['count']}/{total} job tuong tu)")
    print(LINE)