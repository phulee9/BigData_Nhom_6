import re

import pandas as pd
import spacy

from src.config.silver_config import (
    EMPLOYMENT_TYPE_KEYWORDS,
    SENIORITY_KEYWORDS,
    TITLE_REMOVE_TOKENS,
    WORK_MODE_KEYWORDS,
)


def load_spacy_model():
    # Load spaCy model
    return spacy.load(
        "en_core_web_sm",
        disable=["parser", "ner"],
    )


def lemmatize_titles(title_series, batch_size=1000):
    # Lemmatize title bằng spaCy theo batch
    nlp = load_spacy_model()

    titles = (
        title_series
        .fillna("")
        .astype(str)
        .tolist()
    )

    results = []

    for doc in nlp.pipe(titles, batch_size=batch_size):
        tokens = []

        for token in doc:
            if token.is_punct or token.is_space:
                continue

            lemma = token.lemma_.lower().strip()

            if lemma:
                tokens.append(lemma)

        results.append(" ".join(tokens))

    return results


def find_phrase(text, keyword_dict):
    # Tìm keyword phrase trong text
    for keyword, value in keyword_dict.items():
        pattern = rf"\b{re.escape(keyword)}\b"

        if re.search(pattern, text):
            return value

    return ""


def extract_seniority(title):
    # Tách cấp bậc title
    if pd.isna(title):
        return ""

    return find_phrase(str(title), SENIORITY_KEYWORDS)


def extract_work_mode(title):
    # Tách hình thức làm việc
    if pd.isna(title):
        return ""

    return find_phrase(str(title), WORK_MODE_KEYWORDS)


def extract_employment_type(title):
    # Tách loại hình công việc
    if pd.isna(title):
        return ""

    return find_phrase(str(title), EMPLOYMENT_TYPE_KEYWORDS)


def remove_phrases(text, keyword_dict):
    # Xóa phrase đã được tách khỏi title
    for keyword in keyword_dict.keys():
        text = re.sub(
            rf"\b{re.escape(keyword)}\b",
            " ",
            text,
        )

    return re.sub(r"\s+", " ", text).strip()


def build_title_core(title_lemma):
    # Tạo title chính sau khi bỏ metadata
    if pd.isna(title_lemma):
        return ""

    text = str(title_lemma)

    text = remove_phrases(text, SENIORITY_KEYWORDS)
    text = remove_phrases(text, WORK_MODE_KEYWORDS)
    text = remove_phrases(text, EMPLOYMENT_TYPE_KEYWORDS)

    words = [
        word
        for word in text.split()
        if word not in TITLE_REMOVE_TOKENS
    ]

    return " ".join(words).strip()


def process_title_columns(jobs):
    # Tạo các cột title đã xử lý
    jobs = jobs.copy()

    jobs["title_lemma"] = lemmatize_titles(
        jobs["title_clean"],
        batch_size=1000,
    )

    jobs["seniority"] = jobs["title_lemma"].apply(extract_seniority)
    jobs["work_mode"] = jobs["title_lemma"].apply(extract_work_mode)
    jobs["employment_type"] = jobs["title_lemma"].apply(extract_employment_type)

    jobs["title_core"] = jobs["title_lemma"].apply(build_title_core)

    return jobs