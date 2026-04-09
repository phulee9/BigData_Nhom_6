import os
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
    # Upload file Kaggle lên Bronze, bỏ qua nếu đã tồn tại
    path = f"bronze/kaggle/{filename}"
    try:
        client.stat_object(BUCKET, path)
        print(f"Da ton tai, bo qua: {path}")
        return
    except Exception:
        pass
    client.fput_object(BUCKET, path, local_path)
    print(f"Bronze Kaggle: {path}")


def push_crawl(local_path: str, filename: str):
    # Upload file crawl theo ngày, bỏ qua nếu hôm nay đã upload
    date = datetime.now().strftime("%Y-%m-%d")
    path = f"bronze/crawled/{date}/{filename}"
    try:
        client.stat_object(BUCKET, path)
        print(f"Hom nay da upload: {path}")
        return
    except Exception:
        pass
    client.fput_object(BUCKET, path, local_path)
    print(f"Bronze Crawl: {path}")


if __name__ == "__main__":
    # Upload Kaggle dataset, chỉ lần đầu
    push_kaggle("data/linkedin_job_postings.csv", "linkedin_job_postings.csv")
    push_kaggle("data/job_skills.csv", "job_skills.csv")

    # Upload Monster crawl nếu có
    crawl = "scraper/crawl_monster/monster_jobs_with_skills_chunk_1.json"
    if os.path.exists(crawl):
        push_crawl(crawl, "monster_jobs_chunk_1.json")
    else:
        print("Khong co crawl data hom nay")