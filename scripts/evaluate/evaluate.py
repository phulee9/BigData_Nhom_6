import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import random
import numpy as np
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

from src.config import EMBEDDING_MODEL, GOLD_KAGGLE_BM25_MODEL
from src.recommendation.core.hybrid_rrf import reciprocal_rank_fusion
from src.recommendation.core.recommend import load_default_runtime_indexes
from src.storage.minio_client import get_minio_client, download_pickle
from scripts.recommend.run_recommend import run_faiss_recommend_once

client = get_minio_client()
bm25_model = download_pickle(client, GOLD_KAGGLE_BM25_MODEL)
emb_model = SentenceTransformer(EMBEDDING_MODEL)
runtime_indexes = load_default_runtime_indexes()

def split_data(skills, ratio=0.6):
    skills = skills.copy()
    random.shuffle(skills)
    idx = max(1, int(len(skills) * ratio))
    return skills[:idx], set(skills[idx:])

def recall_at_k(preds, targets, k):
    return sum(1 for p in preds[:k] if p in targets) / len(targets) if targets else 0

def precision_at_k(preds, targets, k):
    return sum(1 for p in preds[:k] if p in targets) / k if preds else 0

def ndcg_at_k(preds, targets, k):
    gains = [1 if p in targets else 0 for p in preds[:k]]
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains))
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(sorted(gains, reverse=True)))
    return dcg / idcg if idcg > 0 else 0

def hit_rate_at_k(preds, targets, k):
    return 1 if any(p in targets for p in preds[:k]) else 0

def get_metrics(preds, targets, k=10):
    return {
        "recall":    recall_at_k(preds, targets, k),
        "precision": precision_at_k(preds, targets, k),
        "ndcg":      ndcg_at_k(preds, targets, k),
        "hit_rate":  hit_rate_at_k(preds, targets, k),
    }

K = 10 
df = pd.read_parquet(PROJECT_ROOT / "data/downloads/kaggle/gold/jobs_metadata.parquet")
df['clean_skills'] = df['skills_normalized'].apply(lambda x: [s.strip() for s in str(x).split(',') if s.strip()])
test_df = df[df['clean_skills'].apply(len) >= 4].sample(n=500, random_state=42)

scores = {m: {k: 0.0 for k in ["recall", "precision", "ndcg", "hit_rate"]} for m in ["bm25", "emb", "hybrid"]}
valid = 0

for _, row in tqdm(test_df.iterrows(), total=len(test_df)):
    given, target = split_data(row['clean_skills'])
    if not target:
        continue
    valid += 1
    title = row['title_core']

    bm25_raw  = bm25_model.query(title, given, K)
    bm25_preds = [x['skill'] for x in bm25_raw]

    emb_df    = run_faiss_recommend_once(emb_model, runtime_indexes, {"job_title": title, "skills": ", ".join(given)})
    emb_preds = emb_df['skill'].tolist() if not emb_df.empty else []

    hybrid_preds = [x['skill'] for x in reciprocal_rank_fusion(bm25_raw, emb_df, K)]

    for name, preds in [("bm25", bm25_preds), ("emb", emb_preds), ("hybrid", hybrid_preds)]:
        for metric, val in get_metrics(preds, target, K).items():
            scores[name][metric] += val

print(f"\n--- Evaluate @{K} trên {valid} jobs ---")
print(f"{'Model':<10} {'Recall':>8} {'Precision':>10} {'NDCG':>8} {'HitRate':>9}")
print("-" * 50)
for m in ["bm25", "emb", "hybrid"]:
    r  = scores[m]['recall']    / valid * 100
    p  = scores[m]['precision'] / valid * 100
    nd = scores[m]['ndcg']      / valid * 100
    hr = scores[m]['hit_rate']  / valid * 100
    print(f"{m.upper():<10} {r:>7.2f}% {p:>9.2f}% {nd:>7.2f}% {hr:>8.2f}%")