import json
import os
import sys
import time
import fitz
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

SYSTEM_PROMPT = """You are a CV skill extractor.
Extract ONLY the 5 most important skills for the applied job position.
Rules:
- KEEP: programming languages, frameworks, tools, software, certifications
- REMOVE: soft skills, personality traits, company names, school names
- Return exactly 5 skills ranked by importance

Output ONLY this JSON, nothing else:
{
  "vi_tri_ung_tuyen": "job title in lowercase",
  "skills": ["skill1", "skill2", "skill3", "skill4", "skill5"]
}"""


def pick_cv_file() -> str:
    # Mở hộp thoại chọn file, fallback nhập tay nếu không có tkinter
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
            raise Exception("Chua chon file CV!")
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


def read_pdf(file_input) -> str:
    # Đọc text từ PDF, hỗ trợ cả đường dẫn và Streamlit file object
    try:
        if hasattr(file_input, "read"):
            doc = fitz.open(stream=file_input.read(), filetype="pdf")
        else:
            doc = fitz.open(str(file_input))

        pages = []
        for page in doc:
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        doc.close()

        if not pages:
            raise Exception("Khong doc duoc text. PDF co the la file scan anh.")

        full_text = "\n".join(pages)
        print(f"  [OK] Doc duoc {len(pages)} trang, {len(full_text)} ky tu")
        return full_text

    except Exception as e:
        raise Exception(f"Doc PDF that bai: {e}")


def extract_cv(cv_text: str) -> dict:
    # Gọi Groq extract job_title + 5 skills quan trọng nhất
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY_1")
    if not api_key:
        raise Exception(
            "Khong co GROQ_API_KEY trong .env!\n"
            "Lay key tai: https://console.groq.com"
        )

    print("  Dang phan tich CV voi Groq...")
    t0 = time.time()

    try:
        response = Groq(api_key=api_key).chat.completions.create(
            model           = "llama-3.3-70b-versatile",
            messages        = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Extract from this CV:\n\n{cv_text[:8000]}"}
            ],
            temperature     = 0.0,
            max_tokens      = 1024,
            response_format = {"type": "json_object"}
        )
        print(f"  [OK] Phan tich xong ({time.time() - t0:.1f}s)")
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        raise Exception(f"Groq API that bai: {e}")


def dedup_skills(skills_raw: list) -> list:
    # Loại bỏ skills trùng lặp, giữ thứ tự
    seen, result = set(), []
    for s in skills_raw:
        s_clean = s.lower().strip()
        if s_clean and s_clean not in seen:
            seen.add(s_clean)
            result.append(s_clean)
    return result