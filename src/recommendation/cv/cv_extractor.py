import json
import re
from pathlib import Path
from typing import Any

import fitz
from groq import Groq

from src.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
)


def read_pdf_text(file_path: str | Path) -> str:
    """
    Đọc text từ file PDF bằng PyMuPDF.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file CV: {file_path}")

    if file_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Hiện tại chỉ hỗ trợ PDF. File nhận được: {file_path.suffix}"
        )

    text_parts = []

    with fitz.open(file_path) as pdf:
        for page_index, page in enumerate(pdf):
            page_text = page.get_text("text")

            if page_text:
                text_parts.append(page_text)

    full_text = "\n".join(text_parts)

    # Clean nhẹ text đọc từ PDF
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    full_text = re.sub(r"[ \t]+", " ", full_text)

    return full_text.strip()


def truncate_text(text: str, max_chars: int = 12000) -> str:
    """
    Giới hạn độ dài CV gửi lên LLM để tránh prompt quá dài.
    """
    text = str(text or "").strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars]


def build_cv_extraction_prompt(cv_text: str) -> list[dict[str, str]]:
    """
    Tạo messages gửi lên Groq.
    """
    system_prompt = """
You are an information extraction assistant for CV/resume parsing.

Your task:
Extract only the following fields from the CV text:
1. job_title
2. current_skills
3. location

Return valid JSON only.

Rules:
- job_title: infer the target/current job title from the CV.
  If multiple titles appear, choose the most likely current or target role.
- current_skills: return a clean list of technical/business skills.
  Remove duplicates.
  Keep concise skill names only.
- location: infer the candidate's current/preferred location if present.
  Use format like "Ho Chi Minh, Vietnam", "Hanoi, Vietnam", or "Unknown".
- If a field is missing, use:
  job_title = "Unknown"
  current_skills = []
  location = "Unknown"

Return exactly this JSON structure:
{
  "job_title": "string",
  "current_skills": ["skill 1", "skill 2"],
  "location": "string"
}
""".strip()

    user_prompt = f"""
CV text:

{cv_text}
""".strip()

    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


def safe_json_loads(content: str) -> dict[str, Any]:
    """
    Parse JSON an toàn từ response của LLM.
    """
    content = str(content or "").strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Fallback: cố gắng lấy block JSON trong text nếu model trả kèm chữ
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)

    if not match:
        raise ValueError(f"Không parse được JSON từ Groq response:\n{content}")

    return json.loads(match.group(0))


def normalize_skill(skill: Any) -> str:
    """
    Chuẩn hóa một skill.
    """
    text = str(skill or "").strip()
    text = re.sub(r"\s+", " ", text)

    aliases = {
        "sql": "SQL",
        "power bi": "Power BI",
        "powerbi": "Power BI",
        "excel": "Microsoft Excel",
        "ms excel": "Microsoft Excel",
        "python": "Python",
        "java": "Java",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "nodejs": "Node.js",
        "node.js": "Node.js",
        "reactjs": "React",
        "react": "React",
        "machine learning": "Machine Learning",
        "ml": "Machine Learning",
        "deep learning": "Deep Learning",
        "nlp": "NLP",
        "llm": "LLM",
        "rag": "RAG",
        "etl": "ETL",
        "spark": "Spark",
        "pyspark": "PySpark",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mysql": "MySQL",
        "mongodb": "MongoDB",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "aws": "AWS",
        "azure": "Azure",
    }

    key = text.lower()

    if key in aliases:
        return aliases[key]

    return text


def normalize_extraction_result(data: dict[str, Any]) -> dict[str, Any]:
    """
    Chuẩn hóa kết quả cuối cùng về đúng schema.
    """
    job_title = str(data.get("job_title", "") or "").strip()
    location = str(data.get("location", "") or "").strip()

    if not job_title:
        job_title = "Unknown"

    if not location:
        location = "Unknown"

    raw_skills = data.get("current_skills", [])

    if raw_skills is None:
        raw_skills = []

    if isinstance(raw_skills, str):
        raw_skills = [
            item.strip()
            for item in raw_skills.split(",")
            if item.strip()
        ]

    if not isinstance(raw_skills, list):
        raw_skills = []

    skills = []

    for skill in raw_skills:
        clean_skill = normalize_skill(skill)

        if clean_skill:
            skills.append(clean_skill)

    # Xóa trùng nhưng giữ thứ tự
    skills = list(dict.fromkeys(skills))

    return {
        "job_title": job_title,
        "current_skills": skills,
        "location": location,
    }


def extract_cv_with_groq(cv_text: str) -> dict[str, Any]:
    """
    Gọi Groq để extract thông tin từ text CV.
    """
    if not GROQ_API_KEY:
        raise ValueError(
            "Thiếu GROQ_API_KEY trong .env. Hãy thêm GROQ_API_KEY trước."
        )

    cv_text = truncate_text(cv_text)

    if not cv_text:
        raise ValueError("CV text rỗng, không thể extract.")

    client = Groq(
        api_key=GROQ_API_KEY,
    )

    messages = build_cv_extraction_prompt(cv_text)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0,
        response_format={
            "type": "json_object",
        },
    )

    content = response.choices[0].message.content

    data = safe_json_loads(content)

    return normalize_extraction_result(data)


def extract_cv_file(file_path: str | Path) -> dict[str, Any]:
    """
    Hàm chính:
    PDF path -> text -> Groq extract -> JSON result.
    """
    file_path = Path(file_path)

    cv_text = read_pdf_text(file_path)

    result = extract_cv_with_groq(cv_text)

    return result


def extract_cv_file_with_text(file_path: str | Path) -> dict[str, Any]:
    """
    Hàm debug:
    Trả cả text CV và kết quả extract.
    """
    file_path = Path(file_path)

    cv_text = read_pdf_text(file_path)
    result = extract_cv_with_groq(cv_text)

    return {
        "cv_text": cv_text,
        "extraction": result,
    }