import os
import json
import time
import pandas as pd
from minio import Minio
from collections import Counter
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Đường dẫn lưu whitelist
WHITELIST_PATH = Path(__file__).parent.parent / "recommendation" / "data" / "skill_whitelist.json"
PROGRESS_PATH  = Path(__file__).parent.parent / "recommendation" / "data" / "whitelist_progress.json"

# Multi-key rotation cho Groq
GROQ_KEYS = [
    k for k in [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3"),
        os.getenv("GROQ_API_KEY_4"),
        os.getenv("GROQ_API_KEY_5"),
    ] if k
]

if not GROQ_KEYS:
    single = os.getenv("GROQ_API_KEY")
    if single:
        GROQ_KEYS = [single]
    else:
        raise ValueError("Khong co GROQ_API_KEY nao trong .env!")

print(f"Da load {len(GROQ_KEYS)} Groq API key(s)")
current_key_idx = 0

client_minio = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")

SYSTEM_PROMPT = """You are a job skill classifier.

Keep items that are genuine job skills: specific tools, technologies, 
techniques, certifications, software, equipment, languages, or domain 
knowledge that a person learns and uses professionally.

Remove everything else: job descriptions, soft skills, personality traits, 
physical requirements, education requirements, benefits, and vague phrases.

When in doubt → remove it."""


def get_groq_client() -> Groq:
    return Groq(api_key=GROQ_KEYS[current_key_idx])


def validate_batch(batch: list, retry: int = 0) -> list:
    # Gọi Groq validate 1 batch skills, tự động chuyển key khi hết token
    global current_key_idx

    if retry >= len(GROQ_KEYS):
        print("  [!] Da thu tat ca keys!")
        return []

    try:
        res = get_groq_client().chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"From this list, keep only genuine job skills.\n\n{', '.join(batch)}\n\nReturn ONLY this JSON:\n{{\"valid_skills\": [\"skill1\", \"skill2\"]}}"}
            ],
            temperature     = 0.0,
            max_tokens      = 2048,
            response_format = {"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content.strip())
        return [s.lower().strip() for s in data.get("valid_skills", [])]

    except Exception as e:
        err = str(e)

        if "429" in err and "tokens per day" in err:
            current_key_idx += 1
            if current_key_idx < len(GROQ_KEYS):
                print(f"\n  Het token! Chuyen sang key {current_key_idx + 1}...")
                return validate_batch(batch, retry + 1)
            return None

        elif "429" in err:
            print("\n  Rate limit, doi 30 giay...")
            time.sleep(30)
            return validate_batch(batch, retry)

        else:
            print(f"  [!] Loi: {e}")
            return []


def save_progress(whitelist: set, next_idx: int):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump({"whitelist": sorted(list(whitelist)), "next_idx": next_idx}, f)


def load_progress() -> tuple:
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Resume tu batch {data['next_idx'] // 200 + 1}")
        print(f"Da co: {len(data['whitelist']):,} skills")
        return set(data["whitelist"]), data["next_idx"]
    return set(), 0


if __name__ == "__main__":
    # Đọc job_skills từ Bronze
    print("Doc job_skills tu Bronze...")
    df_skills = pd.read_csv(
        client_minio.get_object(BUCKET, "bronze/kaggle/job_skills.csv")
    ).dropna(subset=["job_skills"])
    print(f"{len(df_skills):,} rows")

    # Đếm tần suất skills
    print("Dem tan suat skills...")
    skill_counter = Counter()
    for skills_str in df_skills["job_skills"]:
        if not isinstance(skills_str, str):
            continue
        for s in skills_str.split(","):
            s = s.strip().lower()
            if s:
                skill_counter[s] += 1
    print(f"Unique skills: {len(skill_counter):,}")

    # Filter sơ bộ trước khi gửi Groq
    CANDIDATES = [
        skill for skill, count in skill_counter.most_common()
        if count >= 200
        and len(skill.split()) <= 4
        and len(skill) > 1
    ]
    print(f"Sau filter: {len(CANDIDATES):,} candidates")

    # Load progress nếu đã chạy trước
    WHITELIST, start_idx = load_progress()

    # Validate từng batch bằng Groq
    BATCH_SIZE  = 200
    total_batch = len(CANDIDATES) // BATCH_SIZE + 1

    print(f"Groq validate {len(CANDIDATES):,} skills...")
    print(f"  {total_batch} batches | {len(GROQ_KEYS)} key(s)\n")

    for i in range(start_idx, len(CANDIDATES), BATCH_SIZE):
        batch     = CANDIDATES[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        print(f"  Batch {batch_num}/{total_batch} [key {current_key_idx + 1}/{len(GROQ_KEYS)}]...", end=" ")
        valid = validate_batch(batch)

        # Hết tất cả keys → lưu progress và dừng
        if valid is None:
            save_progress(WHITELIST, i)
            print(f"\n  Luu progress tai batch {batch_num}")
            print(f"  Da co: {len(WHITELIST):,} skills")
            print("  Dang ky them GROQ_API_KEY roi chay lai!")
            break

        WHITELIST.update(valid)
        print(f"{len(valid)}/{len(batch)} valid | Tong: {len(WHITELIST):,}")

        # Lưu progress mỗi 10 batch
        if batch_num % 10 == 0:
            save_progress(WHITELIST, i + BATCH_SIZE)

        if batch_num % 25 == 0:
            print("  Nghi 60 giay...")
            time.sleep(60)
        else:
            time.sleep(2)

    else:
        # Hoàn thành tất cả batches
        print(f"\nHoan thanh! Whitelist: {len(WHITELIST):,} skills")

        WHITELIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(WHITELIST)), f, ensure_ascii=False, indent=2)
        print(f"Luu: {WHITELIST_PATH}")

        # Xóa progress file
        if PROGRESS_PATH.exists():
            PROGRESS_PATH.unlink()

        print("Tiep theo: python etl/bronze_to_silver.py")