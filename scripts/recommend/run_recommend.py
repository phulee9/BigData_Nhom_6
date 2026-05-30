import sys
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import EMBEDDING_MODEL
from src.recommendation.core.recommend import (
    SOURCE_TOP_K,
    build_query_texts,
    encode_query,
    collect_candidates_from_source,
    build_candidate_rows,
    limit_candidates_by_source,
    recommend_missing_skills,
    parse_skills,
    load_default_runtime_indexes,
)


TOP_SKILLS = 10


def get_manual_input() -> dict:
    # Nhập job title và skills hiện có
    job_title = input("Job title: ").strip()

    while not job_title:
        print("Job title không được rỗng.")
        job_title = input("Job title: ").strip()

    skills = input(
        "Current skills, cách nhau bằng dấu phẩy "
        "(ví dụ: SQL, Power BI, Excel): "
    ).strip()

    return {
        "job_title": job_title,
        "skills": skills,
    }


def run_faiss_recommend_once(
    model: SentenceTransformer,
    runtime_indexes,
    input_data: dict,
) -> pd.DataFrame:
    # Chuẩn hóa input
    user_job_title = str(input_data["job_title"] or "").strip()
    user_skills = parse_skills(input_data["skills"])

    # Tạo query cho title index và skills index
    query_texts = build_query_texts(
        job_title=user_job_title,
        skills=user_skills,
    )

    # Encode query thành vector
    query_embeddings = {
        "title_text": encode_query(
            model=model,
            text=query_texts["title_text"],
        ),
        "skills_text": encode_query(
            model=model,
            text=query_texts["skills_text"],
        ),
    }

    # Search FAISS
    all_candidates = {}

    for runtime in runtime_indexes:
        top_k = SOURCE_TOP_K.get(runtime.source_name, 300)

        source_candidates = collect_candidates_from_source(
            runtime_index=runtime,
            query_embeddings=query_embeddings,
            top_k_each_index=top_k * 2,
        )

        all_candidates.update(source_candidates)

    # Join metadata
    all_jobs_df = build_candidate_rows(
        candidates=all_candidates,
        runtime_indexes=runtime_indexes,
        user_job_title=user_job_title,
        user_skills=user_skills,
    )

    if all_jobs_df.empty:
        return pd.DataFrame()

    # Giới hạn candidates theo source
    rerank_pool_df = limit_candidates_by_source(
        candidates_df=all_jobs_df,
        source_limits=SOURCE_TOP_K,
    )

    # Lấy skills còn thiếu
    missing_skills_df = recommend_missing_skills(
        recommended_jobs=rerank_pool_df,
        user_skills=user_skills,
        top_n=TOP_SKILLS,
    )

    return missing_skills_df


def print_missing_skills(missing_skills: pd.DataFrame) -> None:
    # In kết quả gợi ý skills
    print("\nTOP SKILLS CÒN THIẾU")

    if missing_skills.empty:
        print("Không có skill mới để gợi ý.")
        return

    for index, row in missing_skills.reset_index(drop=True).iterrows():
        skill = str(row.get("skill", "") or "").strip()
        score = row.get("recommend_score", 0)
        job_count = row.get("job_count", 0)

        print(
            f"{index + 1}. {skill} "
            f"(score={score:.4f}, jobs={job_count})"
        )


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("Loaded embedding model.")

    print("\nLoading Kaggle FAISS index...")
    runtime_indexes = load_default_runtime_indexes()
    print("Loaded FAISS index.")

    while True:
        print("\n====================================")
        print("FAISS MISSING SKILL RECOMMENDATION")
        print("Gõ q để thoát")
        print("====================================")

        choice = input("Tiếp tục? [Enter/q]: ").strip().lower()

        if choice in ["q", "quit", "exit", "0"]:
            print("Đã thoát.")
            break

        try:
            input_data = get_manual_input()

            print("\nĐang gợi ý skills bằng FAISS...")

            missing_skills = run_faiss_recommend_once(
                model=model,
                runtime_indexes=runtime_indexes,
                input_data=input_data,
            )

            print_missing_skills(missing_skills)

        except Exception as error:
            print(f"Có lỗi xảy ra: {error}")


if __name__ == "__main__":
    main()