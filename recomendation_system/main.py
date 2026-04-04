import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from recommend     import load_index, recommend_skills, print_recommendation
from roadmap       import skill_gap_roadmap, print_roadmap
from career_switch import career_switch_analysis, print_career_switch


# ── Nhập thông tin chung ───────────────────────────────
def input_info() -> dict:
    print("\n" + "─" * 40)

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

    seen   = set()
    skills = []
    for s in skills_input.split(","):
        s = s.strip().lower()
        if s and s not in seen:
            seen.add(s)
            skills.append(s)

    return {
        "vi_tri_ung_tuyen": job_title.lower().strip(),
        "skills":           skills
    }


# ── In thông tin đã nhập ───────────────────────────────
def print_input(data: dict):
    LINE = "=" * 50
    print(f"\n{LINE}")
    print("  THONG TIN DA NHAP")
    print(LINE)
    print(f"  Vi tri : {data['vi_tri_ung_tuyen']}")
    print(f"\n  Skills ({len(data['skills'])}):")
    for s in data["skills"]:
        print(f"    - {s}")
    print(LINE)


# ── Main ───────────────────────────────────────────────
def main():
    print("\n" + "=" * 50)
    print("  SKILL RECOMMENDER")
    print("  powered by FAISS + Sentence Transformer")
    print("=" * 50)

    print("\n⏳ Khoi dong he thong...")
    index, df = load_index()
    print("✓ San sang!\n")

    while True:
        print("\n" + "─" * 40)
        print("  1. Goi y skills con thieu")
        print("  2. Lo trinh hoc skills")
        print("  3. Phan tich chuyen huong nghe nghiep")
        print("  4. Thoat")
        choice = input("  Chon (1/2/3/4): ").strip()

        if choice == "4":
            print("  Tam biet!")
            break

        if choice not in ["1", "2", "3"]:
            print("  [!] Chon 1, 2, 3 hoac 4!")
            continue

        if choice in ["1", "2"]:
            data = input_info()
            print_input(data)

            if choice == "1":
                result = recommend_skills(
                    cv_skills  = data["skills"],
                    job_title  = data["vi_tri_ung_tuyen"],
                    index      = index,
                    df         = df,
                    top_k      = 150,
                    top_skills = 10
                )
                print_recommendation(result)

            elif choice == "2":
                result = skill_gap_roadmap(
                    cv_skills = data["skills"],
                    job_title = data["vi_tri_ung_tuyen"],
                    df        = df,
                    top_n     = 5
                )
                print_roadmap(result)

        elif choice == "3":
            print("\n" + "─" * 40)

            while True:
                job_from = input(
                    "  Vi tri hien tai: "
                ).strip().lower()
                if job_from:
                    break
                print("  [!] Khong duoc de trong!")

            while True:
                job_to = input(
                    "  Vi tri muon chuyen sang: "
                ).strip().lower()
                if job_to:
                    break
                print("  [!] Khong duoc de trong!")

            print("  Skills hien co (cach nhau bang dau phay):")
            print("  Vi du: docker, linux, git")
            while True:
                skills_input = input("  Skills: ").strip()
                if skills_input:
                    break
                print("  [!] Khong duoc de trong!")

            seen   = set()
            skills = []
            for s in skills_input.split(","):
                s = s.strip().lower()
                if s and s not in seen:
                    seen.add(s)
                    skills.append(s)

            LINE = "=" * 50
            print(f"\n{LINE}")
            print("  THONG TIN DA NHAP")
            print(LINE)
            print(f"  Tu   : {job_from}")
            print(f"  Sang : {job_to}")
            print(f"\n  Skills hien co ({len(skills)}):")
            for s in skills:
                print(f"    - {s}")
            print(LINE)

            result = career_switch_analysis(
                job_from  = job_from,
                job_to    = job_to,
                cv_skills = skills,
                df        = df,
                top_n     = 20
            )
            print_career_switch(result)


if __name__ == "__main__":
    main()