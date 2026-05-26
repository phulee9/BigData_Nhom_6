import pandas as pd

from src.utils.text_utils import split_skills


def validate_mapping_columns(mapping):
    # Kiểm tra cột bắt buộc
    required_columns = [
        "skill_original",
        "keep",
        "skill_normalized",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in mapping.columns
    ]

    if missing_columns:
        raise ValueError(f"skill mapping missing columns: {missing_columns}")


def load_skill_mapping(mapping_path):
    # Đọc skill mapping
    mapping = pd.read_csv(mapping_path)

    validate_mapping_columns(mapping)

    mapping = mapping[
        [
            "skill_original",
            "keep",
            "skill_normalized",
        ]
    ].copy()

    mapping["skill_original"] = (
        mapping["skill_original"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    mapping["skill_normalized"] = (
        mapping["skill_normalized"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    mapping["keep"] = pd.to_numeric(
        mapping["keep"],
        errors="coerce",
    ).fillna(0).astype(int)

    mapping = mapping[mapping["skill_original"] != ""].copy()

    return mapping


def build_mapping_dict(mapping):
    # Chuyển mapping thành dictionary
    return {
        row.skill_original: {
            "keep": int(row.keep),
            "skill_normalized": row.skill_normalized,
        }
        for row in mapping.itertuples(index=False)
    }


def normalize_skill_list(skills_clean, mapping_dict):
    # Chỉ giữ skill có trong mapping và keep = 1
    normalized_skills = []

    for skill in split_skills(skills_clean):
        item = mapping_dict.get(skill)

        if item is None:
            continue

        if item["keep"] != 1:
            continue

        skill_normalized = item["skill_normalized"]

        if skill_normalized == "":
            continue

        if skill_normalized not in normalized_skills:
            normalized_skills.append(skill_normalized)

    return ", ".join(normalized_skills)


def apply_skill_mapping(jobs, mapping_path):
    # Apply skill mapping vào Silver
    jobs = jobs.copy()

    mapping = load_skill_mapping(mapping_path)
    mapping_dict = build_mapping_dict(mapping)

    jobs["skills_normalized"] = jobs["skills_clean"].apply(
        lambda value: normalize_skill_list(value, mapping_dict)
    )

    return jobs