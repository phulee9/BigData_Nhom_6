"""
Load BM25Plus model (pickle) từ MinIO → interactive query.

Không cần rebuild — load pickle là dùng luôn.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.recommendation.core.model_bm25 import BM25PlusRecommender
from src.config import GOLD_KAGGLE_BM25_MODEL
from src.storage.minio_client import get_minio_client, download_pickle


def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    load_dotenv()

    print("==================================================")
    print("BM25Plus — Load & Query từ MinIO")
    print("==================================================")

    print("Đang tải model từ MinIO...")
    client = get_minio_client()
    recommender: BM25PlusRecommender = download_pickle(
        client=client,
        object_name=GOLD_KAGGLE_BM25_MODEL,
    )

    n_roles = len(recommender.get_roles())
    print(f"✅ Tải thành công! {n_roles} roles. Sẵn sàng query.")
    print("--------------------------------------------------")

    while True:
        print("\nNhập thông tin (gõ 'q' để thoát):")

        target_role = input(">> Role (vd: data engineer): ").strip()
        if target_role.lower() in ['q', 'quit', 'exit']:
            break
        if not target_role:
            continue

        skills_input = input(">> Skills đã có (cách nhau bằng dấu phẩy): ").strip()
        user_skills = [s.strip() for s in skills_input.split(",")] if skills_input else []

        query_display = f"{target_role} {' '.join(user_skills)}".strip()
        print(f"\n  🔍 Query: \"{query_display}\"")

        results = recommender.query(
            target_role=target_role,
            user_skills=user_skills,
            top_k=15,
        )

        print("\n[Kết quả — Skills cần học thêm]:")
        if not results:
            print(f"  Không tìm thấy gợi ý cho '{query_display}'.")
        else:
            for i, res in enumerate(results, 1):
                print(f"  {i:>2}. {res['skill']:<30} (Score: {res['recommend_score']:.4f} | Jobs: {res['job_count']})")

        print("-" * 50)


if __name__ == "__main__":
    main()
