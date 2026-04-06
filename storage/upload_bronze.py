import os, json
from datetime import datetime
from pathlib import Path
from minio import Minio
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
BUCKET = os.getenv("MINIO_BUCKET")

def push_kaggle(local_path: str, filename: str):
    path = f"bronze/kaggle/{filename}"
    try:
        client.stat_object(BUCKET, path)
        print(f"Đã tồn tại, bỏ qua: {path}")
        return
    except:
        pass
    client.fput_object(BUCKET, path, local_path)
    print(f"Bronze Kaggle: {path}")

def push_crawl(local_path: str, filename: str):
    date = datetime.now().strftime("%Y-%m-%d")
    path = f"bronze/crawled/{date}/{filename}"
    try:
        client.stat_object(BUCKET, path)
        print(f"Hôm nay đã upload: {path}")
        return
    except:
        pass
    client.fput_object(BUCKET, path, local_path)
    print(f"Bronze Crawl: {path}")

if __name__ == "__main__":
    # Kaggle — chỉ upload lần đầu
    push_kaggle("data/linkedin_job_postings.csv",
                "linkedin_job_postings.csv")
    push_kaggle("data/job_skills.csv",
                "job_skills.csv")

    # Monster crawl
    crawl = "scraper/crawl_monster/monster_jobs_with_skills_chunk_1.json"
    if os.path.exists(crawl):
        push_crawl(crawl, "monster_jobs_chunk_1.json")
    else:
        print("Không có crawl data hôm nay")