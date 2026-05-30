"""
Text and skill utilities.
Dùng chung cho BM25, FAISS skill recommendation và job recommendation.
"""

import ast
import re
from typing import Any

import numpy as np
import pandas as pd


def normalize_text_lower(value: Any) -> str:
    # Chuẩn hóa text về lowercase
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_token(value: Any) -> str:
    # Chuẩn hóa token để so sánh skill
    text = normalize_text_lower(value)
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def parse_skills_lower(value: Any) -> list[str]:
    # Chuyển skills về list lowercase
    if value is None:
        return []

    if isinstance(value, float) and pd.isna(value):
        return []

    if isinstance(value, np.ndarray):
        value = value.tolist()

    if isinstance(value, (list, tuple, set)):
        raw_skills = list(value)

    elif isinstance(value, str):
        text = value.strip()

        if text.lower() in ["", "[]", "nan", "none", "null"]:
            return []

        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, (list, tuple, set)):
                raw_skills = list(parsed)
            else:
                raw_skills = text.split(",")

        except Exception:
            raw_skills = text.split(",")

    else:
        raw_skills = [value]

    skills = []

    for skill in raw_skills:
        skill = normalize_text_lower(skill)

        if skill and skill not in skills:
            skills.append(skill)

    return skills


def skills_to_text(skills: list[str]) -> str:
    # Chuyển list skills thành text để đưa vào query
    clean_skills = [
        normalize_text_lower(skill)
        for skill in skills
        if normalize_text_lower(skill)
    ]

    if not clean_skills:
        return "not specified"

    return ", ".join(clean_skills)