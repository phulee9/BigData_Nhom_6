import re

import pandas as pd

from src.config.silver_config import CITY_ALIASES
from src.utils.text_utils import clean_title, clean_skills
from src.utils.title_utils import process_title_columns


def clean_text(value):
    # Chuẩn hóa text cơ bản
    if pd.isna(value):
        return ""

    return str(value).strip()


def normalize_location_text(value):
    # Chuẩn hóa location
    text = clean_text(value).lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_city(city):
    # Chuẩn hóa tên tỉnh/thành
    city = normalize_location_text(city)

    return CITY_ALIASES.get(city, city)


def parse_location(location):
    # Tách location thành city và country
    location = normalize_location_text(location)

    if location == "":
        return "", ""

    parts = [
        part.strip()
        for part in location.split(",")
        if part.strip() != ""
    ]

    if len(parts) == 1:
        if parts[0] in {"vietnam", "viet nam"}:
            return "", "vietnam"

        return normalize_city(parts[0]), ""

    if parts[-1] in {"vietnam", "viet nam"}:
        city = " ".join(parts[:-1]).strip()
        return normalize_city(city), "vietnam"

    if parts[0] in {"vietnam", "viet nam"}:
        city = " ".join(parts[1:]).strip()
        return normalize_city(city), "vietnam"

    return normalize_city(parts[0]), parts[-1]


def clean_skill_list(skills):
    # Clean skills crawler cơ bản
    if not isinstance(skills, list):
        return ""

    cleaned_skills = []

    for skill in skills:
        skill = clean_text(skill)

        if skill == "":
            continue

        if skill.lower() in {"null", "none", "nan"}:
            continue

        skill_clean = clean_skills(skill)

        for item in skill_clean.split(","):
            item = item.strip()

            if item == "":
                continue

            if item.lower() in {"null", "none", "nan"}:
                continue

            if item not in cleaned_skills:
                cleaned_skills.append(item)

    return ", ".join(cleaned_skills)


def prepare_raw_dataframe(raw_jobs):
    # Chuyển JSON list thành dataframe
    jobs = pd.DataFrame(raw_jobs)

    required_columns = [
        "title",
        "company",
        "location",
        "link",
        "skills",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in jobs.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    jobs = jobs[required_columns].copy()

    jobs = jobs.rename(
        columns={
            "title": "title_raw",
            "location": "location_raw",
            "skills": "skills_raw",
        }
    )

    return jobs


def remove_invalid_and_duplicate_links(jobs):
    # Loại title/link rỗng và duplicate link, giữ bản ghi đầu tiên
    jobs = jobs.copy()

    jobs["title_raw"] = jobs["title_raw"].apply(clean_text)
    jobs["link"] = jobs["link"].apply(clean_text)

    jobs = jobs[
        (jobs["title_raw"] != "")
        & (jobs["link"] != "")
    ].copy()

    before_rows = len(jobs)

    jobs = jobs.drop_duplicates(
        subset=["link"],
        keep="first",
    ).copy()

    after_rows = len(jobs)

    print(f"Rows before removing duplicate links: {before_rows:,}")
    print(f"Rows after removing duplicate links: {after_rows:,}")
    print(f"Removed duplicate links: {before_rows - after_rows:,}")

    return jobs


def clean_crawler_jobs(raw_jobs, week):
    # Clean dữ liệu crawler tuần mới
    jobs = prepare_raw_dataframe(raw_jobs)

    jobs = remove_invalid_and_duplicate_links(jobs)

    jobs["company"] = jobs["company"].apply(clean_text)
    jobs["location_raw"] = jobs["location_raw"].apply(clean_text)

    jobs["title_clean"] = jobs["title_raw"].apply(clean_title)

    jobs = process_title_columns(jobs)

    jobs["skills_clean"] = jobs["skills_raw"].apply(clean_skill_list)

    location_values = jobs["location_raw"].apply(parse_location)

    jobs["city"] = location_values.apply(lambda value: value[0])
    jobs["country"] = location_values.apply(lambda value: value[1])

    jobs["source"] = "monster"
    jobs["crawl_week"] = week

    output_columns = [
        "title_raw",
        "title_clean",
        "title_lemma",
        "title_core",
        "seniority",
        "work_mode",
        "employment_type",

        "company",
        "location_raw",
        "city",
        "country",
        "link",

        "skills_raw",
        "skills_clean",

        "source",
        "crawl_week",
    ]

    return jobs[output_columns].copy()