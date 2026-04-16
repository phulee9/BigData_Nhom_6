import re
import sys
import nltk
import numpy as np
import pandas as pd
from collections import Counter
from pathlib import Path
from sentence_transformers import SentenceTransformer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

# Them path den etl/ de import nlp_utils
sys.path.append(str(Path(__file__).parent.parent.parent / "etl"))

from skill_config import normalize_skill, is_valid_skill

# Setup NLTK
for pkg in ["wordnet", "omw-1.4", "stopwords"]:
    try:
        nltk.data.find(f"corpora/{pkg}")
    except Exception:
        nltk.download(pkg, quiet=True)

lemmatizer = WordNetLemmatizer()
STOP_WORDS  = set(stopwords.words("english"))

# Load Sentence Transformer 1 lan khi import
print("Load Sentence Transformer...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model ready!")


def clean_query(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text   = text.lower()
    text   = re.sub(r"[^\w\s]", " ", text)
    text   = re.sub(r"\s+",     " ", text).strip()
    tokens = [w for w in text.split() if w not in STOP_WORDS]
    return " ".join(lemmatizer.lemmatize(w) for w in tokens)


def get_keywords(job_title: str) -> list:
    # Lay keywords tu job_title goc lan job_title da normalize
    # Dam bao khop duoc voi data da qua NLP pipeline
    # VD: "backend" -> raw=["backend"] + clean=["back","end"]
    # -> filter tim duoc ca "back end developer" trong data
    try:
        from nlp_utils import process_job_title
        job_title_clean = process_job_title(job_title)
        clean_words = [w for w in job_title_clean.split() if len(w) > 2]
    except Exception:
        clean_words = []

    raw_words = [w for w in job_title.lower().split() if len(w) > 2]
    return list(set(raw_words + clean_words))


def search_index(
    query_vector: np.ndarray,
    index,
    df:        pd.DataFrame,
    job_title: str,
    k:         int
) -> pd.DataFrame:
    # Tim top k jobs gan nhat trong index
    # Filter theo keywords cua job_title (ca raw lan normalized)
    # Khong fallback — tra ve ket qua filter thuc te ke ca khi rong
    scores, indices = index.search(query_vector, k=k)
    candidates      = df.iloc[indices[0]].copy()
    candidates["score"] = scores[0]

    keywords = get_keywords(job_title)
    if keywords:
        mask     = candidates["job_title"].str.contains(
            "|".join(keywords), case=False, na=False
        )
        filtered = candidates[mask]
    else:
        filtered = candidates

    return filtered


def count_missing_skills(
    candidate_jobs:  pd.DataFrame,
    user_skills_set: set
) -> Counter:
    # Dem skills con thieu tu cac jobs tuong tu
    missing = []
    for _, row in candidate_jobs.iterrows():
        job_skills = set(
            normalize_skill(s)
            for s in row["job_skills"].lower().split(", ")
            if s.strip() and is_valid_skill(normalize_skill(s.strip()))
        )
        missing += list(job_skills - user_skills_set)
    return Counter(missing)


def recommend_skills(
    cv_skills:  list,
    job_title:  str,
    index_old,
    df_old:     pd.DataFrame,
    top_k:      int   = 150,
    top_skills: int   = 10,
    index_new         = None,
    df_new            = None,
    w_old:      float = 0.6,
    w_new:      float = 0.4
) -> dict:
    # Chuan hoa skills tu CV
    cv_skills_clean = [normalize_skill(s.lower().strip()) for s in cv_skills]
    user_skills_set = set(cv_skills_clean)

    # Encode query = job_title + cv_skills (giong format index)
    query        = job_title + " " + " ".join(cv_skills_clean)
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

    # TH4: ca 2 deu khong co job sau filter -> tra ve error
    if total_old == 0 and total_new == 0:
        return {
            "vi_tri_ung_tuyen"   : job_title,
            "job_titles_gan_nhat": [],
            "top_scores"         : [],
            "skills_da_co"       : cv_skills_clean,
            "total_candidates"   : 0,
            "total_old"          : 0,
            "total_new"          : 0,
            "skills_goi_y"       : [],
            "error"              : f"Khong tim thay job phu hop voi vi tri '{job_title}'"
        }

    # Tinh % xuat hien tung skill trong index cu (TH1 + TH2)
    skill_pct_old = {}
    if total_old > 0:
        counts_old    = count_missing_skills(candidates_old, set())
        skill_pct_old = {s: c / total_old for s, c in counts_old.items()}

    # Tinh % xuat hien tung skill trong index moi (TH1 + TH3)
    skill_pct_new = {}
    if total_new > 0:
        counts_new    = count_missing_skills(candidates_new, set())
        skill_pct_new = {s: c / total_new for s, c in counts_new.items()}

    # Merge ket qua theo 4 truong hop
    all_skills = set(skill_pct_old) | set(skill_pct_new)
    merged     = {}

    for skill in all_skills:
        # Bo qua skills nguoi dung da co trong CV
        if skill in user_skills_set:
            continue

        pct_old = skill_pct_old.get(skill, 0)
        pct_new = skill_pct_new.get(skill, 0)

        if total_old > 0 and total_new > 0:
            # TH1: ca 2 co job -> merge co trong so
            if pct_old > 0 and pct_new > 0:
                merged[skill] = w_old * pct_old + w_new * pct_new
            elif pct_new > 0:
                # Chi xuat hien o index moi -> giam trong so
                merged[skill] = w_new * pct_new * 0.5
            else:
                # Chi xuat hien o index cu
                merged[skill] = w_old * pct_old

        elif total_old > 0:
            # TH2: chi co index cu -> dung 100% index cu
            merged[skill] = pct_old

        else:
            # TH3: chi co index moi -> dung 100% index moi
            merged[skill] = pct_new

    # Sap xep giam dan theo score, lay top skills
    top = sorted(merged.items(), key=lambda x: -x[1])[:top_skills]

    total_candidates = total_old + total_new

    # Job titles gan nhat tu nguon co du lieu
    titles_old = candidates_old["job_title"].unique()[:2].tolist() \
        if not candidates_old.empty else []
    titles_new = candidates_new["job_title"].unique()[:1].tolist() \
        if not candidates_new.empty else []
    job_titles = (titles_old + titles_new)[:3]

    # Top scores tu nguon co du lieu
    if not candidates_old.empty:
        top_scores = candidates_old["score"].head(3).tolist()
    else:
        top_scores = candidates_new["score"].head(3).tolist()

    return {
        "vi_tri_ung_tuyen"   : job_title,
        "job_titles_gan_nhat": job_titles,
        "top_scores"         : top_scores,
        "skills_da_co"       : cv_skills_clean,
        "total_candidates"   : total_candidates,
        "total_old"          : total_old,
        "total_new"          : total_new,
        "skills_goi_y"       : [
            {"skill": s, "score": round(score, 3)}
            for s, score in top
        ],
    }


def print_recommendation(result: dict):
    LINE  = "=" * 50
    t_old = result.get("total_old", 0)
    t_new = result.get("total_new", 0)
    total = result.get("total_candidates", 0)

    print(f"\n{LINE}")
    print("  KET QUA GOI Y SKILLS")
    print(LINE)
    print(f"  Vi tri : {result['vi_tri_ung_tuyen']}")

    if result.get("error"):
        print(f"\n  [!] {result['error']}")
        print(LINE)
        return

    print(f"  Jobs   : {total} ({t_old} cu + {t_new} moi)")

    print(f"\n  Job titles gan nhat:")
    for i, (t, s) in enumerate(
        zip(result["job_titles_gan_nhat"], result["top_scores"]), 1
    ):
        print(f"    {i}. {t} (do tuong dong: {s:.2f})")

    print(f"\n  Skills da co ({len(result['skills_da_co'])}):")
    for s in result["skills_da_co"]:
        print(f"    v {s}")

    print(f"\n  Skills nen hoc them:")
    for i, item in enumerate(result["skills_goi_y"], 1):
        print(f"    {i}. {item['skill']} (score: {item['score']})")

    print(LINE)