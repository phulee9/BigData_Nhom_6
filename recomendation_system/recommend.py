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

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

BASE_DIR = Path(__file__).parent

# ── Setup NLP ──────────────────────────────────────────
for pkg in ["wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(f"corpora/{pkg}")
    except:
        nltk.download(pkg, quiet=True)

lemmatizer = WordNetLemmatizer()
STOP_WORDS  = set(stopwords.words("english"))

# ── Normalize skill map ────────────────────────────────
SKILL_NORMALIZE = {
    # Node
    "node.js"    : "node",
    "nodejs"     : "node",
    "node js"    : "node",
    # React
    "react.js"   : "react",
    "reactjs"    : "react",
    # Vue
    "vue.js"     : "vue",
    "vuejs"      : "vue",
    # Next
    "next.js"    : "next",
    "nextjs"     : "next",
    # Nuxt
    "nuxt.js"    : "nuxt",
    "nuxtjs"     : "nuxt",
    # Express
    "express.js" : "express",
    "expressjs"  : "express",
    # Angular
    "angular.js" : "angular",
    "angularjs"  : "angular",
    # Nest
    "nest.js"    : "nestjs",
    # Jquery
    "jquery"     : "jquery",
    # Typescript
    "typescript" : "typescript",
    "ts"         : "typescript",
    # Javascript
    "javascript" : "javascript",
    "js"         : "javascript",
    # Python
    "python3"    : "python",
    "python 3"   : "python",
    # Database
    "postgresql" : "postgres",
    "mongo"      : "mongodb",
    "mongo db"   : "mongodb",
    # Cloud
    "amazon web services": "aws",
    "google cloud"       : "gcp",
    "microsoft azure"    : "azure",
    # REST
    "rest api"   : "restful apis",
    "rest apis"  : "restful apis",
    "restful"    : "restful apis",
    # CI/CD
    "ci/cd"      : "cicd",
    "ci cd"      : "cicd",
    # Machine Learning
    "machine learning": "machine learning",
    "ml"              : "machine learning",
    # Deep Learning
    "deep learning"   : "deep learning",
    "dl"              : "deep learning",
}

def normalize_skill(skill: str) -> str:
    """Normalize skill về dạng chuẩn"""
    s = skill.lower().strip()
    # Thử map trực tiếp
    if s in SKILL_NORMALIZE:
        return SKILL_NORMALIZE[s]
    # Thử bỏ dấu chấm rồi map
    s_no_dot = s.replace(".", "")
    if s_no_dot in SKILL_NORMALIZE:
        return SKILL_NORMALIZE[s_no_dot]
    return s

# ── Clean query ────────────────────────────────────────
def clean_query(text: str) -> str:
    """Clean nhẹ cho query khi recommend"""
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

# ── Load FAISS index + metadata ────────────────────────
def load_index():
    if not (BASE_DIR / "faiss_index.bin").exists():
        raise FileNotFoundError(
            "\n[LOI] Chua co FAISS index!"
            "\nChay: python spark_etl/silver_to_gold.py"
        )
    print("⏳ Load FAISS index...")
    index = faiss.read_index(str(BASE_DIR / "faiss_index.bin"))
    with open(BASE_DIR / "job_metadata.pkl", "rb") as f:
        df = pickle.load(f)
    print(f"✓ {index.ntotal:,} vectors | {len(df):,} jobs")
    return index, df

# ── Content-Based Filtering + Semantic Search ──────────
def recommend_skills(
    cv_skills:  list,
    job_title:  str,
    index,
    df:         pd.DataFrame,
    top_k:      int = 10,
    top_skills: int = 10
) -> dict:
    """
    Bước 1: Semantic Search tìm job_title gần nhất
    Bước 2: Content-Based Filtering lấy skills còn thiếu
    """

    # Normalize CV skills
    cv_skills_clean = [
        normalize_skill(s.lower().strip())
        for s in cv_skills
    ]

    # ── Bước 1: Semantic Search ────────────────────────
    title_clean  = clean_query(job_title)
    title_vector = model.encode(
        [title_clean],
        normalize_embeddings=True
    ).astype("float32")

    scores, indices = index.search(title_vector, k=top_k * 3)
    candidate_jobs  = df.iloc[indices[0]].copy()
    candidate_jobs["score"] = scores[0]
    total_candidates = len(candidate_jobs)

    # ── Bước 2: Content-Based Filtering ───────────────
    user_skills_set = set(cv_skills_clean)
    missing = []

    for _, row in candidate_jobs.iterrows():
        job_skills = set(
            normalize_skill(s)
            for s in row["job_skills"].lower().split(", ")
            if s.strip()
        )
        missing += list(job_skills - user_skills_set)

    # Đếm tần suất
    skill_counts = Counter(missing).most_common(top_skills)

    return {
        "vi_tri_ung_tuyen":    job_title,
        "job_titles_gan_nhat": candidate_jobs["job_title"] \
                                             .unique()[:3].tolist(),
        "top_scores":          scores[0][:3].tolist(),
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
    total = result.get("total_candidates", 100)

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
        print(
            f"    {i}. {item['skill']}"
            f" (xuat hien trong {item['count']}/{total} job tuong tu)"
        )
    print(LINE)