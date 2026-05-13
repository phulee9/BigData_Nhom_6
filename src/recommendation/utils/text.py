"""
Text & Skill parsing utilities.

Dùng chung cho model_tfidf.py và recommend.py.
"""

import ast
import re
from typing import Any

import numpy as np
import pandas as pd


def normalize_text_lower(value: Any) -> str:
    """Chuẩn hóa text về lowercase, bỏ ký tự thừa."""
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def parse_skills_lower(value: Any) -> list[str]:
    """
    Chuyển skills_canonical về list[str] lowercase.

    Hỗ trợ: list, string dạng "['a','b']", string dạng "a, b".
    """
    if value is None:
        return []

    if isinstance(value, float) and pd.isna(value):
        return []

    if hasattr(value, 'tolist') and callable(value.tolist):
        try:
            value = value.tolist()
        except Exception:
            pass

    if isinstance(value, list):
        return [normalize_text_lower(s) for s in value if normalize_text_lower(s)]

    if isinstance(value, str):
        text = value.strip()

        if text.lower() in ["", "[]", "nan", "none", "null"]:
            return []

        try:
            parsed = ast.literal_eval(text)

            if isinstance(parsed, (list, tuple, set)):
                return [normalize_text_lower(s) for s in parsed if normalize_text_lower(s)]
        except Exception:
            pass

        if "," in text:
            return [s.strip().lower() for s in text.split(",") if s.strip()]

        return [text.lower()]

    return []
