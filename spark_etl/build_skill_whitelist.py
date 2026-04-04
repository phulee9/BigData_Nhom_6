import os, json, time
import pandas as pd
from minio import Minio
from collections import Counter
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client_minio = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
client_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
BUCKET = os.getenv("MINIO_BUCKET")

# ── Đọc thẳng từ Bronze ────────────────────────────────
print("⏳ Đọc job_skills từ Bronze...")
df_skills = pd.read_csv(
    client_minio.get_object(
        BUCKET, "bronze/kaggle/job_skills.csv"
    )
).dropna(subset=["job_skills"])
print(f"✓ {len(df_skills):,} rows")

# ── Đếm tần suất ──────────────────────────────────────
print("⏳ Đếm tần suất skills...")
skill_counter = Counter()
for skills_str in df_skills["job_skills"]:
    if not isinstance(skills_str, str):
        continue
    for s in skills_str.split(","):
        s = s.strip().lower()
        if s:
            skill_counter[s] += 1

print(f"✓ Tổng unique skills: {len(skill_counter):,}")

# ── Filter bước 1 ─────────────────────────────────────
CANDIDATES = [
    skill for skill, count
    in skill_counter.most_common()
    if count >= 200
    and len(skill.split()) <= 4
    and len(skill) > 1
]
print(f"✓ Sau filter: {len(CANDIDATES):,} skills candidates")

# ── Groq validate ─────────────────────────────────────
def validate_batch(batch: list) -> list:
    prompt = f"""Từ danh sách sau, chỉ giữ lại những thứ là KỸ NĂNG THẬT.
Giữ lại: technical skills, professional skills,
          tools, software, languages, frameworks,
          certifications, domain knowledge.
Loại bỏ: mô tả công việc, yêu cầu thể chất,
          bằng cấp chung, cụm từ mơ hồ,
          không phải kỹ năng cụ thể.

Danh sách: {", ".join(batch)}

Trả về JSON: {{"valid_skills": ["skill1", "skill2"]}}
Chỉ JSON thuần túy, không text thêm."""

    try:
        res = client_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=2048,
        )
        raw = res.choices[0].message.content.strip()
        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip().lstrip("json").strip()
                if part.startswith("{"):
                    raw = part
                    break
        data = json.loads(raw)
        return [s.lower().strip()
                for s in data.get("valid_skills", [])]
    except Exception as e:
        print(f"  [!] Loi: {e}")
        return batch

# ── Chạy validate ─────────────────────────────────────
print(f"⏳ Groq validate {len(CANDIDATES):,} skills...")
BATCH_SIZE  = 200
WHITELIST   = set()
total_batch = len(CANDIDATES) // BATCH_SIZE + 1

for i in range(0, len(CANDIDATES), BATCH_SIZE):
    batch     = CANDIDATES[i:i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    print(f"  Batch {batch_num}/{total_batch}...", end=" ")

    valid = validate_batch(batch)
    WHITELIST.update(valid)
    print(f"✓ {len(valid)}/{len(batch)} valid")

    if batch_num % 25 == 0:
        print("  Nghỉ 60 giây...")
        time.sleep(60)
    else:
        time.sleep(2)

print(f"\n✓ Whitelist: {len(WHITELIST):,} skills")

# ── Lưu whitelist ─────────────────────────────────────
out = Path(__file__).parent.parent / \
      "recomendation_system" / "skill_whitelist.json"

with open(out, "w", encoding="utf-8") as f:
    json.dump(sorted(list(WHITELIST)), f,
              ensure_ascii=False, indent=2)

print(f"✓ Lưu: {out}")
print("  Tiep theo: python spark_etl/bronze_to_silver.py")