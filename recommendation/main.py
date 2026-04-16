import os
import sys
import time
import json
import fitz
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

sys.path.append(str(Path(__file__).parent / "core"))
sys.path.append(str(Path(__file__).parent / "cv"))

from loader        import load_all_indexes
from recommend     import recommend_skills, print_recommendation
from roadmap       import skill_gap_roadmap, print_roadmap
from career_switch import career_switch_analysis, print_career_switch
from cv_extractor  import pick_cv_file, read_pdf, extract_cv, dedup_skills

LINE = "=" * 50
DASH = "-" * 40


def print_cv_result(data: dict, skills_clean: list):
    print(f"\n{LINE}")
    print("  KET QUA TRICH XUAT CV")
    print(LINE)
    print(f"  Vi tri : {data.get('vi_tri_ung_tuyen') or 'Khong tim thay'}")
    print(f"\n  Skills quan trong ({len(skills_clean)}):")
    for s in skills_clean:
        print(f"    - {s}")
    print(LINE)


def input_info() -> dict:
    # Nhap tay job_title va skills
    print(f"\n{DASH}")
    while True:
        job_title = input("  Nhap vi tri ung tuyen: ").strip()
        if job_title:
            break
        print("  [!] Khong duoc de trong!")

    print("  Nhap skills (cach nhau bang dau phay)")
    print("  Vi du: python, sql, machine learning")
    while True:
        skills_input = input("  Skills: ").strip()
        if skills_input:
            break
        print("  [!] Khong duoc de trong!")

    seen, skills = set(), []
    for s in skills_input.split(","):
        s = s.strip().lower()
        if s and s not in seen:
            seen.add(s)
            skills.append(s)

    return {"vi_tri_ung_tuyen": job_title.lower().strip(), "skills": skills}


def print_input(data: dict):
    print(f"\n{LINE}")
    print("  THONG TIN DA NHAP")
    print(LINE)
    print(f"  Vi tri : {data['vi_tri_ung_tuyen']}")
    print(f"\n  Skills ({len(data['skills'])}):")
    for s in data["skills"]:
        print(f"    - {s}")
    print(LINE)


def handle_career_switch(data: dict, df):
    # Xu ly tinh nang chuyen huong nghe nghiep
    print(f"\n{DASH}")
    while True:
        job_from = input("  Vi tri hien tai: ").strip().lower()
        if job_from:
            break
        print("  [!] Khong duoc de trong!")

    while True:
        job_to = input("  Vi tri muon chuyen sang: ").strip().lower()
        if job_to:
            break
        print("  [!] Khong duoc de trong!")

    print(f"\n{LINE}")
    print("  THONG TIN DA NHAP")
    print(LINE)
    print(f"  Tu   : {job_from}")
    print(f"  Sang : {job_to}")
    print(f"\n  Skills hien co ({len(data['skills'])}):")
    for s in data["skills"]:
        print(f"    - {s}")
    print(LINE)

    result = career_switch_analysis(
        job_from  = job_from,
        job_to    = job_to,
        cv_skills = data["skills"],
        df        = df,
        top_n     = 20
    )
    print_career_switch(result)


def main():
    print(f"\n{LINE}")
    print("  SKILL RECOMMENDER")
    print("  powered by FAISS + Sentence Transformer")
    print(LINE)

    # Load ca 2 index 1 lan duy nhat khi khoi dong
    print("\nKhoi dong he thong...")
    index_old, df_old, index_new, df_new = load_all_indexes()
    print("San sang!\n")

    while True:
        print(f"\n{DASH}")
        print("  1. Phan tich tu CV (PDF)")
        print("  2. Nhap tay thong tin")
        print("  3. Thoat")
        choice = input("  Chon (1/2/3): ").strip()

        if choice == "3":
            print("  Tam biet!")
            break

        if choice not in ["1", "2"]:
            print("  [!] Chon 1, 2 hoac 3!")
            continue

        # Lay job_title + skills tu CV hoac nhap tay
        if choice == "1":
            cv_path = pick_cv_file()
            print(f"  File: {Path(cv_path).name}")
            cv_text = read_pdf(cv_path)
            data    = extract_cv(cv_text)
            if not data:
                print("  [!] Khong trich xuat duoc CV!")
                continue
            skills_clean   = dedup_skills(data.get("skills", []))
            data["skills"] = skills_clean
            print_cv_result(data, skills_clean)

        else:
            data = input_info()
            print_input(data)

        # Chon tinh nang
        print(f"\n{DASH}")
        print("  a. Goi y skills con thieu")
        print("  b. Lo trinh hoc skills")
        print("  c. Phan tich chuyen huong nghe nghiep")
        print("  d. Quay lai")
        feature = input("  Chon (a/b/c/d): ").strip().lower()

        if feature == "d":
            continue
        elif feature == "a":
            result = recommend_skills(
                cv_skills  = data["skills"],
                job_title  = data["vi_tri_ung_tuyen"],
                index_old  = index_old,
                df_old     = df_old,
                index_new  = index_new,
                df_new     = df_new,
                top_k      = 150,
                top_skills = 10
            )
            print_recommendation(result)
        elif feature == "b":
            result = skill_gap_roadmap(
                cv_skills = data["skills"],
                job_title = data["vi_tri_ung_tuyen"],
                df_old        = df_old,
                index_old = index_old,
                index_new = index_new,  # ← thêm
                df_new    = df_new, 
                top_n     = 5
            )
            print_roadmap(result)
        elif feature == "c":
            handle_career_switch(data, df_old)
        else:
            print("  [!] Chon a, b, c hoac d!")


if __name__ == "__main__":
    main()