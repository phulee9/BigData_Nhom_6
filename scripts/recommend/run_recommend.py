import json
import shutil
import sys
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.config import EMBEDDING_MODEL
from src.recommendation.cv.cv_extractor import extract_cv_file
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


# Fixed config
TOP_JOBS = 10
TOP_SKILLS = 10

KAGGLE_TOP_K = 300
CRAWLER_TOP_K = 50

LOCAL_CV_UPLOAD_DIR = PROJECT_ROOT / "data" / "cv" / "uploads"


# CV upload utilities
def select_cv_file_with_dialog() -> Path | None:
    try:
        from tkinter import Tk, filedialog
    except Exception as error:
        raise RuntimeError(
            "Không import được tkinter. Chức năng Upload CV cần tkinter."
        ) from error

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Chọn file CV PDF",
        filetypes=[
            ("PDF files", "*.pdf"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()

    if not file_path:
        return None

    return Path(file_path)


def copy_selected_cv_to_project(cv_path: Path) -> Path:
    if not cv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file CV: {cv_path}")

    if cv_path.suffix.lower() != ".pdf":
        raise ValueError("File CV phải là PDF.")

    LOCAL_CV_UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = cv_path.name.replace(" ", "_")
    target_path = LOCAL_CV_UPLOAD_DIR / safe_name

    shutil.copy2(
        cv_path,
        target_path,
    )

    return target_path


# Input menu
def choose_input_mode() -> str:
    print("\nJOB & SKILL RECOMMENDATION")
    print("1. Nhập tay")
    print("2. Upload CV PDF")
    print("0. Thoát")

    while True:
        choice = input("\nChọn chức năng [1/2/0]: ").strip()

        if choice in ["1", "2", "0"]:
            return choice

        print("Lựa chọn không hợp lệ. Vui lòng nhập 1, 2 hoặc 0.")


def get_manual_input() -> dict:
    print("\nBạn đã chọn: Nhập tay")

    job_title = input("Job title: ").strip()

    while not job_title:
        print("Job title không được rỗng.")
        job_title = input("Job title: ").strip()

    skills = input(
        "Current skills, cách nhau bằng dấu phẩy "
        "(ví dụ: SQL, Power BI, Excel): "
    ).strip()

    location = input(
        "Location "
        "(ví dụ: Ho Chi Minh, Vietnam): "
    ).strip()

    if not location:
        location = "Unknown"

    return {
        "job_title": job_title,
        "skills": skills,
        "location": location,
    }


def get_cv_input() -> dict:
    print("\nBạn đã chọn: Upload CV PDF")
    print("Đang mở cửa sổ chọn file PDF...")

    selected_file = select_cv_file_with_dialog()

    if selected_file is None:
        raise ValueError("Bạn chưa chọn file CV nào.")

    copied_file = copy_selected_cv_to_project(selected_file)

    print(f"Đã chọn CV: {selected_file}")
    print(f"Đã copy vào project: {copied_file}")
    print("Đang extract CV bằng Groq...")

    extracted = extract_cv_file(copied_file)

    print("\nKết quả extract từ CV:")
    print(
        json.dumps(
            extracted,
            ensure_ascii=False,
            indent=2,
        )
    )

    return {
        "job_title": extracted.get("job_title", "Unknown"),
        "skills": extracted.get("current_skills", []),
        "location": extracted.get("location", "Unknown"),
    }


# Recommend core
def run_recommend_once(
    model: SentenceTransformer,
    runtime_indexes,
    input_data: dict,
) -> dict[str, pd.DataFrame]:
    user_job_title = str(input_data["job_title"] or "").strip()
    user_skills = parse_skills(input_data["skills"])
    user_location = str(input_data["location"] or "Unknown").strip()

    query_texts = build_query_texts(
        job_title=user_job_title,
        skills=user_skills,
        location=user_location,
    )

    query_embeddings = {
        "title_text": encode_query(
            model=model,
            text=query_texts["title_text"],
        ),
        "skills_text": encode_query(
            model=model,
            text=query_texts["skills_text"],
        ),
        "full_text": encode_query(
            model=model,
            text=query_texts["full_text"],
        ),
    }

    all_candidates = {}

    source_top_k = {
        "kaggle": KAGGLE_TOP_K,
        "crawler": CRAWLER_TOP_K,
    }

    for runtime in runtime_indexes:
        source_name = runtime.source_name
        target_top_k = source_top_k.get(
            source_name,
            SOURCE_TOP_K.get(source_name, 100),
        )

        search_top_k_each_index = target_top_k * 2

        source_candidates = collect_candidates_from_source(
            runtime_index=runtime,
            query_embeddings=query_embeddings,
            top_k_each_index=search_top_k_each_index,
        )

        all_candidates.update(source_candidates)

    all_jobs_df = build_candidate_rows(
        candidates=all_candidates,
        runtime_indexes=runtime_indexes,
        user_job_title=user_job_title,
        user_skills=user_skills,
        user_location=user_location,
    )

    if all_jobs_df.empty:
        return {
            "top_jobs": pd.DataFrame(),
            "missing_skills": pd.DataFrame(),
            "rerank_pool": pd.DataFrame(),
        }

    rerank_pool_df = limit_candidates_by_source(
        candidates_df=all_jobs_df,
        source_limits=source_top_k,
    )

    top_jobs_df = (
        rerank_pool_df
        .sort_values(
            by="final_score",
            ascending=False,
        )
        .head(TOP_JOBS)
        .copy()
    )

    missing_skills_df = recommend_missing_skills(
        recommended_jobs=rerank_pool_df,
        user_skills=user_skills,
        top_n=TOP_SKILLS,
    )

    return {
        "top_jobs": top_jobs_df,
        "missing_skills": missing_skills_df,
        "rerank_pool": rerank_pool_df,
    }


# Output
def get_job_link(row: pd.Series) -> str:
    job_url = str(row.get("job_url", "") or "").strip()
    job_link = str(row.get("job_link", "") or "").strip()

    if job_url:
        return job_url

    if job_link:
        return job_link

    return "No link"


def print_top_jobs(top_jobs: pd.DataFrame) -> None:
    print("\nTOP 10 JOBS")

    if top_jobs.empty:
        print("Không tìm thấy job phù hợp.")
        return

    for index, row in top_jobs.reset_index(drop=True).iterrows():
        title = str(row.get("job_title_canonical", "") or "Unknown").strip()
        link = get_job_link(row)

        print(f"{index + 1}. {title}")
        print(f"   Link: {link}")


def print_missing_skills(missing_skills: pd.DataFrame) -> None:
    print("\nTOP 10 SKILLS CÒN THIẾU")

    if missing_skills.empty:
        print("Không có skill mới để gợi ý.")
        return

    for index, row in missing_skills.reset_index(drop=True).iterrows():
        skill = str(row.get("skill", "") or "").strip()

        if skill:
            print(f"{index + 1}. {skill}")


# Main loop
def main() -> None:
    print("Đang load embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("Đã load model.")

    print("\nĐang load Kaggle index + Crawler index...")
    runtime_indexes = load_default_runtime_indexes()
    print("Đã load index. Có thể recommend nhiều lần trong phiên này.")

    while True:
        choice = choose_input_mode()

        if choice == "0":
            print("Đã thoát chương trình.")
            break

        try:
            if choice == "1":
                input_data = get_manual_input()
            else:
                input_data = get_cv_input()

            print("\nĐang recommend...")

            result = run_recommend_once(
                model=model,
                runtime_indexes=runtime_indexes,
                input_data=input_data,
            )

            print_top_jobs(result["top_jobs"])
            print_missing_skills(result["missing_skills"])

        except Exception as error:
            print(f"\nCó lỗi xảy ra: {error}")

        print("\nBạn có thể tiếp tục recommend với input khác.")


if __name__ == "__main__":
    main()