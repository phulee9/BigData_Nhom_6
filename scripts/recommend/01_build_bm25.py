import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.recommendation.core.model_bm25 import BM25PlusRecommender
from src.config import GOLD_KAGGLE_BM25_MODEL
from src.storage.minio_client import get_minio_client, upload_pickle
from dotenv import load_dotenv

def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    load_dotenv()

    recommender = BM25PlusRecommender()

    print("\nĐang kéo dữ liệu từ MinIO và build BM25Plus...")
    recommender.load_from_minio()

    roles = recommender.get_roles()
    print(f"\nĐã build xong! Tổng số roles: {len(roles)}")

    print("\n==================================================")
    print("Test: Gợi ý skills")
    print("==================================================")

    test_cases = [
        {"role": "data engineer", "skills": ["python", "sql", "git"]},
        {"role": "data analyst", "skills": ["excel", "power bi"]},
        {"role": "ml engineer", "skills": ["tensorflow", "python"]},
    ]

    for idx, tc in enumerate(test_cases, 1):
        role = tc["role"]
        skills = tc["skills"]
        query_text = f"{role} {' '.join(skills)}"

        print(f"\n[Test Case {idx}]")
        print(f"Query: \"{query_text}\"")

        results = recommender.query(target_role=role, user_skills=skills, top_k=10)

        if not results:
            print("     (Không tìm thấy)")
        else:
            for i, res in enumerate(results, 1):
                print(f"     {i:>2}. {res['skill']:<25} (Score: {res['recommend_score']:.4f} | Jobs: {res['job_count']})")

    print("Upload BM25Plus model (pickle) lên MinIO...")
    client = get_minio_client()
    upload_pickle(
        client=client,
        obj=recommender,
        object_name=GOLD_KAGGLE_BM25_MODEL,
    )
    print(f"Done: s3://{GOLD_KAGGLE_BM25_MODEL}")


if __name__ == "__main__":
    main()
