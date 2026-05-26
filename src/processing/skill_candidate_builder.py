import pandas as pd

from src.utils.text_utils import split_skills


def explode_skills(jobs):
    # Tách skills_clean thành từng dòng skill
    skills_df = jobs[["job_id", "skills_clean"]].copy()

    skills_df["skill_original"] = skills_df["skills_clean"].apply(split_skills)
    skills_df = skills_df.explode("skill_original")

    skills_df["skill_original"] = (
        skills_df["skill_original"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    skills_df = skills_df[skills_df["skill_original"] != ""].copy()

    return skills_df[["job_id", "skill_original"]]


def count_unique_skills(skills_df):
    # Đếm tần suất skill
    skill_frequency = (
        skills_df.groupby("skill_original")
        .size()
        .reset_index(name="freq")
        .sort_values("freq", ascending=False)
        .reset_index(drop=True)
    )

    skill_frequency["word_count"] = (
        skill_frequency["skill_original"]
        .astype(str)
        .str.split()
        .str.len()
    )

    return skill_frequency


def filter_skill_candidates(skill_frequency, min_freq=200, max_words=4):
    # Lọc skill đủ điều kiện gửi Groq
    candidates = skill_frequency[
        (skill_frequency["freq"] >= min_freq)
        & (skill_frequency["word_count"] <= max_words)
    ].copy()

    candidates = candidates.reset_index(drop=True)

    return candidates


def build_skill_candidates(jobs, min_freq=200, max_words=4):
    # Build skill frequency và candidates
    skills_df = explode_skills(jobs)
    skill_frequency = count_unique_skills(skills_df)

    skill_candidates = filter_skill_candidates(
        skill_frequency=skill_frequency,
        min_freq=min_freq,
        max_words=max_words,
    )

    return skill_frequency, skill_candidates