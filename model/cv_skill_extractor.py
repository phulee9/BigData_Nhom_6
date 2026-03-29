import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

try:
    import fitz  # pymupdf
except ImportError:
    sys.exit("[LOI] pip install pymupdf")

try:
    from groq import Groq
except ImportError:
    sys.exit("[LOI] pip install groq")


# 1. Chon file CV

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


# 2. Doc text tu PDF

def read_pdf(pdf_path: str) -> str:
    print("  Dang doc PDF...")
    try:
        pages = []
        doc = fitz.open(pdf_path)
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


# 3. Goi Groq API

SYSTEM_PROMPT = """Ban la mot cong cu trich xuat thong tin tu CV.
NHIEM VU DUY NHAT: Doc CV va tra ve JSON voi dung 3 truong.
TUYET DOI KHONG duoc viet bat cu text nao ngoai JSON.
TUYET DOI KHONG lap lai noi dung CV.
Chi tra ve dung dinh dang JSON nay va khong gi khac:
{
  "vi_tri_ung_tuyen": "...",
  "dia_diem": "...",
  "skills": ["...", "..."]
}"""

USER_PROMPT = """Trich xuat thong tin tu CV nay va tra ve JSON:

{cv_text}

Nho: Chi tra ve JSON, khong them bat ky text nao khac."""


def call_groq(cv_text: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        sys.exit(
            "\n  [LOI] Khong co GROQ_API_KEY trong file .env\n"
            "        Them vao file .env: GROQ_API_KEY=gsk_...\n"
            "        Lay key tai: https://console.groq.com"
        )

    client = Groq(api_key=api_key)

    print("  Dang phan tich CV voi Groq...")
    t0 = time.time()

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": USER_PROMPT.format(cv_text=cv_text[:8000])}
            ],
            temperature=0.0,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content.strip()

    except Exception as e:
        sys.exit(f"\n  [LOI] Groq API: {e}")

    elapsed = time.time() - t0
    print(f"  [OK] Phan tich xong ({elapsed:.1f}s)")

    # Bo markdown neu co
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip().lstrip("json").strip()
            if part.startswith("{"):
                raw = part
                break

    # Tim va parse JSON
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError:
        pass

    print("  [CANH BAO] Khong parse duoc JSON:")
    print(raw[:300])
    return {}


# 4. In ket qua

def print_result(data: dict):
    LINE = "=" * 50
    print(f"\n{LINE}")
    print("  KET QUA TRICH XUAT")
    print(LINE)
    print(f"  Vi tri ung tuyen : {data.get('vi_tri_ung_tuyen') or 'Khong tim thay'}")
    print(f"  Dia diem         : {data.get('dia_diem') or 'Khong tim thay'}")
    skills = data.get("skills", [])
    print(f"\n  Skills ({len(skills)} ky nang):")
    for s in skills:
        print(f"    - {s}")
    print(LINE)


# 5. Main

def main():
    print("\n" + "=" * 50)
    print("  CV SKILL EXTRACTOR  (powered by Groq)")
    print("=" * 50)

    cv_path = pick_cv_file()
    print(f"  File: {Path(cv_path).name}")

    cv_text = read_pdf(cv_path)

    data = call_groq(cv_text)

    if data:
        print_result(data)
        out = Path(cv_path).stem + "_result.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n  Da luu: {out}\n")
    else:
        print("  [!] Khong trich xuat duoc du lieu.")


if __name__ == "__main__":
    main()