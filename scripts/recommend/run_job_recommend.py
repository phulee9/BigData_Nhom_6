import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.recommendation.core.recommend_job import (
    load_embedding_model,
    load_crawler_runtime,
    recommend_jobs_by_faiss,
)


def get_user_input() -> dict:
    # Nhập thông tin tìm việc
    job_title = input("Job title mong muốn: ").strip()

    while not job_title:
        print("Job title không được rỗng.")
        job_title = input("Job title mong muốn: ").strip()

    skills = input(
        "Skills hiện có, cách nhau bằng dấu phẩy "
        "(ví dụ: SQL, Excel, Power BI): "
    ).strip()

    location = input(
        "Location mong muốn, có thể bỏ trống "
        "(ví dụ: hanoi, ho chi minh): "
    ).strip()

    return {
        "job_title": job_title,
        "skills": skills,
        "location": location,
    }


def print_jobs(jobs: pd.DataFrame) -> None:
    # In kết quả job
    if jobs.empty:
        print("\nKhông tìm thấy job phù hợp.")
        return

    print("\nTOP JOBS PHÙ HỢP")

    for index, row in jobs.reset_index(drop=True).iterrows():
        title = str(row.get("title", "") or "").strip()
        location_raw = str(row.get("location_raw", "") or "").strip()
        score = float(row.get("score", 0) or 0)
        link = str(row.get("link", "") or "").strip()

        print(f"\n{index + 1}. {title}")
        print(f"   Location: {location_raw}")
        print(f"   Score   : {score:.4f}")
        print(f"   Link    : {link}")


def main() -> None:
    # Fix lỗi encoding khi in tiếng Việt trên Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    print("Loading embedding model...")
    model = load_embedding_model()
    print("Loaded embedding model.")

    print("\nLoading crawler FAISS runtime...")
    runtime = load_crawler_runtime()
    print("Loaded crawler runtime.")

    while True:
        print("\n====================================")
        print("JOB RECOMMENDATION BY FAISS")
        print("Gõ q để thoát")
        print("====================================")

        choice = input("Tiếp tục? [Enter/q]: ").strip().lower()

        if choice in [
            "q",
            "quit",
            "exit",
            "0",
        ]:
            print("Đã thoát.")
            break

        try:
            input_data = get_user_input()

            print("\nĐang tìm job phù hợp...")

            jobs = recommend_jobs_by_faiss(
                model=model,
                runtime=runtime,
                job_title=input_data["job_title"],
                skills=input_data["skills"],
                location=input_data["location"],
                top_k_each_index=100,
                top_n=10,
            )

            print_jobs(jobs)

        except Exception as error:
            print(f"Có lỗi xảy ra: {error}")


if __name__ == "__main__":
    main()