import json
import os

import fitz
from dotenv import load_dotenv
from groq import Groq

from recommendation.core.preprocess import (
    normalize_location,
    normalize_skill,
    process_job_title,
)

load_dotenv()


# ===============================
# READ PDF
# ===============================
def read_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Không tìm thấy file CV: {pdf_path}")

    text = ""

    doc = fitz.open(pdf_path)

    for page in doc:
        text += page.get_text()

    return text


# ===============================
# CALL GROQ
# ===============================
def extract_cv_with_groq(cv_text):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("Thiếu GROQ_API_KEY trong file .env")

    client = Groq(api_key=api_key)

    prompt = f"""
Extract structured information from this CV.

Return ONLY valid JSON with this schema:
{{
  "job_title": "target job title or most relevant professional role",
  "skills": ["skill1", "skill2"],
  "location": "country name only"
}}

Rules:
- job_title phải là vị trí chính (ví dụ: data analyst, backend developer)
- skills phải là kỹ năng thực tế (tool, tech, framework, domain knowledge)
- location MUST be normalized to COUNTRY LEVEL only (not city)

Location rules (VERY IMPORTANT):
- Convert any city/state → country
  Example:
    "Ho Chi Minh", "Hanoi" → "Vietnam"
    "New York", "California" → "United States"
    "London" → "United Kingdom"
- If multiple locations → choose the most recent or most relevant
- If remote but có quốc gia → vẫn trả quốc gia
- If only "Remote" and không có quốc gia → return "remote"
- If không xác định được → return "other"

Output format:
- Lowercase
- Country name in English
  Example:
    "vietnam"
    "united states"
    "united kingdom"

CV:
{cv_text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You extract structured data from CVs. Return JSON only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


# ===============================
# CLEAN DATA
# ===============================
def normalize_cv_data(cv_data):
    job_title_raw = cv_data.get("job_title", "")
    location_raw = cv_data.get("location", "other")
    skills_raw = cv_data.get("skills", [])

    job_title = process_job_title(job_title_raw)
    location = normalize_location(location_raw)

    skills = sorted(
        list(
            set(
                normalize_skill(skill)
                for skill in skills_raw
                if normalize_skill(skill)
            )
        )
    )

    return {
        "job_title": job_title,
        "location": location,
        "skills": skills,
    }


# ===============================
# MAIN PIPELINE
# ===============================
def extract_and_prepare_cv(pdf_path):
    print("\n📄 Đang đọc CV...")
    cv_text = read_pdf(pdf_path)

    print("🤖 Đang trích xuất thông tin bằng Groq...")
    cv_data = extract_cv_with_groq(cv_text)

    print("🧹 Đang clean dữ liệu...")
    cv_input = normalize_cv_data(cv_data)

    # ===== CHỈ PRINT CLEANED DATA =====
    print("\n===== CLEANED DATA =====")
    print(f"Job Title : {cv_input['job_title']}")
    print(f"Location  : {cv_input['location']}")
    print(f"Skills    : {', '.join(cv_input['skills'])}")

    return cv_input