import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from recommend import load_index, recommend_skills, print_recommendation


# ── Nhập tay thông tin ─────────────────────────────────
def input_manual() -> dict:
    print("\n" + "─" * 40)

    # Nhập vị trí
    while True:
        job_title = input("  Nhap vi tri ung tuyen: ").strip()
        if job_title:
            break
        print("  [!] Khong duoc de trong!")

    # Nhập skills
    print("  Nhap skills (cach nhau bang dau phay)")
    print("  Vi du: python, sql, machine learning")
    while True:
        skills_input = input("  Skills: ").strip()
        if skills_input:
            break
        print("  [!] Khong duoc de trong!")

    # Parse skills
    skills = [
        s.strip().lower()
        for s in skills_input.split(",")
        if s.strip()
    ]

    # Dedup
    seen   = set()
    skills_clean = []
    for s in skills:
        if s and s not in seen:
            seen.add(s)
            skills_clean.append(s)

    return {
        "vi_tri_ung_tuyen": job_title.lower().strip(),
        "skills":           skills_clean
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
    print("=" * 50)

    # Load index 1 lần
    print("\n⏳ Khoi dong he thong...")
    index, df = load_index()
    print("✓ San sang!\n")

    # Loop
    while True:
        print("\n" + "─" * 40)
        print("  1. Goi y skills")
        print("  2. Thoat")
        choice = input("  Chon (1/2): ").strip()

        if choice == "2":
            print("  Tam biet!")
            break

        if choice != "1":
            print("  [!] Chon 1 hoac 2!")
            continue

        # Nhập tay
        data = input_manual()
        print_input(data)

        # Recommend
        result = recommend_skills(
            cv_skills  = data["skills"],
            job_title  = data["vi_tri_ung_tuyen"],
            index      = index,
            df         = df,
            top_k      = 10,
            top_skills = 10
        )

        print_recommendation(result)

        # Lưu kết quả
        filename = data["vi_tri_ung_tuyen"].replace(" ", "_")
        out = f"{filename}_recommendation.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Da luu: {out}\n")


if __name__ == "__main__":
    main()