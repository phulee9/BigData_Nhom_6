import io
import json
import os
import sys
import pandas as pd
from minio import Minio
from multiprocessing import Pool, cpu_count
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq

sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent / "recommendation" / "core"))
from nlp_utils import process_row_title_only, process_job_skills, get_whitelist, reload_whitelist
from skill_config import normalize_skill

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key = os.getenv("MINIO_ACCESS_KEY"),
    secret_key = os.getenv("MINIO_SECRET_KEY"),
    secure     = False
)
BUCKET         = os.getenv("MINIO_BUCKET")
PROCESSED_LOG  = "silver/processed_files.json"
WHITELIST_PATH = Path(__file__).parent.parent / "recommendation" / "data" / "skill_whitelist.json"

GROQ_KEYS = [
    k for k in [
        os.getenv("GROQ_API_KEY_1"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3"),
    ] if k
] or [os.getenv("GROQ_API_KEY")]

current_key_idx = 0

SYSTEM_PROMPT_VALIDATE = """You are a job skill classifier.
Keep items that are genuine job skills: specific tools, technologies,
techniques, certifications, software, equipment, languages, or domain
knowledge that a person learns and uses professionally.
Remove everything else.
When in doubt, remove it."""


def get_groq_client() -> Groq:
    return Groq(api_key=GROQ_KEYS[current_key_idx])


def load_processed_log() -> set:
    # Doc danh sach files da xu ly tu MinIO
    try:
        data = json.loads(
            client.get_object(BUCKET, PROCESSED_LOG).read().decode()
        )
        return set(data)
    except Exception:
        return set()


def save_processed_log(processed: set):
    # Luu danh sach files da xu ly len MinIO
    data = json.dumps(sorted(list(processed))).encode("utf-8")
    client.put_object(
        bucket_name  = BUCKET,
        object_name  = PROCESSED_LOG,
        data         = io.BytesIO(data),
        length       = len(data),
        content_type = "application/json"
    )


def get_new_files(processed: set) -> list:
    # Quet Bronze, lay files CSV chua co trong processed log
    new_files = []
    objs = client.list_objects(
        BUCKET, prefix="bronze/crawled/", recursive=True
    )
    for o in objs:
        if not o.object_name.endswith(".csv"):
            continue
        # Bo prefix "bronze/crawled/" de lay key
        # VD: "bronze/crawled/indeed/2026-04-09.csv" -> "indeed/2026-04-09.csv"
        key = "/".join(o.object_name.split("/")[2:])
        if key not in processed:
            new_files.append(o.object_name)
    return sorted(new_files)


def read_file(object_name: str) -> pd.DataFrame:
    # Doc file CSV tu MinIO theo format chuan: title + skills (phan cach " | ")
    try:
        data = client.get_object(BUCKET, object_name).read()
        df   = pd.read_csv(io.BytesIO(data))

        if "title" not in df.columns or "skills" not in df.columns:
            print(f"  [!] Thieu cot title/skills: {object_name}")
            return pd.DataFrame()

        df = df.rename(columns={"title": "job_title"})

        # Doi dau phan cach " | " thanh ", "
        df["job_skills"] = df["skills"].str.replace(
            " | ", ", ", regex=False
        ).str.lower().str.strip()

        df = df[["job_title", "job_skills"]].dropna(
            subset=["job_title", "job_skills"]
        )
        df = df[df["job_skills"].str.strip() != ""]

        # Luu ten file nguon de silver_to_gold_new.py biet job tu file nao
        df["source_file"] = "/".join(object_name.split("/")[2:])

        print(f"  Doc duoc: {len(df):,} rows")
        return df

    except Exception as e:
        print(f"  [!] Loi doc file: {e}")
        return pd.DataFrame()


def clean_title_only(df: pd.DataFrame) -> pd.DataFrame:
    # Buoc 1: Chi clean job_title (spaCy NER + synonym + lemmatize)
    # Giu nguyen job_skills tho de validate whitelist o buoc sau
    print(f"  Clean job_title ({cpu_count()} cores)...")
    rows = df[["job_title", "job_skills"]].to_dict("records")

    with Pool(cpu_count()) as p:
        results = p.map(process_row_title_only, rows)

    df["job_title"], df["job_skills"] = zip(*results)
    df = df[df["job_title"] != ""].reset_index(drop=True)
    print(f"  Sau clean title: {len(df):,} jobs")
    return df


def validate_batch(batch: list, retry: int = 0) -> list:
    # Goi Groq validate 1 batch skills, tu chuyen key khi het token
    global current_key_idx

    if retry >= len(GROQ_KEYS):
        print("  [!] Da thu tat ca Groq keys!")
        return []

    try:
        res = get_groq_client().chat.completions.create(
            model    = "llama-3.3-70b-versatile",
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_VALIDATE},
                {"role": "user",   "content":
                    f"Keep only genuine job skills:\n\n{', '.join(batch)}\n\n"
                    f"Return ONLY valid JSON in this format:\n"
                    f"Return ONLY: {{\"valid_skills\": [\"skill1\", \"skill2\"]}}"}
            ],
            temperature     = 0.0,
            max_tokens      = 1024,
            response_format = {"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        return [s.lower().strip() for s in data.get("valid_skills", [])]

    except Exception as e:
        err = str(e)
        if "429" in err and "tokens per day" in err:
            current_key_idx += 1
            if current_key_idx < len(GROQ_KEYS):
                print(f"  Het token! Chuyen sang key {current_key_idx + 1}...")
                return validate_batch(batch, retry + 1)
        print(f"  [!] Groq loi: {e}")
        return []


def update_whitelist(df: pd.DataFrame, whitelist: set) -> set:
    # Buoc 2: Tim skills chua co trong whitelist (kiem tra qua normalized version)
    # Goi Groq validate, them skills hop le vao whitelist va luu file
    new_skills = set()
    for skills_str in df["job_skills"]:
        if not isinstance(skills_str, str):
            continue
        for s in skills_str.split(","):
            s_clean = s.strip().lower()
            s_norm  = normalize_skill(s_clean)
            if s_norm and s_norm not in whitelist:
                new_skills.add(s_clean)

    if not new_skills:
        print("  Khong co skills moi can validate")
        return whitelist

    print(f"  Tim thay {len(new_skills)} skills moi, dang validate...")

    added    = 0
    new_list = list(new_skills)
    for i in range(0, len(new_list), 200):
        batch = new_list[i:i + 200]
        valid = validate_batch(batch)
        for s in valid:
            s_norm = normalize_skill(s)
            if s_norm not in whitelist:
                whitelist.add(s_norm)
                added += 1

    print(f"  Them {added} skills moi ({len(whitelist):,} tong)")

    # Luu whitelist da cap nhat xuong file
    with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(list(whitelist)), f, ensure_ascii=False, indent=2)

    return whitelist


