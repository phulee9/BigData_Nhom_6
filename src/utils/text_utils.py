import re
import unicodedata

import pandas as pd

from src.config.silver_config import (
    TECH_REPLACEMENTS,
    TITLE_REMOVE_PHRASES,
    TITLE_REPLACEMENTS,
)


def clean_text(value, keep_numbers=True):
    # Chuẩn hóa text cơ bản
    if pd.isna(value):
        return ""

    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()

    for old_value, new_value in TECH_REPLACEMENTS.items():
        text = text.replace(old_value, new_value)

    text = re.sub(r"[/&+\-%(),#@;:–—_\[\]{}|\\]+", " ", text)
    text = re.sub(r"\.", " ", text)

    if keep_numbers:
        text = re.sub(r"[^a-z0-9\s]", " ", text)
    else:
        text = re.sub(r"[^a-z\s]", " ", text)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def remove_title_phrases(text):
    # Loại cụm không cần thiết trong title
    for phrase in TITLE_REMOVE_PHRASES:
        text = re.sub(rf"\b{re.escape(phrase)}\b", " ", text)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def replace_title_abbreviations(text):
    # Chuẩn hóa viết tắt trong title
    words = text.split()
    words = [TITLE_REPLACEMENTS.get(word, word) for word in words]

    return " ".join(words).strip()


def clean_title(value):
    # Làm sạch cơ bản job title
    text = clean_text(value, keep_numbers=True)
    text = remove_title_phrases(text)
    text = replace_title_abbreviations(text)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_skill_item(value):
    # Làm sạch một skill
    return clean_text(value, keep_numbers=True)


def clean_skills(value):
    # Làm sạch danh sách skills
    if pd.isna(value):
        return ""

    text = str(value)

    text = re.sub(r"[;|/]", ",", text)

    skills = text.split(",")
    cleaned_skills = []

    for skill in skills:
        skill = clean_skill_item(skill)

        if skill:
            cleaned_skills.append(skill)

    cleaned_skills = list(dict.fromkeys(cleaned_skills))

    return ", ".join(cleaned_skills)


def split_skills(value):
    # Tách skills_clean thành list
    if pd.isna(value):
        return []

    value = str(value).strip()

    if value == "":
        return []

    return [
        skill.strip()
        for skill in value.split(",")
        if skill.strip()
    ]