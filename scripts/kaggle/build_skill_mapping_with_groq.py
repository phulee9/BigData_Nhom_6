import os
import sys
import time

import pandas as pd

sys.path.append(os.getcwd())

from scripts.minio.minio_client import (
    MINIO_BUCKET,
    get_minio_client,
)
from src.llm.groq_client import call_groq_json
from src.processing.skill_candidate_builder import build_skill_candidates


SILVER_INPUT_PATH = "silver/kaggle/jobs_silver.parquet"
LOCAL_SILVER_PATH = "data/temp/jobs_silver.parquet"

SKILL_FREQUENCY_OUTPUT = "data/check/skill_frequency.csv"
SKILL_CANDIDATES_OUTPUT = "data/mapping/skill_candidates.parquet"

SKILL_MAPPING_OUTPUT = "data/mapping/skill_alias_mapping.csv"
SKILL_WHITELIST_OUTPUT = "data/mapping/skill_whitelist.csv"

MIN_SKILL_FREQ = 200
MAX_SKILL_WORDS = 4
BATCH_SIZE = 150
SLEEP_SECONDS = 50


def download_silver_file(client):
    # Tải Silver từ MinIO
    os.makedirs(os.path.dirname(LOCAL_SILVER_PATH), exist_ok=True)

    client.fget_object(
        bucket_name=MINIO_BUCKET,
        object_name=SILVER_INPUT_PATH,
        file_path=LOCAL_SILVER_PATH,
    )


def read_silver_file():
    # Đọc Silver local
    return pd.read_parquet(LOCAL_SILVER_PATH)


def save_skill_frequency(skill_frequency, skill_candidates):
    # Lưu file check và candidate
    os.makedirs(os.path.dirname(SKILL_FREQUENCY_OUTPUT), exist_ok=True)
    os.makedirs(os.path.dirname(SKILL_CANDIDATES_OUTPUT), exist_ok=True)

    skill_frequency.to_csv(
        SKILL_FREQUENCY_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    skill_candidates.to_parquet(
        SKILL_CANDIDATES_OUTPUT,
        index=False,
    )


def split_batches(dataframe, batch_size):
    # Chia dataframe thành batch
    for start in range(0, len(dataframe), batch_size):
        yield dataframe.iloc[start:start + batch_size]


def build_skill_prompt(batch):
    # Tạo prompt cho Groq
    skills = batch[["skill_original", "freq", "word_count"]].to_dict("records")

    return f"""
You are cleaning a list of job skills.

For each input skill:
- keep = 1 if it is a real job skill
- keep = 0 if it is noise, job description text, benefit text, or not a skill
- skill_normalized should be a clean standard skill name
- Do not explain
- Return JSON only

Examples:
powerbi -> power bi
ms excel -> excel
node js -> nodejs
team player -> teamwork
equal opportunity employer -> keep 0

Input skills:
{skills}

Return JSON in this exact format:
{{
  "items": [
    {{
      "skill_original": "powerbi",
      "keep": 1,
      "skill_normalized": "power bi"
    }}
  ]
}}
""".strip()


def parse_groq_items(result, batch):
    # Chuẩn hóa output Groq
    items = result.get("items", [])
    item_map = {}

    for item in items:
        skill_original = str(item.get("skill_original", "")).strip()
        keep = item.get("keep", 0)
        skill_normalized = str(item.get("skill_normalized", "")).strip()

        if skill_original == "":
            continue

        try:
            keep = int(keep)
        except Exception:
            keep = 0

        item_map[skill_original] = {
            "keep": keep,
            "skill_normalized": skill_normalized,
        }

    rows = []

    for row in batch.itertuples(index=False):
        skill_original = row.skill_original
        item = item_map.get(skill_original)

        if item is None:
            rows.append(
                {
                    "skill_original": skill_original,
                    "keep": 1,
                    "skill_normalized": skill_original,
                    "freq": row.freq,
                    "word_count": row.word_count,
                }
            )
        else:
            rows.append(
                {
                    "skill_original": skill_original,
                    "keep": item["keep"],
                    "skill_normalized": item["skill_normalized"],
                    "freq": row.freq,
                    "word_count": row.word_count,
                }
            )

    return rows


def clean_skills_with_groq(skill_candidates):
    # Gửi skill candidates lên Groq
    results = []
    batches = list(split_batches(skill_candidates, BATCH_SIZE))

    for batch_index, batch in enumerate(batches, start=1):
        print(f"Batch {batch_index}/{len(batches)} - skills: {len(batch):,}")

        try:
            prompt = build_skill_prompt(batch)
            result = call_groq_json(prompt)
            rows = parse_groq_items(result, batch)
            results.extend(rows)

        except Exception as error:
            print(f"Batch {batch_index} failed: {error}")
            print("Stop here. Run again later if needed.")
            break

        time.sleep(SLEEP_SECONDS)

    return pd.DataFrame(results)


def save_skill_mapping(skill_mapping):
    # Lưu mapping và whitelist
    os.makedirs(os.path.dirname(SKILL_MAPPING_OUTPUT), exist_ok=True)

    skill_mapping = skill_mapping.drop_duplicates(
        subset=["skill_original"],
        keep="last",
    )

    skill_mapping.to_csv(
        SKILL_MAPPING_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    whitelist = (
        skill_mapping[
            (skill_mapping["keep"] == 1)
            & (skill_mapping["skill_normalized"].fillna("").astype(str).str.strip() != "")
        ][["skill_normalized"]]
        .drop_duplicates()
        .sort_values("skill_normalized")
        .reset_index(drop=True)
    )

    whitelist.to_csv(
        SKILL_WHITELIST_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )


def main():
    client = get_minio_client()

    print("Downloading Silver file...")
    download_silver_file(client)

    print("Reading Silver file...")
    jobs = read_silver_file()

    print(f"Silver rows: {len(jobs):,}")

    print("Counting unique skills...")
    skill_frequency, skill_candidates = build_skill_candidates(
        jobs=jobs,
        min_freq=MIN_SKILL_FREQ,
        max_words=MAX_SKILL_WORDS,
    )

    print(f"Unique skills: {len(skill_frequency):,}")
    print(f"Skill candidates: {len(skill_candidates):,}")

    print("Saving skill frequency and candidates...")
    save_skill_frequency(
        skill_frequency=skill_frequency,
        skill_candidates=skill_candidates,
    )

    print("Calling Groq...")
    skill_mapping = clean_skills_with_groq(skill_candidates)

    print(f"Mapped skills: {len(skill_mapping):,}")

    print("Saving skill mapping...")
    save_skill_mapping(skill_mapping)

    print(f"Saved: {SKILL_MAPPING_OUTPUT}")
    print(f"Saved: {SKILL_WHITELIST_OUTPUT}")
    print("Done.")


if __name__ == "__main__":
    main()