def filter_skills(df: pd.DataFrame) -> pd.DataFrame:
    # Buoc 3: Reload whitelist moi roi normalize + filter tung skill
    # Skills moi vua them o buoc 2 se khong bi loc mat
    reload_whitelist()
    print(f"  Filter skills theo whitelist moi...")

    df["job_skills"] = df["job_skills"].apply(
        lambda x: process_job_skills(x, use_whitelist=True)
    )
    df["title_skills"] = df["job_title"] + " " + df["job_skills"]

    df = df[
        df["job_skills"] != ""
    ].drop_duplicates(
        subset=["job_title", "job_skills"]
    ).reset_index(drop=True)

    print(f"  Sau filter: {len(df):,} jobs")
    return df


def save_silver_new(df: pd.DataFrame, object_name: str):
    # Buoc 4: Luu Silver theo cung cau truc Bronze
    # bronze/crawled/indeed/2026-04-09.csv -> silver/new/indeed/2026-04-09.csv
    silver_path = "silver/new/" + "/".join(object_name.split("/")[2:])

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    client.put_object(
        bucket_name  = BUCKET,
        object_name  = silver_path,
        data         = io.BytesIO(csv_bytes),
        length       = len(csv_bytes),
        content_type = "application/csv"
    )
    print(f"  Da luu: {silver_path} ({len(df):,} jobs)")


if __name__ == "__main__":

    # Kiem tra whitelist truoc khi chay
    whitelist = get_whitelist()
    if not whitelist:
        print("[LOI] Chua co whitelist!")
        print("  Chay truoc: python etl/build_skill_whitelist.py")
        sys.exit(1)

    # Tim cac file moi chua xu ly tren Bronze
    processed = load_processed_log()
    print(f"Da xu ly truoc: {len(processed)} files")

    new_files = get_new_files(processed)
    if not new_files:
        print("Khong co file moi!")
        sys.exit(0)

    print(f"Tim thay {len(new_files)} file moi:")
    for f in new_files:
        print(f"  - {f}")

    # Xu ly tung file moi
    for object_name in new_files:
        print(f"\nXu ly: {object_name}")

        # Doc file CSV tu Bronze
        df_raw = read_file(object_name)
        if df_raw.empty:
            processed.add("/".join(object_name.split("/")[2:]))
            continue

        # Buoc 1: Clean job_title, giu nguyen skills tho
        df_clean = clean_title_only(df_raw)
        if df_clean.empty:
            processed.add("/".join(object_name.split("/")[2:]))
            continue

        # Buoc 2: Tim skills moi, Groq validate, cap nhat whitelist
        whitelist = update_whitelist(df_clean, whitelist)

        # Buoc 3: Reload whitelist moi, normalize + filter skills
        df_clean = filter_skills(df_clean)
        if df_clean.empty:
            processed.add("/".join(object_name.split("/")[2:]))
            continue

        # Buoc 4: Luu Silver theo cung cau truc Bronze
        save_silver_new(df_clean, object_name)

        # Danh dau file da xu ly
        processed.add("/".join(object_name.split("/")[2:]))

    # Luu processed log
    save_processed_log(processed)
    print("\nXong! Tiep theo: python etl/silver_to_gold_new.py")