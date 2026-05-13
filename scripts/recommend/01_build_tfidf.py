"""
Script build TF-IDF Unified Document Model từ MinIO.

Workflow:
1. Khởi tạo TFIDFRecommender
2. Load Silver Final Clean từ MinIO → build unified TF-IDF
3. Test query với vài test cases
4. Upload matrix lên MinIO (gold/kaggle/tfidf/)
"""

import sys
from pathlib import Path

# Thêm project root vào sys.path để import được src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.recommendation.core.model_tfidf import TFIDFRecommender
from src.config import GOLD_KAGGLE_TFIDF_MATRIX
from src.storage.minio_client import (
    get_minio_client,
    upload_df_parquet,
)

from dotenv import load_dotenv


def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    load_dotenv()

    print("==================================================")
    print("Build TF-IDF Unified Document Model")
    print("==================================================")

    # 1. Khởi tạo model và build từ MinIO (Silver Final Clean)
    recommender = TFIDFRecommender()

    print("\nĐang kéo dữ liệu từ MinIO và build unified TF-IDF...")
    recommender.load_from_minio()

    if not recommender.is_loaded:
        print("Lỗi: Không thể load dữ liệu để build model.")
        return

    # In thống kê
    roles = recommender.get_roles()
    print(f"\nĐã build xong! Tổng số roles: {len(roles)}")
    print("Top 5 roles đầu tiên:")
    for r in roles[:5]:
        print(f"  - {r}")

    # 2. Test query (skill recommendation — unified: role + skills gộp chung)
    print("\n==================================================")
    print("Test: Gợi ý skills (Unified TF-IDF Query)")
    print("  → Query = role + skills gộp thành 1 chuỗi")
    print("  → Cosine similarity trên toàn bộ TF-IDF space")
    print("==================================================")

    test_cases = [
        {
            "role": "data engineer",
            "skills": ["python", "sql", "git"],
            "level": "senior",
        },
        {
            "role": "data analyst",
            "skills": ["excel", "power bi"],
            "level": "junior",
        },
        {
            "role": "ml engineer",
            "skills": ["tensorflow", "python"],
            "level": None,
        },
    ]

    for idx, tc in enumerate(test_cases, 1):
        role = tc["role"]
        skills = tc["skills"]
        level = tc["level"]

        # Hiện unified query
        query_text = f"{role} {' '.join(skills)}"
        level_display = level.title() if level else "N/A"

        print(f"\n[Test Case {idx}]")
        print(f"  🔍 Query (unified): \"{query_text}\"")
        print(f"  Level: {level_display}")

        results = recommender.query(
            target_role=role,
            user_skills=skills,
            level=level,
            top_k=10,
        )

        print("  => Gợi ý skills cần học thêm:")
        if not results:
            print("     (Không tìm thấy)")
        else:
            for i, res in enumerate(results, 1):
                print(f"     {i:>2}. {res['skill']:<25} (Score: {res['score']:.4f} | Jobs: {res['job_count']})")

    # 3. Upload matrix lên MinIO
    print("\n==================================================")
    print("Upload TF-IDF matrix lên MinIO...")
    client = get_minio_client()
    upload_df_parquet(
        client=client,
        df=recommender.df_tfidf,
        object_name=GOLD_KAGGLE_TFIDF_MATRIX,
    )
    print(f"✅ Đã upload lên: s3://{GOLD_KAGGLE_TFIDF_MATRIX}")
    print("==================================================")


if __name__ == "__main__":
    main()
