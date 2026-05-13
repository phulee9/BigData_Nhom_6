"""
Script offline query TF-IDF Unified Document Model.

Load matrix từ MinIO (gold/kaggle/tfidf/), cho phép interactive query.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.recommendation.core.model_tfidf import TFIDFRecommender
from src.config import GOLD_KAGGLE_TFIDF_MATRIX
from src.storage.minio_client import (
    get_minio_client,
    read_parquet_from_minio,
)


def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    load_dotenv()

    print("==================================================")
    print("TF-IDF Unified Document Model — Query từ MinIO")
    print("==================================================")

    # Load matrix từ MinIO
    print("Đang tải ma trận TF-IDF từ MinIO...")
    client = get_minio_client()
    df_matrix = read_parquet_from_minio(
        client=client,
        object_name=GOLD_KAGGLE_TFIDF_MATRIX,
    )

    recommender = TFIDFRecommender()
    recommender.load_matrix(df_matrix)

    n_roles = len(recommender.get_roles())
    print(f"✅ Tải thành công! {n_roles} roles, {len(df_matrix)} entries.")
    print("--------------------------------------------------")

    while True:
        print("\nNhập thông tin để nhận gợi ý (hoặc gõ 'q' ở Role để thoát):")

        target_role = input(">> Nhập Role (vd: data engineer): ").strip()
        if target_role.lower() in ['q', 'quit', 'exit']:
            break

        if not target_role:
            continue

        skills_input = input(">> Nhập Skills bạn đã có, cách nhau bằng dấu phẩy (vd: python, sql): ").strip()
        user_skills = [s.strip() for s in skills_input.split(",")] if skills_input else []

        level = input(">> Nhập Level (junior / senior / bỏ trống): ").strip()

        # Hiện query string (unified: role + skills gộp chung)
        query_display = f"{target_role} {' '.join(user_skills)}".strip()
        print(f"\n  🔍 Query (unified): \"{query_display}\"")

        print("\n[Kết quả gợi ý TF-IDF — Unified Model]:")
        results = recommender.query(
            target_role=target_role,
            user_skills=user_skills,
            level=level if level else None,
            top_k=15,
        )

        if not results:
            print(f"Không tìm thấy gợi ý nào cho '{query_display}'. Hãy thử keyword khác.")
        else:
            for i, res in enumerate(results, 1):
                print(f"  {i:>2}. {res['skill']:<30} (Score: {res['score']:.4f} | Jobs: {res['job_count']})")

        print("-" * 50)


if __name__ == "__main__":
    main()
