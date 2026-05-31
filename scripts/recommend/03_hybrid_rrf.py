import sys
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv

from src.config import EMBEDDING_MODEL, GOLD_KAGGLE_BM25_MODEL
from src.recommendation.core.model_bm25 import BM25PlusRecommender
from src.recommendation.core.hybrid_rrf import reciprocal_rank_fusion
from scripts.recommend.run_recommend import run_faiss_recommend_once
from src.recommendation.core.recommend import (
    load_default_runtime_indexes,
)
from src.storage.minio_client import get_minio_client, download_pickle

TOP_JOBS = 10
TOP_SKILLS = 10


def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    load_dotenv()

    print("Hybrid RRF — BM25Plus + Embedding")

    print("\n[1/3] Loading BM25Plus model từ MinIO...")
    client = get_minio_client()
    bm25_recommender: BM25PlusRecommender = download_pickle(
        client=client,
        object_name=GOLD_KAGGLE_BM25_MODEL,
    )
    n_roles = len(bm25_recommender.get_roles())
    print(f"BM25Plus: {n_roles} roles")

    print("\n[2/3] Loading Embedding model...")
    emb_model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"Embedding: {EMBEDDING_MODEL}")

    print("\n[3/3] Loading FAISS indexes...")
    runtime_indexes = load_default_runtime_indexes()
    print("FAISS indexes loaded")

    print("Sẵn sàng! Nhập role + skills để nhận gợi ý hybrid.")

    while True:
        print("\n(Gõ 'q' để thoát)")

        target_role = input(">> Role (vd: data engineer): ").strip()
        if target_role.lower() in ['q', 'quit', 'exit']:
            break
        if not target_role:
            continue

        skills_input = input(">> Skills đã có (phẩy ngăn cách): ").strip()
        user_skills = [s.strip() for s in skills_input.split(",")] if skills_input else []

        print(f"\nQuery: \"{target_role}\" + {user_skills}")

        print("\n[BM25+] Querying...")
        bm25_results = bm25_recommender.query(
            target_role=target_role,
            user_skills=user_skills,
            top_k=TOP_SKILLS,
        )

        print("[Embedding] Querying...")
        input_data = {
            "job_title": target_role,
            "skills": skills_input,
        }
        emb_results_df = run_faiss_recommend_once(
            model=emb_model,
            runtime_indexes=runtime_indexes,
            input_data=input_data,
        )

        print("  [RRF] Fusing results...")
        hybrid_results = reciprocal_rank_fusion(
            bm25_skills=bm25_results,
            emb_skills=emb_results_df,
            top_k=TOP_SKILLS,
        )

        print(f"\n{'='*60}")
        print(f"  BM25+ ({len(bm25_results)} skills):")
        for i, r in enumerate(bm25_results, 1):
            print(f"    {i}. {r['skill']}")

        emb_list = emb_results_df.to_dict("records") if not emb_results_df.empty else []
        print(f"\nEmbedding ({len(emb_list)} skills):")
        for i, r in enumerate(emb_list, 1):
            print(f"    {i}. {r['skill']}")

        print(f"\nHYBRID RRF ({len(hybrid_results)} skills):")
        for i, r in enumerate(hybrid_results, 1):
            bm25_r = r['bm25_rank'] or '-'
            emb_r = r['emb_rank'] or '-'
            print(f"    {i:>2}. {r['skill']:<30} (RRF: {r['rrf_score']:.4f} | BM25: {bm25_r} | EMB: {emb_r} | Jobs: {r['job_count']})")

        print("=" * 60)


if __name__ == "__main__":
    main()