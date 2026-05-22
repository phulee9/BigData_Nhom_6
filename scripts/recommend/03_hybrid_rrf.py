"""
Hybrid RRF Recommend — Kết hợp BM25Plus + Embedding.

1. Load BM25Plus model (pickle) từ MinIO
2. Load Embedding model + FAISS indexes
3. User nhập role + skills
4. Query cả 2 bên → RRF fusion → in kết quả
"""

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
from src.recommendation.core.recommend import (
    build_query_texts,
    encode_query,
    collect_candidates_from_source,
    build_candidate_rows,
    limit_candidates_by_source,
    recommend_missing_skills,
    parse_skills,
    load_default_runtime_indexes,
    SOURCE_TOP_K,
)
from src.storage.minio_client import get_minio_client, download_pickle


TOP_JOBS = 10
TOP_SKILLS = 10
KAGGLE_TOP_K = 300
CRAWLER_TOP_K = 50


def get_emb_missing_skills(
    model: SentenceTransformer,
    runtime_indexes,
    job_title: str,
    user_skills: list[str],
    location: str = "Unknown",
) -> pd.DataFrame:
    """Chạy embedding pipeline, trả về missing_skills DataFrame."""
    query_texts = build_query_texts(
        job_title=job_title,
        skills=user_skills,
        location=location,
    )

    query_embeddings = {
        "title_text": encode_query(model=model, text=query_texts["title_text"]),
        "skills_text": encode_query(model=model, text=query_texts["skills_text"]),
        "full_text": encode_query(model=model, text=query_texts["full_text"]),
    }

    source_top_k = {"kaggle": KAGGLE_TOP_K, "crawler": CRAWLER_TOP_K}
    all_candidates = {}

    for runtime in runtime_indexes:
        source_name = runtime.source_name
        target_top_k = source_top_k.get(
            source_name, SOURCE_TOP_K.get(source_name, 100)
        )
        source_candidates = collect_candidates_from_source(
            runtime_index=runtime,
            query_embeddings=query_embeddings,
            top_k_each_index=target_top_k * 2,
        )
        all_candidates.update(source_candidates)

    all_jobs_df = build_candidate_rows(
        candidates=all_candidates,
        runtime_indexes=runtime_indexes,
        user_job_title=job_title,
        user_skills=user_skills,
        user_location=location,
    )

    if all_jobs_df.empty:
        return pd.DataFrame()

    rerank_pool_df = limit_candidates_by_source(
        candidates_df=all_jobs_df,
        source_limits=source_top_k,
    )

    return recommend_missing_skills(
        recommended_jobs=rerank_pool_df,
        user_skills=user_skills,
        top_n=TOP_SKILLS,
    )


def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    load_dotenv()

    print("==================================================")
    print("Hybrid RRF — BM25Plus + Embedding")
    print("==================================================")

    # 1. Load BM25Plus model
    print("\n[1/3] Loading BM25Plus model từ MinIO...")
    client = get_minio_client()
    bm25_recommender: BM25PlusRecommender = download_pickle(
        client=client,
        object_name=GOLD_KAGGLE_BM25_MODEL,
    )
    n_roles = len(bm25_recommender.get_roles())
    print(f"  ✅ BM25Plus: {n_roles} roles")

    # 2. Load Embedding model
    print("\n[2/3] Loading Embedding model...")
    emb_model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"  ✅ Embedding: {EMBEDDING_MODEL}")

    # 3. Load FAISS indexes
    print("\n[3/3] Loading FAISS indexes...")
    runtime_indexes = load_default_runtime_indexes()
    print("  ✅ FAISS indexes loaded")

    print("\n==================================================")
    print("Sẵn sàng! Nhập role + skills để nhận gợi ý hybrid.")
    print("==================================================")

    while True:
        print("\n(Gõ 'q' để thoát)")

        target_role = input(">> Role (vd: data engineer): ").strip()
        if target_role.lower() in ['q', 'quit', 'exit']:
            break
        if not target_role:
            continue

        skills_input = input(">> Skills đã có (phẩy ngăn cách): ").strip()
        user_skills = [s.strip() for s in skills_input.split(",")] if skills_input else []

        print(f"\n  🔍 Query: \"{target_role}\" + {user_skills}")

        # BM25 query
        print("\n  [BM25+] Querying...")
        bm25_results = bm25_recommender.query(
            target_role=target_role,
            user_skills=user_skills,
            top_k=TOP_SKILLS,
        )

        # Embedding query
        print("  [Embedding] Querying...")
        emb_results_df = get_emb_missing_skills(
            model=emb_model,
            runtime_indexes=runtime_indexes,
            job_title=target_role,
            user_skills=user_skills,
        )

        # RRF fusion
        print("  [RRF] Fusing results...")
        hybrid_results = reciprocal_rank_fusion(
            bm25_skills=bm25_results,
            emb_skills=emb_results_df,
            top_k=TOP_SKILLS,
        )

        # Print results
        print(f"\n{'='*60}")
        print(f"  BM25+ ({len(bm25_results)} skills):")
        for i, r in enumerate(bm25_results[:5], 1):
            print(f"    {i}. {r['skill']}")

        emb_list = emb_results_df.to_dict("records") if not emb_results_df.empty else []
        print(f"\n  Embedding ({len(emb_list)} skills):")
        for i, r in enumerate(emb_list[:5], 1):
            print(f"    {i}. {r['skill']}")

        print(f"\n  🏆 HYBRID RRF ({len(hybrid_results)} skills):")
        for i, r in enumerate(hybrid_results, 1):
            bm25_r = r['bm25_rank'] or '-'
            emb_r = r['emb_rank'] or '-'
            print(f"    {i:>2}. {r['skill']:<30} (RRF: {r['rrf_score']:.4f} | BM25: {bm25_r} | EMB: {emb_r} | Jobs: {r['job_count']})")

        print("=" * 60)


if __name__ == "__main__":
    main()
