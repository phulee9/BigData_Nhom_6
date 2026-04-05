import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

try:
    import fitz
except ImportError:
    sys.exit("[LOI] pip install pymupdf")

try:
    from groq import Groq
except ImportError:
    sys.exit("[LOI] pip install groq")

from recommend     import load_index, recommend_skills, print_recommendation
from roadmap       import skill_gap_roadmap, print_roadmap
from career_switch import career_switch_analysis, print_career_switch


# ── 1. Chọn file CV ────────────────────────────────────
def pick_cv_file() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()

        print("  Mo hop thoai chon file...")
        file_path = filedialog.askopenfilename(
            title="Chon file CV (PDF)",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        root.destroy()

        if not file_path:
            sys.exit("  [!] Chua chon file. Thoat.")
        return file_path

    except Exception:
        print("  Nhap duong dan file CV:")
        print("  Vi du: C:\\Users\\ten\\Downloads\\cv.pdf")
        while True:
            path = input("\n  >>> ").strip().strip("'\"")
            if not path:
                continue
            if not os.path.exists(path):
                print(f"  [!] Khong tim thay: {path}")
                continue
            if not path.lower().endswith(".pdf"):
                print("  [!] Can file .pdf")
                continue
            return path


# ── 2. Đọc PDF ─────────────────────────────────────────
def read_pdf(pdf_path: str) -> str:
    print("  Dang doc PDF...")
    try:
        pages = []
        doc   = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        doc.close()
    except Exception as e:
        sys.exit(f"  [LOI] Doc PDF that bai: {e}")

    if not pages:
        sys.exit("  [LOI] Khong doc duoc text. PDF co the la file scan anh.")

    full_text = "\n".join(pages)
    print(f"  [OK] Doc duoc {len(pages)} trang, {len(full_text)} ky tu")
    return full_text


# ── 3. Groq extract CV ─────────────────────────────────
SYSTEM_PROMPT_CV = """You are a CV skill extractor.

Your task: Read the CV and extract ONLY the 5 most important skills for the applied job position.

Rules:
- Choose skills that are most relevant to the job title in the CV
- KEEP: programming languages, frameworks, tools, software, certifications, technical skills
- REMOVE: soft skills, personality traits, vague phrases, company names, school names
- Return exactly 5 skills, ranked by importance (most important first)

Output ONLY this JSON, nothing else:
{
  "vi_tri_ung_tuyen": "job title in lowercase",
  "skills": ["skill1", "skill2", "skill3", "skill4", "skill5"]
}"""

USER_PROMPT_CV = """Read this CV and extract the job title and the 5 most important skills for that position:

{cv_text}

Return ONLY the JSON, no extra text."""


def call_groq_cv(cv_text: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY") or \
              os.environ.get("GROQ_API_KEY_1")
    if not api_key:
        sys.exit(
            "\n  [LOI] Khong co GROQ_API_KEY trong .env\n"
            "        Lay key tai: https://console.groq.com"
        )

    client = Groq(api_key=api_key)
    print("  Dang phan tich CV voi Groq...")
    t0 = time.time()

    try:
        response = client.chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_CV},
                {"role": "user",   "content": USER_PROMPT_CV.format(
                    cv_text=cv_text[:8000]
                )}
            ],
            temperature     = 0.0,
            max_tokens      = 1024,
            response_format = {"type": "json_object"}
        )
        raw = response.choices[0].message.content.strip()

    except Exception as e:
        sys.exit(f"\n  [LOI] Groq API: {e}")

    elapsed = time.time() - t0
    print(f"  [OK] Phan tich xong ({elapsed:.1f}s)")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("  [CANH BAO] Khong parse duoc JSON")
        return {}


# ── 4. Dedup skills ────────────────────────────────────
def dedup_skills(skills_raw: list) -> list:
    seen   = set()
    result = []
    for s in skills_raw:
        s_clean = s.lower().strip()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            result.append(s_clean)
    return result


# ── 5. In kết quả CV ──────────────────────────────────
def print_cv_result(data: dict, skills_clean: list):
    LINE = "=" * 50
    print(f"\n{LINE}")
    print("  KET QUA TRICH XUAT CV")
    print(LINE)
    print(f"  Vi tri : {data.get('vi_tri_ung_tuyen') or 'Khong tim thay'}")
    print(f"\n  Skills quan trong ({len(skills_clean)}):")
    for s in skills_clean:
        print(f"    - {s}")
    print(LINE)


# ── 6. Nhập tay thông tin ─────────────────────────────
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


# ── 7. In thông tin đã nhập ───────────────────────────
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


# ── 8. Main ────────────────────────────────────────────
def main():
    print("\n" + "=" * 50)
    print("  SKILL RECOMMENDER")
    print("  powered by FAISS + Sentence Transformer")
    print("=" * 50)

    # Load index 1 lần duy nhất
    print("\n⏳ Khoi dong he thong...")
    index, df = load_index()
    print("✓ San sang!\n")

    while True:
        print("\n" + "─" * 40)
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

        # ── Lấy job_title + skills ────────────────────
        if choice == "1":
            # Extract từ CV
            cv_path = pick_cv_file()
            print(f"  File: {Path(cv_path).name}")
            cv_text      = read_pdf(cv_path)
            data         = call_groq_cv(cv_text)
            if not data:
                print("  [!] Khong trich xuat duoc CV!")
                continue
            skills_clean = dedup_skills(data.get("skills", []))
            data["skills"] = skills_clean
            print_cv_result(data, skills_clean)

        elif choice == "2":
            # Nhập tay
            data = input_info()
            print_input(data)

        # ── Chọn tính năng ────────────────────────────
        print("\n" + "─" * 40)
        print("  a. Goi y skills con thieu")
        print("  b. Lo trinh hoc skills")
        print("  c. Phan tich chuyen huong nghe nghiep")
        print("  d. Quay lai")
        feature = input("  Chon (a/b/c/d): ").strip().lower()

        if feature == "d":
            continue

        if feature == "a":
            result = recommend_skills(
                cv_skills  = data["skills"],
                job_title  = data["vi_tri_ung_tuyen"],
                index      = index,
                df         = df,
                top_k      = 150,
                top_skills = 10
            )
            print_recommendation(result)

        elif feature == "b":
            result = skill_gap_roadmap(
                cv_skills = data["skills"],
                job_title = data["vi_tri_ung_tuyen"],
                df        = df,
                top_n     = 5
            )
            print_roadmap(result)

        elif feature == "c":
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

            LINE = "=" * 50
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

        else:
            print("  [!] Chon a, b, c hoac d!")


if __name__ == "__main__":
    main()