from tkinter import Tk, filedialog

from recommendation.core.loader import load_system
from recommendation.core.recommend import recommend_from_cv_input
from recommendation.cv.cv_extractor import extract_and_prepare_cv
from recommendation.core.preprocess import (
    normalize_skill,
    normalize_location,
    process_job_title,
)


def pick_cv_file():
    root = Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="Chọn CV PDF",
        filetypes=[("PDF files", "*.pdf")],
    )

    return file_path if file_path else None


def input_manual():
    job_title = input("Nhập vị trí ứng tuyển: ").strip()
    location = input("Nhập location (vd: vietnam, united states, remote): ").strip()
    skills_text = input("Nhập skills hiện có, cách nhau bằng dấu phẩy: ").strip()

    skills = [
        normalize_skill(skill)
        for skill in skills_text.split(",")
        if normalize_skill(skill)
    ]

    return {
        "job_title": process_job_title(job_title),
        "location": normalize_location(location),
        "skills": sorted(list(set(skills))),
    }


def print_result(cv_input, result):
    print("\n==============================")
    print("INPUT")
    print("------------------------------")
    print(f"Job Title : {cv_input['job_title']}")
    print(f"Location  : {cv_input['location']}")
    print(f"Skills    : {', '.join(cv_input['skills'])}")

    print("\nTOP 5 JOB TƯƠNG ĐỒNG NHẤT")
    print("------------------------------")
    for job in result["top_5_similar_jobs"]:
        print(
            f"{job['rank']}. {job['job_title']} "
            f"({job['location']}) "
            f"| score={job['score']}"
        )

    print("\nTOP 10 SKILLS NGƯỜI DÙNG CHƯA CÓ")
    print("------------------------------")
    for skill in result["top_10_missing_skills"]:
        print(
            f"{skill['rank']}. {skill['skill']} "
            f"| score={skill['score']} "
            f"| frequency={skill['frequency']}"
        )

    print("==============================\n")


def run_recommend(cv_input, index, metadata, model):
    result = recommend_from_cv_input(
        cv_input=cv_input,
        index=index,
        metadata=metadata,
        model=model,
        retrieve_jobs=200,
        rerank_jobs=50,
        top_skills=10,
    )

    print_result(cv_input, result)


def main():
    print("Loading system...")
    index, metadata, model = load_system()
    print("System ready!")

    while True:
        print("\n========== MENU ==========")
        print("1. Gợi ý từ CV")
        print("2. Nhập tay")
        print("3. Thoát")

        choice = input("Chọn: ").strip()

        if choice == "3":
            print("Bye!")
            break

        elif choice == "1":
            cv_path = pick_cv_file()

            if not cv_path:
                print("Bạn chưa chọn CV.")
                continue

            print("Đang phân tích CV...")
            cv_input = extract_and_prepare_cv(cv_path)

            run_recommend(cv_input, index, metadata, model)

        elif choice == "2":
            cv_input = input_manual()

            if not cv_input["job_title"]:
                print("Job title không hợp lệ.")
                continue

            run_recommend(cv_input, index, metadata, model)

        else:
            print("Chọn 1, 2 hoặc 3.")


if __name__ == "__main__":
    main()